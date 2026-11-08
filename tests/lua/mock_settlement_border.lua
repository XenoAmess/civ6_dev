-- Public map-cell and owned-city oracles. Foreign rosters are deliberately private.
local w=TestWorld;local o=w.objects
w.withSettler=true;w.withBuilder=false;w.queueSize=1
w.settlementRecommendations={47};w.foreign=true;w.ownX=0;w.ownY=0
local originalPlot,originalByIndex=Map.GetPlot,Map.GetPlotByIndex
local extra={}
local function add(index,x,y,foreign)
 local p={GetIndex=function()return index end,
  GetX=function()return index==200 and w.foreignX or x end,
  GetY=function()return index==200 and w.foreignY or y end,GetOwner=function()
   if foreign and w.foreign and((index==201)==(w.nearForeign==true))then return 8 end
   return -1
  end,GetFeatureType=function()return -1 end,IsWater=function()return false end,
  IsImpassable=function()return false end,GetImprovementType=function()return -1 end,
  IsImprovementPillaged=function()return false end}
 p.IsCity=function()
  if foreign then
   assert(not w.hidden[index]and not w.fogged[index],'HiddenForeignCityFlagRead')
   if w.unknownCityFlag then return nil end
   return w.foreign and((index==201)==(w.nearForeign==true))or false
  end
  return false
 end
 extra[index]=p
end
add(90,0,0,false);add(200,12,4,true);add(201,11,4,true)
Map.GetPlot=function(x,y)
 for _,p in pairs(extra)do if p:GetX()==x and p:GetY()==y then return p end end
 return originalPlot(x,y)
end
Map.GetPlotByIndex=function(id)
 if id==200 and w.badNeighbor then return extra[201]end
 return extra[id]or originalByIndex(id)
end
o.city.GetX=function()return w.ownX end
o.city.GetY=function()return w.ownY end
local counts=o.player.GetCities
o.player.GetCities=function(...)
 local collection=counts(...)
 if w.emptyOwnInventory then collection.Members=function()return function()end end end
 return collection
end
Players[8]={GetCities=function()error('ForeignCityRosterRead')end}
PlayerManager.GetAliveIDs=function()return{7,8}end
w.cityQueries=0
CityManager.GetCityAt=function(x,y)
 local p=Map.GetPlot(x,y)
 assert(p and not w.hidden[p:GetIndex()]and not w.fogged[p:GetIndex()],
   'HiddenForeignCityLookup')
 w.cityQueries=w.cityQueries+1
 if w.lookupThrows then error('NativeCityLookupUnavailable')end
 local id=p:GetIndex()
 if(id==200 or id==201)and w.foreign and((id==201)==(w.nearForeign==true))then
  if w.lookupMissing then return nil end
  return{GetID=function()return w.badCityID and -1 or 600+id end,
   GetOwner=function()return 8 end,
   GetX=function()return w.wrongCityCoordinates and x+1 or x end,
   GetY=function()return y end}
 end
end
