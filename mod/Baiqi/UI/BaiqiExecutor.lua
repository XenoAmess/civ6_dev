-- Invisible executor: the leader selection is the only administration switch.
include("BaiqiController")
include("BaiqiAdmin")
local ready=false
local adminStopped=false
local adminElapsed=0
local recoveryNeeded=false
local awaitingStandby=false
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
  if not Visible() or not BaiqiController.IsAvailable() then return end
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
  if Visible() then
    if BaiqiController.IsAvailable() then
      Recover()
      adminElapsed=adminElapsed+delta
      if not adminStopped and adminElapsed>=BaiqiConfig.interval then
        adminElapsed=0
        local ok,err=pcall(BaiqiAdmin.Run)
        if not ok then adminStopped=true;print("BAIQI|admin_error|"..tostring(err)) end
      end
    end
    BaiqiController.Update(delta)
  end
end
local function Activate()
  if not ready then return end
  recoveryNeeded=true
  ContextPtr:SetHide(false)
  Recover()
  if Visible() then BaiqiController.RunNow() end
end
local function OnViewReady() ready=true; Activate() end
local function OnPlayback() if Visible() then BaiqiController.RunNow() end end
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
