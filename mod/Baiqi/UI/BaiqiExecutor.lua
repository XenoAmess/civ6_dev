-- Invisible executor: the leader selection is the only administration switch.
include("BaiqiController")
include("BaiqiAdmin")
include("BaiqiMissionaryPurchase")
local ready=false
local adminStopped=false
local adminElapsed=0
local updateElapsed=0
local recoveryNeeded=false
local awaitingStandby=false
local acknowledgedTurn
local function CurrentTurn()
  if not Game or type(Game.GetCurrentGameTurn)~="function" then return nil end
  local ok,value=pcall(Game.GetCurrentGameTurn)
  if ok and type(value)=="number" and value>=0 and value<=2147483647 and value==math.floor(value) then return value end
end
local function UnsentRead(ok,...)
  return ok==true and select("#",...)==1 and (...)==false
end
local function TurnReady()
  local acknowledged=acknowledgedTurn
  if acknowledged==nil or CurrentTurn()~=acknowledged then return false end
  -- The native end request can be sent before active/strategic/busy changes.
  -- Keep passive receipts available, but require a fresh unsent state for orders.
  local ui=UI
  local read=ui and ui.HasSentTurnComplete
  if type(read)~="function" then return false end
  return UnsentRead(pcall(read)) and UI==ui and ui.HasSentTurnComplete==read
    and acknowledgedTurn==acknowledged and CurrentTurn()==acknowledged
end
BaiqiController.SetTurnGuard(TurnReady)
local function Visible()
  local hud=ContextPtr:LookUpControl("/InGame/HUD")
  return ready and hud~=nil and not hud:IsHidden()
end
-- CanProduce is the UI readback of native project availability, not attach ACK.
local function StandbyAvailable()
  local row=GameInfo.Projects and GameInfo.Projects.PROJECT_BAIQI_STANDBY
  local player=Players[Game.GetLocalPlayer()]
  if not row or not player then return nil end
  local count=0
  for _,city in player:GetCities():Members() do
    count=count+1
    if city:GetBuildQueue():CanProduce(row.Hash,true)==true then return true end
  end
  if count>0 then return false end
end
local function Recover()
  if not recoveryNeeded and not awaitingStandby then return end
  if not Visible() or not TurnReady() or not BaiqiController.IsAvailable() then return end
  local available=StandbyAvailable()
  if awaitingStandby and available==true then
    awaitingStandby=false
    BaiqiController.RefreshProduction()
    print("BAIQI|standby_unlock_observed|proof=native_can_produce")
  end
  if not recoveryNeeded then return end
  local params={OnStart="BaiqiRequisitionRecover"}
  if available==false then params.standbyUnlockNeeded=true;awaitingStandby=true end
  UI.RequestPlayerOperation(Game.GetLocalPlayer(),PlayerOperations.EXECUTE_SCRIPT,params)
  recoveryNeeded=false
end
local function Update(delta)
  -- Batch frame time before entering Native UI/player reads. Event callbacks
  -- still run immediately, and every periodic pass rechecks current authority.
  if type(delta)~="number" or delta~=delta or delta<0 or delta==math.huge then return end
  updateElapsed=updateElapsed+delta
  if updateElapsed<BaiqiConfig.interval then return end
  delta=updateElapsed
  updateElapsed=0
  if Visible() then
    if TurnReady() and BaiqiController.IsAvailable() then
      Recover()
      adminElapsed=adminElapsed+delta
      if not adminStopped and adminElapsed>=BaiqiConfig.interval then
        adminElapsed=0
        local ok,err=pcall(BaiqiAdmin.Run)
        if not ok then adminStopped=true;print("BAIQI|admin_error|"..tostring(err)) end
      end
    end
    BaiqiController.Update(delta,TurnReady())
  end
end
local function RunIfReady()
  if not Visible() or not TurnReady() or not BaiqiController.IsAvailable() then return end
  Recover()
  if TurnReady() and BaiqiController.IsAvailable() then BaiqiController.RunNow() end
end
local function Activate(playerID)
  local localPlayer=Game.GetLocalPlayer()
  if type(localPlayer)~="number" or localPlayer<0 or localPlayer>2147483647 or localPlayer%1~=0
    or playerID~=localPlayer then return end
  local current=CurrentTurn()
  if current==nil then return end
  acknowledgedTurn=current
  print("BAIQI|turn_acknowledged|turn="..current.."|player="..localPlayer.."|source=native_player_turn_activated")
  recoveryNeeded=true
  if ready then ContextPtr:SetHide(false);RunIfReady() end
end
local function OnViewReady()
  ready=true
  if type(GameConfiguration)=="table" and type(GameConfiguration.IsSavedGame)=="function" then
    local ok,saved=pcall(GameConfiguration.IsSavedGame)
    if ok and type(saved)=="boolean" then
      BaiqiController.SetSettlementLoadKind(saved)
      if saved==true then acknowledgedTurn=CurrentTurn() end
    end
  end
  recoveryNeeded=true
  ContextPtr:SetHide(false)
  RunIfReady()
end
local function OnPlayback()
  if Visible() and TurnReady() and BaiqiController.IsAvailable() then BaiqiController.RunNow() end
end
ContextPtr:SetUpdate(Update)
Events.LoadGameViewStateDone.Add(OnViewReady)
Events.PlayerTurnActivated.Add(Activate)
Events.GameCoreEventPlaybackComplete.Add(OnPlayback)
ContextPtr:SetInitHandler(function(isReload) if isReload then OnViewReady() end end)
ContextPtr:SetShutdown(function()
  Events.LoadGameViewStateDone.Remove(OnViewReady)
  Events.PlayerTurnActivated.Remove(Activate)
  Events.GameCoreEventPlaybackComplete.Remove(OnPlayback)
  BaiqiController.Shutdown()
end)
