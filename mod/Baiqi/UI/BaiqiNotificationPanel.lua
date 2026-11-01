include("BaiqiUIGuard")
include("BaiqiUILoader")
-- The base script includes its installed NotificationPanel_* extensions itself.
BaiqiUILoader.Load("NotificationPanel")

local function GuardBoostHandlers()
  for _,kind in ipairs({NotificationTypes.TECH_BOOST,NotificationTypes.CIVIC_BOOST}) do
    local handler=g_notificationHandlers[kind]
    if handler and handler.Activate then
      local native=handler.Activate
      handler.Activate=function(entry,id,activatedByUser,...)
        if entry and entry.m_PlayerID==BaiqiUIGuard.PlayerID() and not activatedByUser then
          print("BAIQI|boost_cinematic_skipped|turn="..Game.GetCurrentGameTurn().."|notification="..tostring(id))
          return
        end
        return native(entry,id,activatedByUser,...)
      end
    end
  end
end

local function GuardGovernmentHandler()
  local kind=NotificationTypes and NotificationTypes.CONSIDER_GOVERNMENT_CHANGE
  local handler=kind~=nil and g_notificationHandlers[kind]
  if handler and type(handler.Activate)=="function" then
    local native=handler.Activate
    handler.Activate=function(entry,id,activatedByUser,...)
      local pid=BaiqiUIGuard.PlayerID()
      if pid~=nil and entry and entry.m_PlayerID==pid and not activatedByUser then
        print("BAIQI|government_notification_delegated|source=automatic")
        return
      end
      return native(entry,id,activatedByUser,...)
    end
  end
end

-- ActionPanel marks its turn-blocker activation as "by user" even though the
-- player only asked to end a turn. Filter that route before native dispatch;
-- direct notification inspection and the launch bar keep their native paths.
local NativeOnLuaActivateNotification=OnLuaActivateNotification
if type(NativeOnLuaActivateNotification)=="function" then
  function OnLuaActivateNotification(notification,...)
    local pid=BaiqiUIGuard.PlayerID()
    local kind=NotificationTypes and NotificationTypes.CONSIDER_GOVERNMENT_CHANGE
    if pid~=nil and kind~=nil and notification and notification:IsValidForPhase()
      and notification:GetPlayerID()==pid and notification:GetType()==kind then
      print("BAIQI|government_notification_delegated|source=turn_blocker")
      return
    end
    return NativeOnLuaActivateNotification(notification,...)
  end
end

-- Native OnInit calls this global later. Guard the freshly registered handlers,
-- rather than rebinding the broad notification event or dropping notifications.
local NativeRegisterHandlers=RegisterHandlers
function RegisterHandlers(...)
  NativeRegisterHandlers(...)
  GuardBoostHandlers()
  GuardGovernmentHandler()
end
GuardBoostHandlers()
GuardGovernmentHandler()
