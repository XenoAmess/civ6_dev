-- Native UnitPanel remains available for inspection. Writes use mandatory delegation.
include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("UnitPanel")
BaiqiUILoader.ReadOnly()
include("BaiqiPolicy")
include("BaiqiActions")
MoveUnitToPlot=BaiqiActions.WrapMove(MoveUnitToPlot)
local nativeShutdown=OnShutdown
Events.GameCoreEventPlaybackComplete.Add(BaiqiActions.Poll)
ContextPtr:SetShutdown(function()
  Events.GameCoreEventPlaybackComplete.Remove(BaiqiActions.Poll)
  if nativeShutdown then nativeShutdown() end
end)
local nativeActions=GetUnitActionsTable
GetUnitActionsTable=function(unit)
  local actions=nativeActions(unit)
  if BaiqiUIGuard.Civilian(unit) then
    for key,value in pairs(actions) do
      if key~="displayOrder" and type(value)=="table" then actions[key]={} end
    end
  end
  return actions
end
