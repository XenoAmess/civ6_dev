include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("CivicsChooser")
BaiqiUILoader.ReadOnly()
local nativeChoose=OnChooseCivic
OnChooseCivic=function(...)
  if BaiqiUIGuard.PlayerID()~=nil then return false end
  return nativeChoose(...)
end
