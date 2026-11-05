-- Unit flags submit native operations in their own context.
include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("UnitFlagManager")
include("BaiqiActions")
local guardedManager=UnitManager
local flagManager=setmetatable({
  RequestOperation=BaiqiActions.WrapFlagOperation(guardedManager.RequestOperation),
},{__index=guardedManager})
UnitManager=flagManager
local nativeShutdown=OnShutdown
Events.GameCoreEventPlaybackComplete.Add(BaiqiActions.Poll)
ContextPtr:SetShutdown(function()
  Events.GameCoreEventPlaybackComplete.Remove(BaiqiActions.Poll)
  if UnitManager==flagManager then UnitManager=guardedManager end
  if nativeShutdown then nativeShutdown() end
end)
