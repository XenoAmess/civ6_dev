-- Extend the existing blocked-building adapter with a visible hostile occupant.
local w=TestWorld
w.blockedPillaged=false;w.occupiedVisible=true;w.occupiedWar=true
w.occupiedID=501;w.occupiedOwner=8;w.occupiedType=70
w.occupiedComplete=true;w.occupiedDead=false;w.occupiedDelayed=false
w.occupiedX=3;w.occupiedY=3
local row={Index=70,Hash=970,UnitType='UNIT_ARCHER',Combat=15,RangedCombat=25,Domain='DOMAIN_LAND'}
GameInfo.Units[70]=row;GameInfo.Units[970]=row;w.occupiedDefinition=row
local plot={GetIndex=function()return 43 end,GetX=function()return 3 end,GetY=function()return 3 end,
 GetOwner=function()return w.occupiedPlotOwner or 7 end,GetDistrictType=function()return 4 end}
local getPlot,getIndex=Map.GetPlot,Map.GetPlotByIndex
Map.GetPlot=function(x,y)if x==3 and y==3 then return plot end;return getPlot(x,y)end
Map.GetPlotByIndex=function(index)if index==43 then return plot end;return getIndex(index)end
local enemy={GetOwner=function()return w.occupiedOwner end,GetID=function()return w.occupiedID end,
 GetUnitType=function()return w.occupiedType end,GetX=function()return w.occupiedX end,GetY=function()return w.occupiedY end,
 IsDead=function()return w.occupiedDead end,IsDelayedDeath=function()return w.occupiedDelayed end}
w.occupiedEnemy=enemy
local list=Units.GetUnitsInPlot
Units.GetUnitsInPlot=function(p)
 if p==plot then if w.occupiedUnitsUnknown then return nil end;return {enemy}end
 return list(p)
end
local vis=PlayersVisibility[7]
local visible,revealed=vis.IsVisible,vis.IsRevealed
vis.IsVisible=function(self,x,y)if x==3 and y==3 then return w.occupiedVisible end;return visible(self,x,y)end
vis.IsRevealed=function(self,x,y)if x==3 and y==3 then return w.occupiedRevealed~=false end;return revealed(self,x,y)end
local player=Players[7]
player.GetDiplomacy=function()return {IsAtWarWith=function(_,owner)
 if owner==w.occupiedOwner then return w.occupiedWar end;return false
end}end
for _,city in ipairs(w.cities)do
 local gd=city.GetDistricts
 city.GetDistricts=function()
  local districts=gd()
  local component={GetType=function()return 4 end,GetID=function()return w.occupiedDistrictID or 9010 end,
   GetX=function()return 3 end,GetY=function()return 3 end,
   IsComplete=function()return w.occupiedComplete end,IsPillaged=function()return w.blockedPillaged end}
  districts.Members=function()
   if w.throwOccupiedDistricts then error('district list unavailable')end
   local values=w.occupiedDuplicate and {component,component}or {component};local i=0
   return function()i=i+1;if values[i]then return i,values[i]end end
  end
  return districts
 end
end
