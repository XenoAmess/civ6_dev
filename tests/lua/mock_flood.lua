-- Synthetic native ports. This fixture never models barrier drainage effects.
function InstallFlood(cities,pid)
  TestFlood={has=false,barrierPillaged=false,complete=true,pillaged=true,low=2,
    flooded=true,submerged=false,visible=true,revealed=true,count=1,terrainReads=0,owner=pid}
  local w=TestFlood
  if not cities then
    cities={{GetID=function()return 66 end,GetOwner=function()return w.owner end,
      GetX=function()return 2 end,GetY=function()return 3 end}}
    Players[pid].GetCities=function()return {Members=function()return ipairs(cities)end,
      FindID=function(_,id)if id==66 then return cities[1]end end}end
  end
  w.cities=cities
  local b={Index=113,Hash=913,BuildingType='BUILDING_FLOOD_BARRIER',PrereqTech='TECH_COMPUTERS',Maintenance=0}
  w.definition=b
  local old=GameInfo.Buildings
  GameInfo.Buildings=setmetatable({[113]=b,[913]=b,BUILDING_FLOOD_BARRIER=b},{__index=old,
    __call=function()local f=old and old();local done=false;return function()
      local r=f and f();if r then return r end;if not done then done=true;return b end end end})
  for _,city in ipairs(cities)do
    local oldBuildings,oldDistricts=city.GetBuildings,city.GetDistricts
    city.GetBuildings=function(self)
      local previous=oldBuildings and oldBuildings(self)or{}
      return {HasBuilding=function(_,i)if i==113 then return w.has end;return previous.HasBuilding and previous:HasBuilding(i)or false end,
        IsPillaged=function(_,i)if i==113 then return w.barrierPillaged end;return previous.IsPillaged and previous:IsPillaged(i)or false end}
    end
    city.GetDistricts=function(self)
      local d=oldDistricts and oldDistricts(self)or{}
      d.Members=function()local i=0;return function()
        i=i+1;if i<=w.count then return i,{IsComplete=function()return w.complete end,IsPillaged=function()return w.pillaged end,
          GetX=function()return city:GetX()end,GetY=function()return city:GetY()end}end end end
      return d
    end
  end
  Map=Map or {GetPlot=function(x,y)return {GetX=function()return x end,GetY=function()return y end,GetOwner=function()return w.owner end}end}
  PlayersVisibility=PlayersVisibility or{}
  PlayersVisibility[pid]={IsVisible=function()return w.visible end,IsRevealed=function()return w.revealed end}
  TerrainManager={GetCoastalLowlandType=function()
    w.terrainReads=w.terrainReads+1;if w.shock then w.shock()end;if w.throwTerrain then error('native terrain')end;return w.low end,
    IsFlooded=function()return w.flooded end,IsSubmerged=function()return w.submerged end}
  return w
end
