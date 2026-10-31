include("BaiqiController")

local function Update(delta)
  local available=BaiqiController.IsAvailable()
  Controls.Root:SetHide(not available)
  if available then
    BaiqiController.Update(delta)
    Controls.Status:SetText(BaiqiController.GetStatus())
  end
end

Controls.GlobalToggle:RegisterCallback(Mouse.eLClick,BaiqiController.ToggleGlobal)
Controls.CityToggle:RegisterCallback(Mouse.eLClick,BaiqiController.ToggleCity)
Controls.UnitToggle:RegisterCallback(Mouse.eLClick,BaiqiController.ToggleUnit)
Controls.Protect:RegisterCallback(Mouse.eLClick,BaiqiController.ProtectPlot)
ContextPtr:SetUpdate(Update)
local function ShowPanel()
  ContextPtr:SetHide(false)
  Update(0)
end
Events.LoadGameViewStateDone.Add(ShowPanel)
Events.PlayerTurnActivated.Add(ShowPanel)
ContextPtr:SetInitHandler(function(isReload) if isReload then ShowPanel() end end)
ContextPtr:SetShutdown(function()
  Events.LoadGameViewStateDone.Remove(ShowPanel)
  Events.PlayerTurnActivated.Remove(ShowPanel)
  BaiqiController.Shutdown()
end)
Update(0)
print("BAIQI|panel_loaded|version=1")
