-- Native bindings only. Core metadata and the real Controller are loaded later.
local W=TestWorld
W.queueSize=1
W.withMissionary=false;W.missionaryID=4;W.missionaryOwner=7;W.missionaryType=60
W.unitReligion=1;W.ownReligion=1;W.spreadCharges=3;W.missionaryMoves=4;W.missionaryFormation=1
W.missionaryPlot=42;W.cityMajority=-1;W.cityOwner=7;W.cityID=66
W.secondCityMajority=-1;W.spreadLegal=true;W.withArmy=true;W.spreadRequests={}
GameInfo.Units[60]={UnitType='UNIT_MISSIONARY',Index=60,Hash=600,Combat=0,RangedCombat=0,FormationClass='FORMATION_CLASS_CIVILIAN'}
for index,name in ipairs({'UNIT_APOSTLE','UNIT_INQUISITOR','UNIT_GURU'}) do
 GameInfo.Units[60+index]={UnitType=name,Index=60+index,Hash=600+index,Combat=0,RangedCombat=0,FormationClass='FORMATION_CLASS_CIVILIAN'}
end
GameInfo.UnitOperations={UNITOPERATION_SPREAD_RELIGION={Hash=1592408602,Index=38}}
assert(UnitOperationTypes.SPREAD_RELIGION==nil)
local plots={}
for i=42,44 do
 local x=i-40
 plots[i]={GetIndex=function() return i end,GetX=function() return x end,GetY=function() return 3 end,
  GetOwner=function() return W.plotOwner or 7 end,GetFeatureType=function() return -1 end}
end
Map.GetPlotByIndex=function(index) return plots[index] end
Map.GetPlot=function(x,y) return y==3 and plots[x+40] or nil end
Map.GetPlotDistance=function(x,y,a,b) return math.abs(x-a)+math.abs(y-b) end
local city=W.objects.city
city.GetID=function() return W.cityID end
city.GetOwner=function() return W.cityOwner end
city.GetReligion=function() return {GetMajorityReligion=function() return W.cityMajority end} end
city:GetBuildQueue().HasBeenPlaced=function() return false end
local second={GetID=function() return 67 end,GetOwner=function() return 7 end,
 GetX=function() return 4 end,GetY=function() return 3 end,
 GetReligion=function() return {GetMajorityReligion=function() return W.secondCityMajority end} end,
 GetBuildQueue=function() return city:GetBuildQueue() end,GetPopulation=function() return 1 end,
 GetBuildings=function() return city:GetBuildings() end}
local function members(list)
 return function() local i=0;return function() i=i+1;if list[i] then return i,list[i] end end end
end
W.objects.player.GetCities=function()
 local list=W.withCity and {city} or {}
 if W.secondCity then list[#list+1]=second end
 return {Members=members(list),GetCount=function() return #list end,
  FindID=function(_,id)
   if id==66 and W.withCity then return city end
   if id==67 and W.secondCity then return second end
  end}
end
W.objects.player.GetReligion=function()
 return {GetReligionTypeCreated=function() return W.ownReligion end}
end
local missionary={GetID=function() return W.missionaryID end,GetOwner=function() return W.missionaryOwner end,
 GetUnitType=function() return W.missionaryType end,GetMovesRemaining=function() return W.missionaryMoves end,
 GetFormationUnitCount=function() return W.missionaryFormation end,GetX=function() return plots[W.missionaryPlot]:GetX() end,
 GetY=function() return 3 end,GetReligionType=function() return W.unitReligion end,
 GetSpreadCharges=function() return W.spreadCharges end,IsReadyToMove=function() return W.ready~=false end}
W.objects.missionary=missionary
W.objects.player.GetUnits=function()
 local list={}
 if W.withArmy then list[#list+1]=W.objects.army end
 if W.withMissionary then list[#list+1]=missionary end
 return {Members=members(list),FindID=function(_,id)
  if W.withMissionary and (id==W.missionaryID or W.recycledFind) then return missionary end
  if id==1 and W.withArmy then return W.objects.army end
 end}
end
PlayersVisibility[7].IsVisible=function() return W.visible~=false end
PlayersVisibility[7].IsRevealed=function() return W.revealed~=false end
UnitManager.GetMoveToPathEx=function(unit,target)
 if W.noPath then return nil end
 local direction=target>=W.missionaryPlot and 1 or -1
 local path={};for index=W.missionaryPlot,target,direction do path[#path+1]=index end
 return {plots=path}
end
local nativeCan=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(unit,op,...)
 if op==1592408602 then return W.spreadLegal end
 return nativeCan(unit,op,...)
end
local nativeRequest=UnitManager.RequestOperation
UnitManager.RequestOperation=function(unit,op,params)
 if op==1592408602 then
  if W.onSpread then W.onSpread(unit,op,params) end
  W.spreadRequests[#W.spreadRequests+1]={unit=unit:GetID(),op=op,params=params}
  if W.throwSpread then error('injected unknown spread outcome') end
  if W.autoSpread then W.spreadCharges=W.spreadCharges-1;W.missionaryMoves=0 end
 else return nativeRequest(unit,op,params) end
end
