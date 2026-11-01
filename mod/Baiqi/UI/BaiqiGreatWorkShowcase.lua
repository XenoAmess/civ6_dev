include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("GreatWorkShowcase")

if not GameConfiguration.IsAnyMultiplayer() and not GameConfiguration.IsHotseat() then
  local native=OnGreatWorkCreated
  Events.GreatWorkCreated.Remove(native)
  function OnGreatWorkCreated(player,...)
    if player==BaiqiUIGuard.PlayerID() then
      print("BAIQI|great_work_cinematic_skipped|turn="..Game.GetCurrentGameTurn())
      return
    end
    return native(player,...)
  end
  Events.GreatWorkCreated.Add(OnGreatWorkCreated)
end
