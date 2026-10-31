include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("TechCivicCompletedPopup")

-- Captured native notification callbacks resolve this global at invocation.
-- Suppress before AddCompletedPopup queues anything; explicit inspection remains.
local NativeAddCompletedPopup=AddCompletedPopup
function AddCompletedPopup(player,civic,tech,isByUser)
  if player==BaiqiUIGuard.PlayerID() and not isByUser then
    print("BAIQI|completion_cinematic_skipped|turn="..Game.GetCurrentGameTurn()
      .."|civic="..tostring(civic).."|tech="..tostring(tech))
    return
  end
  return NativeAddCompletedPopup(player,civic,tech,isByUser)
end
