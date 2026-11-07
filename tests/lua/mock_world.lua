-- Explicit adapter test world. This is not an engine simulation or a gameplay PASS.
TestWorld={cityRequests={},unitRequests={},turn=1,paused=false,formation=1,withCity=true,withSettler=false}
local W=TestWorld
function include(name)
 if name=="BaiqiSettlementJournal" then
  for _,module in ipairs({"BaiqiSettlementJournal","BaiqiSettlementStateCore","BaiqiSettlementUnitCore",
    "BaiqiSettlementTileCore","BaiqiSettlementIntentCore"})do dofile("mod/Baiqi/Lua/"..module..".lua")end
  -- Existing controller fixtures begin with a valid initialized journal. The
  -- initialization/load-kind boundary is exercised separately, not guessed here.
  local E={Game=Game,GameConfiguration=GameConfiguration,Players=Players,PlayerConfigurations=PlayerConfigurations,
    GameInfo=GameInfo,Map=Map,PlayersVisibility=PlayersVisibility,CityManager=CityManager}
  local S=assert(BaiqiSettlementStateCore.Create(BaiqiConfig,BaiqiSettlementJournal,E))
  local api=assert(BaiqiSettlementIntentCore.Create(BaiqiConfig,BaiqiSettlementJournal,S,BaiqiSettlementUnitCore,BaiqiSettlementTileCore,E))
  api.version=1;api.marker="baiqi-settlement-intent-v1"
  ExposedMembers=ExposedMembers or {};ExposedMembers.BaiqiSettlementIntentBridge=api
   -- Controller-only fixtures use abstract plot indices. Proposal bridge
   -- responses are supplied independently; real storage/schema and consistent
   -- native geometry are tested in the dedicated goals Core/world contracts.
   W.goalProposals=W.goalProposals or {}
   ExposedMembers.BaiqiSettlerGoalsBridge={version=1,marker='baiqi-settler-goals-v1',
    Read=function(pid,id)return 'READY',W.goalProposals[tostring(id)] end,
    Remember=function(pid,id,index,x,y)
      local g={unitID=id,unitType='UNIT_SETTLER',plot=index,x=x,y=y}
      W.goalProposals[tostring(id)]=g;return 'READY',g
    end,
    Forget=function(pid,id)W.goalProposals[tostring(id)]=nil;return 'READY' end}
 end
end
Game={GetLocalPlayer=function() return 7 end,GetCurrentGameTurn=function() return W.turn end,
 IsAllowStrategicCommands=function() return W.strategic~=false end}
GameConfiguration={IsAnyMultiplayer=function() return false end,IsHotseat=function() return false end}
local function rows(data)
  local result={}
  for i,row in ipairs(data) do result[row.Hash]=row; result[row.Index]=row; if row.BuildingType then result[row.BuildingType]=row end end
  return setmetatable(result,{__call=function() local i=0; return function() i=i+1; return data[i] end end})
end
GameInfo={Buildings=rows({
  {BuildingType="BUILDING_GRANARY",Hash=100,Index=0,IsWonder=false,RequiresPlacement=false,MustPurchase=false,Maintenance=0},
  {BuildingType="BUILDING_MONUMENT",Hash=101,Index=1,IsWonder=false,RequiresPlacement=false,MustPurchase=false,Maintenance=0}}),
  Districts=rows({}),Projects=rows({}),Resources=rows({}),Improvements=rows({}),
  Units=rows({{UnitType="UNIT_WARRIOR",Hash=200,Index=0,Combat=20,Maintenance=0},
    {UnitType="UNIT_SETTLER",Hash=201,Index=1,Combat=0,Maintenance=0},
    {UnitType="UNIT_BUILDER",Hash=202,Index=2,Combat=0,Maintenance=0}})}
CityOperationTypes={BUILD=1,PARAM_BUILDING_TYPE=2,PARAM_DISTRICT_TYPE=3,PARAM_UNIT_TYPE=4,
  PARAM_PROJECT_TYPE=5,PARAM_INSERT_MODE=6,VALUE_APPEND=7,PARAM_X=8,PARAM_Y=9}
UnitOperationTypes={MOVE_TO=10,FOUND_CITY=11,BUILD_IMPROVEMENT=12,REPAIR=13,PARAM_X=14,PARAM_Y=15,PARAM_IMPROVEMENT_TYPE=16,SKIP_TURN=17}
PlayerOperations={EXECUTE_SCRIPT=1}
YieldTypes={PRODUCTION=0}
local plot={}
function plot:GetIndex() return 42 end
function plot:GetX() return 2 end
function plot:GetY() return 3 end
function plot:GetFeatureType() return -1 end
function plot:GetOwner() return 7 end
function plot:IsCity() return false end
function plot:IsImprovementPillaged() return false end
function plot:GetImprovementType() return -1 end
Map={GetPlotByIndex=function() return plot end,GetPlot=function() return plot end,
  GetGridSize=function()return 10,10 end,
  -- The minimal world contains its queried center only. More detailed fixtures
  -- replace this oracle; zero native offset must still return the current plot.
  GetPlotXYWithRangeCheck=function(x,y,dx,dy,r)
    if dx==0 and dy==0 then return Map.GetPlot(x,y) end
  end,GetCityPlots=function() return {GetPurchasedPlots=function() return {} end} end}
MapLayers={PRIMARY=0,TRADE=1,SPY=2,RELIGIOUS=3,ANY=-1}
Units={GetUnitsInPlot=function() return {} end,
 GetUnitsInPlotLayerID=function(plot,layer)
  assert(layer==MapLayers.RELIGIOUS,"Background read a private map layer")
  return {}
 end}
local queue={}
function queue:GetSize() return W.queueSize or 0 end
function queue:GetCurrentProductionTypeHash() return 0 end
function queue:CanProduce(hash,mode) if hash==100 and mode==true then return false end return true end
local city={}
function city:GetID() return 66 end
function city:GetOwner() return 7 end
function city:GetX() return 2 end
function city:GetY() return 3 end
function city:GetPopulation() return 1 end
function city:GetBuildQueue() return queue end
function city:GetBuildings() return {IsPillaged=function() return false end} end
local army,settler,builder={},{},{}
for object,definition in pairs({[army]=0,[settler]=1,[builder]=2}) do
  object.GetUnitType=function() return definition end
  object.GetType=function(self)return self:GetUnitType()end
  object.IsDead=function()return false end
  object.IsDelayedDeath=function()return false end
  object.GetOwner=function() return 7 end
  object.GetID=function() return definition+1 end
  object.GetPlotId=function() return 42 end
  object.GetX=function() return 2 end
  object.GetY=function() return 3 end
  object.GetMovesRemaining=function() return 2 end
  object.GetFormationUnitCount=function() return W.formation end
end
local function members(objects)
 return function() local i=0;return function() i=i+1;if objects[i] then return i,objects[i] end end end
end
local player={}
function player:IsTurnActive() return true end
function player:GetProperty(key)
 if key=="BAIQI_SETTLEMENT_INTENTS_V1"then
  if W.settlementBank==nil and not W.missingSettlementBank then W.settlementBank=BaiqiSettlementJournal.New(7) end
  return W.settlementBank
 end
 return {version=1,enabled=not W.paused,cities={},units={},protected={}}
end
function player:SetProperty(key,value)
 assert(key=="BAIQI_SETTLEMENT_INTENTS_V1");W.settlementBank=value
end
function player:GetCities()
 return {Members=members(W.withCity and {city} or {}),GetCount=function() return W.withCity and 1 or 0 end,
   FindID=function() return W.withCity and city or nil end}
end
function player:GetUnits()
 local list=W.withSettler and {army,settler} or {army}
 if W.withBuilder then list[#list+1]=builder end
 return {Members=members(list),FindID=function(_,id) for _,unit in ipairs(list) do if unit:GetID()==id then return unit end end end}
end
function player:GetTreasury() return {GetGoldBalance=function() return 10 end,GetGoldYield=function() return 5 end,GetTotalMaintenance=function() return 0 end} end
function player:GetGrandStrategicAI() return nil end
function player:GetDiplomacy() return {IsAtWarWith=function() return false end} end
Players={[7]=player}
PlayerConfigurations={[7]={IsHuman=function() return true end,GetLeaderTypeName=function() return "LEADER_BAIQI" end}}
PlayersVisibility={[7]={IsRevealed=function() return true end,IsVisible=function() return true end}}
CityManager={CanStartOperation=function() return true end,RequestOperation=function(c,op,params) W.cityRequests[#W.cityRequests+1]=params end}
CityManager.GetCityAt=function() return nil end
CityManager.RequestCommand=function(c,op,params)
 W.cityCommandRequests=W.cityCommandRequests or {}
 W.cityCommandRequests[#W.cityCommandRequests+1]={city=c:GetID(),op=op,params=params}
 return false,nil,'tail',nil
end
UnitManager={CanStartOperation=function() return true end,RequestOperation=function(u,op,params) W.unitRequests[#W.unitRequests+1]={unit=u:GetID(),op=op,params=params} end}
UnitManager.GetQueuedDestination=function()return W.queuedDestination end
UI={GetHeadSelectedCity=function() return nil end,GetHeadSelectedUnit=function() return nil end,
 IsGameCoreBusy=function() return W.busy or false end,IsProcessingMessages=function() return W.processing or false end}
local function event() return {Add=function() end,Remove=function() end} end
Events={UnitOperationStarted=event(),CityProductionCompleted=event()}
TestWorld.objects={builder=builder,settler=settler,army=army,city=city,player=player}
