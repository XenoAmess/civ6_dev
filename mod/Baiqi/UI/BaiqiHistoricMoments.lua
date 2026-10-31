include("BaiqiUIGuard")
include("BaiqiUILoader")
-- Both expansion addons use this exact base filename in the mounted UI.
BaiqiUILoader.Load("HistoricMoments")

if HasCapability("CAPABILITY_HISTORIC_MOMENTS") then
  local native=OnProcessNotification
  local momentType=DB.MakeHash("NOTIFICATION_PRIDE_MOMENT_RECORDED")
  Events.NotificationActivated.Remove(native)
  function OnProcessNotification(player,id,activatedByUser)
    if player==BaiqiUIGuard.PlayerID() and not activatedByUser then
      local notification=NotificationManager.Find(player,id)
      if notification and notification:GetType()==momentType then
        print("BAIQI|history_cinematic_skipped|turn="..Game.GetCurrentGameTurn().."|notification="..tostring(id))
        return
      end
    end
    return native(player,id,activatedByUser)
  end
  Events.NotificationActivated.Add(OnProcessNotification)
end
