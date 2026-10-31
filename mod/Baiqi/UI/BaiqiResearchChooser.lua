-- Quick chooser is a separate input context from the full technology tree.
include("BaiqiUIGuard")
include("BaiqiUILoader")
BaiqiUILoader.Load("ResearchChooser")
BaiqiUILoader.ReadOnly()
local nativeChoose=OnChooseResearch
OnChooseResearch=function(...)
  if BaiqiUIGuard.PlayerID()~=nil then return false end
  return nativeChoose(...)
end
