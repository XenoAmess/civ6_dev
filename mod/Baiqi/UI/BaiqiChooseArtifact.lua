include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("ChooseArtifact")

local nativeOnOpen = OnOpen
LuaEvents.NotificationPanel_OpenArtifactPanel.Remove(nativeOnOpen)

function OnOpen(...)
  nativeOnOpen(...)
  if Controls.Button1 ~= nil then
    Controls.Button1:SetDisabled(BaiqiUIGuard.PlayerID() ~= nil)
  end
  if Controls.Button2 ~= nil then
    Controls.Button2:SetDisabled(BaiqiUIGuard.PlayerID() ~= nil)
  end
end

LuaEvents.NotificationPanel_OpenArtifactPanel.Add(OnOpen)
