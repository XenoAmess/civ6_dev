-- Real controller consumers with independently supplied native hints and paths.
local w=TestWorld;local o=w.objects
w.pathQueries={};w.cityCopies=1;w.builderRecommendations={43,44,45}
w.settlementRecommendations={46,47};w.hidden={};w.fogged={};w.siteOwners={};w.settlerPlot=42
local coords={[42]={2,3},[43]={3,3},[44]={2,4},[45]={2,5},[46]={8,3},[47]={8,4},[48]={7,3},[50]={9,3},
 [60]={4,3},[61]={5,3},[62]={6,3},[70]={3,4},[71]={4,4},[72]={5,4},[73]={6,4},[74]={7,4}}
local plots,xy={},{}
for index,c in pairs(coords) do
 local id,x,y=index,c[1],c[2]
 local p={GetIndex=function() return id end,GetX=function() return x end,GetY=function() return y end,
  GetOwner=function() if w.siteOwners[id]~=nil then return w.siteOwners[id] end
   return (id==46 or id==47 or id==48 or id==50) and -1 or 7 end,
  GetFeatureType=function() return -1 end,IsWater=function() return false end,IsImpassable=function() return false end,
  IsCity=function() return false end,IsImprovementPillaged=function() return false end,GetImprovementType=function() return -1 end}
 plots[id]=p;xy[x..':'..y]=p
end
Map.GetPlotByIndex=function(index) return plots[index] end
Map.GetPlot=function(x,y) return xy[x..':'..y] end
Map.GetPlotDistance=function(x,y,x2,y2)
 local dx,dy=x2-x,y2-y;return (math.abs(dx)+math.abs(dy)+math.abs(dx+dy))/2
end
Map.GetPlotXYWithRangeCheck=function(x,y,dx,dy,r)
 if Map.GetPlotDistance(x,y,x+dx,y+dy)<=r then return Map.GetPlot(x+dx,y+dy) end
end
PlayersVisibility[7].IsRevealed=function(_,x,y) local p=Map.GetPlot(x,y);return p~=nil and not w.hidden[p:GetIndex()] end
PlayersVisibility[7].IsVisible=function(_,x,y) local p=Map.GetPlot(x,y);return p~=nil and not w.hidden[p:GetIndex()] and not w.fogged[p:GetIndex()] end
local enemy={GetID=function() return 900 end,GetOwner=function() return 8 end,GetUnitType=function() return 0 end}
Units.GetUnitsInPlot=function(p)
 if w.fogged[p:GetIndex()] then error('hidden unit information queried') end
 return p:GetIndex()==w.enemyPlot and {enemy} or {}
end
o.player.GetDiplomacy=function() return {IsAtWarWith=function(_,pid) return pid==8 end} end
o.city.GetCityAI=function() return {GetImprovementRecommendationsForBuilder=function()
 local r={};for _,id in ipairs(w.builderRecommendations) do r[#r+1]={ImprovementLocation=id} end;return r
end} end
local function members(list) return function() local i=0;return function() i=i+1;if list[i] then return i,list[i] end end end end
o.player.GetCities=function()
 local cities={}
 if w.withCity then for i=1,w.cityCopies do
  local id=65+i;cities[#cities+1]=setmetatable({GetID=function() return id end},{__index=o.city})
 end end
 return {Members=members(cities),GetCount=function() return #cities end,FindID=function(_,id)
  for _,c in ipairs(cities) do if c:GetID()==id then return c end end
 end}
end
o.player.GetGrandStrategicAI=function() return {GetSettlementRecommendations=function()
 local r={};for _,id in ipairs(w.settlementRecommendations) do r[#r+1]={SettlingLocation=id} end;return r
end} end
PlayerManager={GetAliveIDs=function() return {7} end}
o.settler.GetX=function() return plots[w.settlerPlot]:GetX() end
o.settler.GetY=function() return plots[w.settlerPlot]:GetY() end
o.settler.GetPlotId=function() return w.settlerPlot end
local second=setmetatable({GetID=function() return 4 end},{__index=o.settler})
o.player.GetUnits=function()
 local list={o.army};if w.withBuilder then list[#list+1]=o.builder end
 if w.withSettler then list[#list+1]=o.settler;if w.secondSettler then list[#list+1]=second end end
 return {Members=members(list),FindID=function(_,id) for _,u in ipairs(list) do if u:GetID()==id then return u end end end}
end
w.paths={[43]={42,43},[44]={42,44},[45]={42,44,45},[46]={42,43,60,61,62,48,46},
 [47]={42,44,70,71,72,73,74,47},[48]={42,43,60,61,62,48},[50]={42,43,60,61,62,48,46,50}}
UnitManager.GetMoveToPathEx=function(unit,index)
 w.pathQueries[#w.pathQueries+1]={unit=unit:GetID(),target=index}
 local path=w.paths[index];if path==false then return nil end
 return {plots=path or {index}}
end
UnitManager.CanStartOperation=function(_,op,_,params)
 if op==UnitOperationTypes.BUILD_IMPROVEMENT or op==UnitOperationTypes.REPAIR then return false end
 if op==UnitOperationTypes.MOVE_TO and w.rejectMoveX and params and params[14]==w.rejectMoveX then return false end
 return true
end
