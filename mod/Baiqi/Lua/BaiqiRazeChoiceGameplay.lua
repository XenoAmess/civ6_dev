if BaiqiRazeChoiceGameplay then return end
include('BaiqiRazeChoiceCore')
local E={Game=Game,GameConfiguration=GameConfiguration,Players=Players,
  PlayerConfigurations=PlayerConfigurations,PlayersVisibility=PlayersVisibility,
  Map=Map,CityManager=CityManager}
local api=BaiqiRazeChoiceCore.Create(BaiqiConfig,E)
BaiqiRazeChoiceGameplay={}
if api and type(ExposedMembers)=='table'and(ExposedMembers.BaiqiRazeChoiceBridge==nil
  or(type(ExposedMembers.BaiqiRazeChoiceBridge)=='table'
    and ExposedMembers.BaiqiRazeChoiceBridge.marker=='baiqi-raze-choice-v1'
    and ExposedMembers.BaiqiRazeChoiceBridge.version==1))then
  api.version=1;api.marker='baiqi-raze-choice-v1'
  BaiqiRazeChoiceGameplay.api=api
  ExposedMembers.BaiqiRazeChoiceBridge=api
  print('BAIQI|raze_choice_loaded|version=1')
else
  print('BAIQI|raze_choice_unavailable')
end
