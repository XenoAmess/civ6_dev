-- Invisible executor: the leader selection is the only administration switch.
include("BaiqiController")
include("BaiqiAdmin")
local ready=false
local adminStopped=false
local function Visible()
  local hud=ContextPtr:LookUpControl("/InGame/HUD")
  return ready and hud~=nil and not hud:IsHidden()
end
local function Update(delta)
  if Visible() then
    if not adminStopped then
      local ok,err=pcall(BaiqiAdmin.Run)
      if not ok then adminStopped=true;print("BAIQI|admin_error|"..tostring(err)) end
    end
    BaiqiController.Update(delta)
  end
end
local function Recover()
  if not ready or not BaiqiController.IsAvailable() then return end
  local pid=Game.GetLocalPlayer()
  UI.RequestPlayerOperation(pid,PlayerOperations.EXECUTE_SCRIPT,{OnStart="BaiqiRequisitionRecover"})
end
local function Activate()
  if not ready then return end
  ContextPtr:SetHide(false)
  if Visible() then BaiqiController.RunNow() end
  Recover()
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
