-- Independent movement proposals; no bootstrap writes and no command API.
if BaiqiSettlerGoalsGameplay then return end
include("BaiqiSettlerGoals")
include("BaiqiSettlementJournal")
include("BaiqiSettlementUnitCore")
include("BaiqiSettlerGoalsCore")
local E={Game=Game,GameConfiguration=GameConfiguration,Players=Players,
  PlayerConfigurations=PlayerConfigurations,GameInfo=GameInfo,Map=Map,PlayersVisibility=PlayersVisibility}
local api=BaiqiSettlerGoalsCore.Create(BaiqiConfig,BaiqiSettlerGoals,BaiqiSettlementJournal,BaiqiSettlementUnitCore,E)
local MARKER="baiqi-settler-goals-v1"
BaiqiSettlerGoalsGameplay={}
if api and type(ExposedMembers)=="table"and(ExposedMembers.BaiqiSettlerGoalsBridge==nil
  or(type(ExposedMembers.BaiqiSettlerGoalsBridge)=="table"
    and ExposedMembers.BaiqiSettlerGoalsBridge.marker==MARKER
    and ExposedMembers.BaiqiSettlerGoalsBridge.version==1))then
  api.version=1;api.marker=MARKER;ExposedMembers.BaiqiSettlerGoalsBridge=api
  print("BAIQI|settler_goals_loaded|version=1")
else print("BAIQI|settler_goals_unavailable|bridge_or_dependencies=true")end
