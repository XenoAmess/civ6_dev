-- The native event handlers resolve ShowRandomEvent when called. Suppress only
-- the cinematic before it acquires UI/playback locks. Gameplay remains native.
include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("NaturalDisasterPopup")
local nativeShow=ShowRandomEvent
ShowRandomEvent=function(...)
  if BaiqiUIGuard.PlayerID()~=nil then
    print("BAIQI|disaster_cinematic_skipped|turn="..Game.GetCurrentGameTurn())
    return
  end
  return nativeShow(...)
end
