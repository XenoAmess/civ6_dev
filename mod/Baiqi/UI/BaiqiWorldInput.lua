-- Native WorldInput remains available for inspection. Writes use mandatory delegation.
include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("WorldInput")
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
