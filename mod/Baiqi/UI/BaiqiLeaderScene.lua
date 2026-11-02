-- Preserve native scene registration and loading; only Baiqi uses a full image.
include("LeaderScene")
local nativeGenerateLayers=GenerateLayers
GenerateLayers=function(playerID,...)
  nativeGenerateLayers(playerID,...)
  local config=PlayerConfigurations[playerID]
  local static=config~=nil and config:GetLeaderTypeName()=="LEADER_BAIQI"
  Controls.TopLetterbox:SetHide(static)
  Controls.BottomLetterbox:SetHide(static)
end
