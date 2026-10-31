-- Install the request guard before native callbacks capture UI methods.
include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("PantheonChooser")
BaiqiUILoader.ReadOnly()
local nativeConfirm=ConfirmPantheon
ConfirmPantheon=function(...)
  if BaiqiUIGuard.PlayerID()~=nil then return false end
  return nativeConfirm(...)
end
