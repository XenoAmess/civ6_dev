-- Delayed route/production consumers for the shipped Controller.
local w=TestWorld
local o=w.objects
w.queueSize=1;w.tradeCapacity=1;w.activeRoutes=0;w.activity=100;w.tradeFormation=1
w.traderMoves=2;w.traderPlot=42;w.routes={};w.withTrader=true;w.routePath={42,43}
ActivityTypes={ACTIVITY_AWAKE=100}
UnitOperationTypes.MAKE_TRADE_ROUTE=18
UnitOperationTypes.PARAM_X0='x0';UnitOperationTypes.PARAM_Y0='y0'
UnitOperationTypes.PARAM_X1='x1';UnitOperationTypes.PARAM_Y1='y1'
local traderRow={UnitType='UNIT_TRADER',Hash=203,Index=3,Combat=0,Maintenance=0}
GameInfo.Projects=setmetatable({[301]={ProjectType='PROJECT_TEST',Hash=301,Index=0},
 [0]={ProjectType='PROJECT_TEST',Hash=301,Index=0}},
 {__call=function(t) local done=false;return function() if not done then done=true;return t[301] end end end})
local oldUnits=GameInfo.Units
local unitRows={oldUnits[0],oldUnits[1],oldUnits[2],traderRow}
GameInfo.Units=setmetatable({},{__index=function(_,key)
 for _,r in ipairs(unitRows) do if key==r.Index or key==r.Hash or key==r.UnitType then return r end end
end,__call=function() local i=0;return function() i=i+1;return unitRows[i] end end})
local function members(list)
 return function() local i=0;return function() i=i+1;if list[i] then return i,list[i] end end end
end
local function plot(index,x)
 return {GetIndex=function() return index end,GetX=function() return x end,GetY=function() return 3 end,
  GetOwner=function() return w.pathForeign and index==43 and 8 or 7 end}
end
local plots={[42]=plot(42,2),[43]=plot(43,3)}
Map.GetPlotByIndex=function(i) return plots[i] end
Map.GetPlot=function(x) return plots[x==2 and 42 or 43] end
local city=o.city
local destination=setmetatable({GetID=function() return 67 end,GetX=function() return 3 end,
 GetOwner=function() return w.destForeign and 8 or 7 end},{__index=city})
local cities={city,destination}
Cities={GetCityInPlot=function(x) return x==2 and city or destination end}
function city:GetTrade() return {GetOutgoingRoutes=function() return w.routes end} end
function o.player:GetCities()
 return {Members=members(cities),GetCount=function() return #cities end,
  FindID=function(_,id) for _,c in ipairs(cities) do if c:GetID()==id then return c end end end}
end
function o.player:GetTrade()
 return {GetNumOutgoingRoutes=function() return w.activeRoutes end,GetOutgoingRouteCapacity=function() return w.tradeCapacity end}
end
function o.player:GetTreasury() return {GetGoldBalance=function() return 100 end,GetGoldYield=function() return 6 end,
 GetTotalMaintenance=function() return 0 end} end
local function trader(id)
 return {GetUnitType=function() return 3 end,GetOwner=function() return 7 end,GetID=function() return id end,
  GetPlotId=function() return w.traderPlot end,GetX=function() return w.traderPlot==42 and 2 or 3 end,
  GetY=function() return 3 end,GetMovesRemaining=function() return w.traderMoves end,
  GetFormationUnitCount=function() return w.tradeFormation end}
end
local t1,t2=trader(4),trader(5)
function o.player:GetUnits()
 local list={o.army}
 if w.withTrader then list[#list+1]=t1 end
 if w.secondTrader then list[#list+1]=t2 end
 for i=1,w.extraArmy or 0 do
  list[#list+1]=setmetatable({GetID=function() return 10+i end},{__index=o.army})
 end
 return {Members=members(list),FindID=function(_,id) for _,u in ipairs(list) do if u:GetID()==id then return u end end end}
end
Game.GetTradeManager=function() return {GetTradeRoutePath=function() return w.routePath,{},{} end} end
UnitManager.GetActivityType=function() return w.activity end
UnitManager.CanStartOperation=function(_,op) return not (op==18 and w.nativeReject) end
UnitManager.RequestOperation=function(u,op,params)
 w.unitRequests[#w.unitRequests+1]={unit=u:GetID(),op=op,params=params}
end
UI.IsGameCoreBusy=function() return w.busy or false end
UI.IsProcessingMessages=function() return w.processing or false end
PlayersVisibility[7].IsRevealed=function(_,x) return not (w.pathHidden and x==3) end
PlayersVisibility[7].IsVisible=function() return not w.fogged end
Units.GetUnitsInPlot=function(p)
 w.unitVisibilityReads=(w.unitVisibilityReads or 0)+1
 return w.enemy and {o.army} or {}
end
local enemyOwner=o.army.GetOwner
o.army.GetOwner=function() return w.enemy and 8 or enemyOwner() end
function o.player:GetDiplomacy() return {IsAtWarWith=function(_,pid) return pid==8 end} end
Map.GetPlotXYWithRangeCheck=function(x,y,dx,dy) if dx==0 and dy==0 then return Map.GetPlot(x,y) end end
w.objects.trader=t1
w.objects.destination=destination

-- A production queue only changes when the test accepts an actual packet.
w.queues={[66]={},[67]={}}
function city:GetBuildQueue()
 local id=self:GetID()
 return {GetSize=function() return w.productionMode and #w.queues[id] or 1 end,
  GetCurrentProductionTypeHash=function()
   local e=w.queues[id][1]
   if not e then return 0 end
   local row=e.UnitType and GameInfo.Units[e.UnitType] or (e.ProjectType and GameInfo.Projects[301])
   return row and row.Hash or 0
  end,
  GetAt=function(_,index) return w.queues[id][index+1] end,
  CanProduce=function(_,hash)
   if w.blockSecondCity and id==67 then return false end
   return w.productionMode and (hash==(w.productionHash or 203) or (w.allowProject and hash==301))
  end}
end
CityManager.RequestOperation=function(c,op,params)
 w.cityRequests[#w.cityRequests+1]={city=c:GetID(),op=op,params=params}
end

function w.EnableSettlerSite()
 local site={GetIndex=function() return 44 end,GetX=function() return 8 end,GetY=function() return 3 end,
  GetOwner=function() return -1 end,GetFeatureType=function() return -1 end,
  IsWater=function() return false end,IsImpassable=function() return false end,IsCity=function() return false end}
 plots[44]=site
 Map.GetPlotDistance=function(x,y,x2,y2) return math.abs(x-x2) end
 PlayerManager={GetAliveIDs=function() return {7} end}
 function o.player:GetGrandStrategicAI()
  return {GetSettlementRecommendations=function() return {{SettlingLocation=44}} end}
 end
 city.GetPopulation=function() return 4 end
end
