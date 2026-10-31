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

-- Native OnInit calls this global later. Guard the freshly registered handlers,
-- rather than rebinding the broad notification event or dropping notifications.
local NativeRegisterHandlers=RegisterHandlers
function RegisterHandlers(...)
  NativeRegisterHandlers(...)
  GuardBoostHandlers()
end
GuardBoostHandlers()
