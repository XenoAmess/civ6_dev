include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("ChooseArtifact")

local nativeOnOpen = OnOpen
LuaEvents.NotificationPanel_OpenArtifactPanel.Remove(nativeOnOpen)

function OnOpen(...)
  if BaiqiUIGuard.PlayerID() ~= nil then
    ContextPtr:SetHide(true)
    return
  end
  nativeOnOpen(...)
  if Controls.Button1 ~= nil then
    Controls.Button1:SetDisabled(false)
  end
  if Controls.Button2 ~= nil then
    Controls.Button2:SetDisabled(false)
  end
end

LuaEvents.NotificationPanel_OpenArtifactPanel.Add(OnOpen)
