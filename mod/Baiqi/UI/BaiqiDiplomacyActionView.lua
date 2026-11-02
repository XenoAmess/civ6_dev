-- Native diplomacy owns loading, event locks, sessions and all player choices.
include("BaiqiUILoader")
BaiqiUILoader.Load("DiplomacyActionView")
local nativeShowLeader=ShowLeader
ShowLeader=function(player,...)
  nativeShowLeader(player,...)
  local config=player and PlayerConfigurations[player:GetID()]
  -- Our explicit empty Leaders.artdef removes the default 3D model. The complete
  -- portrait is in the background, so hide only its native fallback image anchor.
  Controls.LeaderAnchor:SetHide(config~=nil and config:GetLeaderTypeName()=="LEADER_BAIQI")
end
