-- Synthetic native-port fixture, not a game outcome or a Native action script.
local w=TestWorld
YieldTypes.FOOD=1
w.created=-1;w.earned=0;w.held=false
w.timeline={{Class=0,Individual=0}}
w.queues={};w.current={};w.completed={};w.placed={};w.qualification={}
w.allowed={[777]=true,[778]=true,[901]=true}
local function rows(data,typeKey)
 local t={}
 for _,r in ipairs(data)do t[r.Index]=r;t[r.Hash]=r;t[r[typeKey]]=r end
 return setmetatable(t,{__call=function()return ipairs(data)end})
end
-- GameInfo generic-for yields rows as its first value, unlike city Members.
local function defs(data,typeKey)
 local t=rows(data,typeKey)
 return setmetatable(t,{__call=function()
  local i=0;return function()i=i+1;return data[i]end
 end})
end
GameInfo.Districts=defs({
 {Index=3,Hash=777,DistrictType='DISTRICT_HOLY_SITE'},
 {Index=4,Hash=778,DistrictType='DISTRICT_CAMPUS'}},'DistrictType')
GameInfo.Buildings=defs({
 {Index=9,Hash=901,BuildingType='BUILDING_WORKSHOP',Maintenance=0},
 {Index=0,Hash=100,BuildingType='BUILDING_GRANARY',Maintenance=0},
 {Index=1,Hash=101,BuildingType='BUILDING_MONUMENT',Maintenance=0}},'BuildingType')
GameInfo.GreatPersonClasses={GREAT_PERSON_CLASS_PROPHET={Index=0,GreatPersonClassType='GREAT_PERSON_CLASS_PROPHET'}}
GameInfo.GreatPersonIndividuals={[0]={Index=0,GreatPersonClassType='GREAT_PERSON_CLASS_PROPHET'}}
local main=w.objects.city
local basePlot=Map.GetPlot(2,3)
w.cities={main,setmetatable({GetID=function()return 67 end,GetX=function()return 3 end},{__index=main})}
w.plots={}
for _,c in ipairs(w.cities)do
 local id=c:GetID();local x=c:GetX()
 local p=setmetatable({GetIndex=function()return id-24 end,GetX=function()return x end,
   GetYield=function(_,kind)assert(kind==YieldTypes.FOOD);return 0 end,
  IsNaturalWonder=function()return false end,IsNationalPark=function()return false end,
  GetDistrictType=function()return -1 end,GetResourceType=function()return -1 end,
  CanHaveDistrict=function(_,index,owner,cityID)
   assert(owner==7 and cityID==id and(index==3 or index==4));return not w.noPlacement
  end},{__index=basePlot})
 w.plots[id-24]=p
 c.GetDistricts=function()return {HasDistrict=function(_,index)
  assert(index==3);if w.districtUnknown then return nil end
  return w.completed[id]==true
 end}end
 c.GetBuildQueue=function()
  local q={}
  function q:GetSize()return #(w.queues[id]or{})end
  function q:GetAt(i)return (w.queues[id]or{})[i+1]end
  function q:GetCurrentProductionTypeHash()return w.current[id]or 0 end
  function q:HasBeenPlaced(hash)
   assert(hash==777 or hash==778)
   return hash==777 and w.placed[id]==true
  end
  function q:CanProduce(hash)return w.allowed[hash]==true end
  return q
 end
end
Map.GetPlotByIndex=function(i)return w.plots[i]end
Map.GetPlot=function(x,y)
 for _,p in pairs(w.plots)do if p:GetX()==x and p:GetY()==y then return p end end
end
Map.GetCityPlots=function()return {GetPurchasedPlots=function(_,c)return {c:GetID()-24}end}end
w.objects.player.GetCities=function()return {
 GetCount=function()return #w.cities end,Members=function()return ipairs(w.cities)end,
 FindID=function(_,id)for _,c in ipairs(w.cities)do if c:GetID()==id then return c end end end}
end
w.objects.player.GetReligion=function()
 if w.throwReligion then error('religion unavailable')end
 return {GetReligionTypeCreated=function()return w.created end,
  GetNumBeliefsEarned=function()return w.earned end,
  HasReligiousFoundingUnit=function()return w.held end}
end
Game.GetGreatPeople=function()return {GetTimeline=function()
 if w.throwTimeline then error('timeline unavailable')end
 return w.timeline
end}end
CityManager.CanStartOperation=function(_,_,params)
 local hash=params[CityOperationTypes.PARAM_DISTRICT_TYPE]or params[CityOperationTypes.PARAM_BUILDING_TYPE]
  or params[CityOperationTypes.PARAM_UNIT_TYPE]or params[CityOperationTypes.PARAM_PROJECT_TYPE]
 w.qualification[hash]=(w.qualification[hash]or 0)+1
 if hash==777 and w.qualification[hash]==2 and w.shock then w.shock()end
 return hash~=777 or not w.noOperation
end
CityManager.RequestOperation=function(c,op,params)
 w.cityRequests[#w.cityRequests+1]={city=c:GetID(),op=op,params=params}
 if w.throwWriter then error('unknown after write')end
end
