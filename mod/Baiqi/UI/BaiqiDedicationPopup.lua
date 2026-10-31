include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("DedicationPopup")
BaiqiUILoader.ReadOnly()
local nativeConfirm=OnConfirm
OnConfirm=function(...)
  if BaiqiUIGuard.PlayerID()~=nil then return false end
  return nativeConfirm(...)
end
