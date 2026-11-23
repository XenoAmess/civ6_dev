include('BaiqiConfig')
include('BaiqiUILoader')
BaiqiUILoader.Load('RazeCity')
include('BaiqiRazeChoiceView')
local identity={Game=Game,GameConfiguration=GameConfiguration,Players=Players,
  PlayerConfigurations=PlayerConfigurations}
local original=CityManager
local proxy=setmetatable({RequestCommand=BaiqiRazeChoiceView.Wrap(original.RequestCommand,original,
  {PlayerID=function()return BaiqiRazeChoiceView.PlayerID(BaiqiConfig,identity)end,
   CityCommandTypes=CityCommandTypes,CityDestroyDirectives=CityDestroyDirectives,
   UnitOperationTypes=UnitOperationTypes,Map=Map,ExposedMembers=ExposedMembers,Print=print})},
  {__index=original})
CityManager=proxy
local shutdown=OnShutdown
ContextPtr:SetShutdown(function()
  if CityManager==proxy then CityManager=original end
  if shutdown then shutdown()end
end)
