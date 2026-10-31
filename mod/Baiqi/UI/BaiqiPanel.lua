include("BaiqiController")
include("BaiqiActions")
local ready=false

local function Update(delta)
  local available=BaiqiController.IsAvailable()
  Controls.Root:SetHide(not available)
  if available and ready then
    BaiqiController.Update(delta)
    local action=BaiqiActions.Status()
    Controls.Status:SetText(action~="" and action or BaiqiController.GetStatus())
  end
end

Controls.GlobalToggle:RegisterCallback(Mouse.eLClick,BaiqiController.ToggleGlobal)
Controls.CityToggle:RegisterCallback(Mouse.eLClick,BaiqiController.ToggleCity)
Controls.UnitToggle:RegisterCallback(Mouse.eLClick,BaiqiController.ToggleUnit)
Controls.Protect:RegisterCallback(Mouse.eLClick,BaiqiController.ProtectPlot)
Controls.Requisition:RegisterCallback(Mouse.eLClick,function() BaiqiActions.Show("city") end)
Controls.Granary:RegisterCallback(Mouse.eLClick,function() BaiqiActions.Show("granary") end)
ContextPtr:SetUpdate(Update)
local function ShowPanel()
  if not ready then return end
  ContextPtr:SetHide(false)
  Update(0)
  BaiqiController.RunNow()
  BaiqiActions.Recover()
end
local function OnViewReady() ready=true; ShowPanel() end
local function OnPlayback() if ready then BaiqiController.RunNow() end end
Events.LoadGameViewStateDone.Add(OnViewReady)
Events.PlayerTurnActivated.Add(ShowPanel)
Events.GameCoreEventPlaybackComplete.Add(OnPlayback)
ContextPtr:SetInitHandler(function(isReload) if isReload then OnViewReady() end end)
ContextPtr:SetShutdown(function()
  Events.LoadGameViewStateDone.Remove(OnViewReady)
  Events.PlayerTurnActivated.Remove(ShowPanel)
  Events.GameCoreEventPlaybackComplete.Remove(OnPlayback)
  BaiqiController.Shutdown()
end)
Update(0)
Controls.GlobalText:SetText(Locale.Lookup("LOC_BAIQI_UI_GLOBAL"))
Controls.CityText:SetText(Locale.Lookup("LOC_BAIQI_UI_CITY"))
Controls.UnitText:SetText(Locale.Lookup("LOC_BAIQI_UI_UNIT"))
Controls.ProtectText:SetText(Locale.Lookup("LOC_BAIQI_UI_PROTECT"))
Controls.RequisitionText:SetText("征取相邻城市")
Controls.GranaryText:SetText("征取粮仓经营权")
print("BAIQI|panel_loaded|version=1")
