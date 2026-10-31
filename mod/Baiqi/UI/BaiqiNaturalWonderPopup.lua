include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("NaturalWonderPopup")

-- The native callback acquires an exclusive lock before calling ShowPopup.
-- Replace its captured event registration, not the already-too-late display.
if not GameConfiguration.IsAnyMultiplayer() and not GameConfiguration.IsHotseat() then
  local native=OnNaturalWonderRevealed
  Events.NaturalWonderRevealed.Remove(native)
  function OnNaturalWonderRevealed(...)
    if BaiqiUIGuard.PlayerID()~=nil then
      print("BAIQI|natural_wonder_cinematic_skipped|turn="..Game.GetCurrentGameTurn())
      return
    end
    return native(...)
  end
  Events.NaturalWonderRevealed.Add(OnNaturalWonderRevealed)
end
