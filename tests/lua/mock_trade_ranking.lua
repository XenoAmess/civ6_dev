-- Independently supplied route geometry, city order and native qualification.
local w=TestWorld;local o=w.objects
w.tradeCityOrder={70,69,68,67,66};w.tradePathQueries={};w.tradeQualifications={}
w.tradeRoutePaths={
 [67]={42,43,44,45},[68]={42,52,53,54,55},
 [69]={42,52,53,56},[70]={42,43,44,45,46,47,48}}
w.tradeHidden={};w.tradeOwners={};w.tradeReads={}
local coords={[42]={2,3},[43]={3,3},[44]={4,3},[45]={5,3},[46]={6,3},[47]={7,3},[48]={8,3},
 [52]={2,4},[53]={2,5},[54]={2,6},[55]={2,7},[56]={3,5}}
local plots,xy={},{}
for index,c in pairs(coords) do
 local id,x,y=index,c[1],c[2]
 local p={GetIndex=function() return id end,GetX=function() return x end,GetY=function() return y end,
  GetOwner=function() return w.tradeOwners[id] or 7 end}
 plots[id]=p;xy[x..':'..y]=p
end
Map.GetPlot=function(x,y) return xy[x..':'..y] end
Map.GetPlotByIndex=function(i) return plots[i] end
Map.GetPlotDistance=function(x,y,x2,y2)
 local dx,dy=x2-x,y2-y
 return (math.abs(dx)+math.abs(dy)+math.abs(dx+dy))/2
end
Map.GetPlotXYWithRangeCheck=function(x,y,dx,dy,r)
 if Map.GetPlotDistance(x,y,x+dx,y+dy)<=r then return Map.GetPlot(x+dx,y+dy) end
end
local cities={[66]=o.city}
for id,index in pairs({[67]=45,[68]=55,[69]=56,[70]=48}) do
 local cid,pid=id,index
 cities[cid]=setmetatable({GetID=function() return cid end,
  GetX=function() return plots[pid]:GetX() end,GetY=function() return plots[pid]:GetY() end,
  GetOwner=function() return w.tradeOwners[pid] or 7 end},{__index=o.city})
 w.queues[cid]={}
end
local byxy={}
for _,city in pairs(cities) do byxy[city:GetX()..':'..city:GetY()]=city end
Cities.GetCityInPlot=function(x,y) return byxy[x..':'..y] end
o.player.GetCities=function()
 return {Members=function()
   local i=0
   return function() i=i+1;local id=w.tradeCityOrder[i];if id then return i,cities[id] end end
  end,GetCount=function() return #w.tradeCityOrder end,FindID=function(_,id) return cities[id] end}
end
Game.GetTradeManager=function() return {GetTradeRoutePath=function(_,pid,origin,pid2,dest)
 assert(pid==7 and pid2==7 and origin==66)
 w.tradePathQueries[#w.tradePathQueries+1]=dest
 if w.tradeOnPath then w.tradeOnPath(dest) end
 return w.tradeRoutePaths[dest],{},{}
end} end
PlayersVisibility[7].IsRevealed=function(_,x,y)
 local p=Map.GetPlot(x,y)
 return p~=nil and not w.tradeHidden[p:GetIndex()]
end
PlayersVisibility[7].IsVisible=PlayersVisibility[7].IsRevealed
local enemy={GetID=function() return 900 end,GetOwner=function() return 8 end,GetUnitType=function() return 0 end}
Units.GetUnitsInPlot=function(p)
 assert(not w.tradeHidden[p:GetIndex()],'Hidden unit information read')
 local id=p:GetIndex();w.tradeReads[id]=(w.tradeReads[id] or 0)+1
 return w.tradeEnemy==id and {enemy} or {}
end
UnitManager.CanStartOperation=function(unit,op,mode,params)
 if op==18 then
  local q={x=params.x0,y=params.y0};w.tradeQualifications[#w.tradeQualifications+1]=q
  if w.tradeOnQualify then return w.tradeOnQualify(q,#w.tradeQualifications) end
 end
 return true
end
