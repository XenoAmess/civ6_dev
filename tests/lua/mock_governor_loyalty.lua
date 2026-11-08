-- Actual governor requests queue and apply separately; no synchronous ACK effect.
local w=TestAdmin;local g=w.gov;local cities=g.cities
g.points=6;g.spent=6;g.pressure=8;g.permissionReads=0
g.base={[1]=21,[2]=-6.28125};g.loyalty={[1]=100,[2]=8.828125}
local pg=Players[7]:GetGovernors()
local v={GetType=function()return 3 end,GetNeutralizedTurns=function()return g.neutralized end,
 GetIdentityPressure=function()if g.pressureError then error('unknown pressure')end;return g.pressure end,
 HasPromotion=function()return false end}
v.city=cities[1];v.GetAssignedCity=function()return v.city end;g.owned[930]=v
for i,c in ipairs(cities)do
 local id=i
 c.GetOwner=function()if id==2 and g.foreign then return 8 end;return 7 end
 c.GetPopulation=function()return id==1 and 11 or 2 end
 c.GetCulturalIdentity=function()
  return {GetLoyalty=function()return g.loyalty[id]end,
   GetLoyaltyPerTurn=function()return g.base[id]+(pg:GetAssignedGovernor(c)and g.removal or 0)end,
   GetIdentitySourcesBreakdown=function()
    if g.breakdownError then error('unknown breakdown')end
    return {{Population=g.base[id]},{Governors=pg:GetAssignedGovernor(c)and g.removal or 0}}
   end}
 end
end
g.removal=8
Players[7].GetCities=function()return {
 GetCount=function()return #cities end,FindID=function(_,id)return cities[id]end,
 Members=function()local i=0;return function()i=i+1;if cities[i]then return i,cities[i]end end end}end
local permission=pg.CanAssignGovernor
pg.CanAssignGovernor=function(self,hash,city,report)
 local can=permission(self,hash,city,report)
 if city:GetID()==2 then
  g.permissionReads=g.permissionReads+1
  if g.onPermission then g.onPermission(g.permissionReads)end
 end
 return can
end
local original=UI.RequestPlayerOperation
UI.RequestPlayerOperation=function(pid,operation,params)
 local result=original(pid,operation,params)
 if operation==11 then
  if g.requestError then error('native uncertain')end
  if g.requestFalse then return false end
 end
 return result
end
