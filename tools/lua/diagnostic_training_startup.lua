-- Passive startup bundle. Existing bounded SDK recorder and production event
-- installer are injected as full reviewed sources by the private package.
return function(E,Recorder,InstallProduction)
 assert(type(E)=='table'and type(Recorder)=='table'and type(Recorder.Install)=='function')
 assert(type(InstallProduction)=='function'and type(E.GetProduction)=='function')
 for _,name in ipairs({'GetCities','GetUnits','GetEvents','GetGame','GetInfo','GetPlayers'})do
  assert(type(E[name])=='function','Missing startup dependency')
 end
 local unpackValues=table.unpack or unpack
 local function Copy(v,depth)
  local kind=type(v)
  if kind~='table'then assert(kind=='nil'or kind=='number'or kind=='boolean'or kind=='string');return v end
  assert(depth<5 and getmetatable(v)==nil)
  local result,n={},0
  for k,x in pairs(v)do n=n+1;assert(n<=1024);assert(type(k)=='number'or type(k)=='string');result[k]=Copy(x,depth+1)end
  return result
 end
 assert(E.GetProduction()==nil,'Production observer namespace occupied')
 local domains={};local retired=false;local ownedProduction
 local events=E.GetEvents();local eventBindings={}
 for _,name in ipairs({'CityProductionCompleted','UnitAddedToMap','CityPopulationChanged'})do
  local event=assert(events[name]);assert(type(event.Add)=='function'and type(event.Remove)=='function')
  eventBindings[name]={event=event,remove=event.Remove}
 end
 local function Facts(object,isUnit)
  local info,players=E.GetInfo(),E.GetPlayers()
  local r={id=object:GetID(),owner=object:GetOwner(),x=object:GetX(),y=object:GetY()}
  if isUnit then
   r.unitType=info.Units[object:GetUnitType()].UnitType
   r.moves=object:GetMovesRemaining();r.formation=object:GetFormationUnitCount()
  else
   local q=object:GetBuildQueue();local row=assert(info.Units.UNIT_SETTLER)
   r.population=object:GetPopulation();r.head=q:GetCurrentProductionTypeHash();r.size=q:GetSize()
   r.settlerIndex=row.Index;r.settlerHash=row.Hash;r.basePopulationCost=row.PopulationCost
   r.settlerProgress=q:GetUnitProgress(row.Index);r.settlerCost=q:GetUnitCost(row.Index)
   local growth=object:GetGrowth()
   r.food=growth:GetFood();r.foodSurplus=growth:GetFoodSurplus();r.growthThreshold=growth:GetGrowthThreshold()
   local player=players[0];local governor=player:GetGovernors():GetAssignedGovernor(object)
   local promotion=info.GovernorPromotions.GOVERNOR_PROMOTION_RESOURCE_MANAGER_EXPEDITION
   if governor then
    r.governor=governor:GetType();r.established=governor:IsEstablished()
    if promotion then r.provision=governor:HasPromotion(promotion.Hash)
    else r.provision='UNAVAILABLE'end
   else r.governor='NONE';r.established='NONE';r.provision='NONE'end
  end
  return Copy(r,0)
 end
 local function Domain(getManager,isUnit)
  local manager=getManager();assert(type(manager)=='table'and type(manager.RequestOperation)=='function')
  local original=manager.RequestOperation;local proxy={RequestCommand=original};local published
  local s=Recorder.Install({getTable=function()return proxy end,getPublished=function()return published end,
   publish=function(v)published=v end,unpack=unpackValues,game=E.GetGame()})
  local inner=proxy.RequestCommand
  local d={filterErrors=0,metadataErrors=0,ignored=0,before={},retired=false}
  local function Matches(object)
   if object:GetOwner()~=0 then return false end
   if not isUnit then return true end
   local row=E.GetInfo().Units[object:GetUnitType()]
   return row and row.UnitType=='UNIT_SETTLER'or false
  end
  local wrapper=function(object,...)
   if d.retired then return original(object,...)end
   local ok,match=pcall(Matches,object)
   if not ok or type(match)~='boolean'then d.filterErrors=d.filterErrors+1;return original(object,...)end
   if not match then d.ignored=d.ignored+1;return original(object,...)end
   local sequence=s.count+1
   if sequence<=256 then
    local row={argumentCount=select('#',...)+1,metadataKnown=false}
    local good,facts=pcall(Facts,object,isUnit)
    if good then row.metadataKnown=true;row.facts=facts else d.metadataErrors=d.metadataErrors+1;row.error=tostring(facts)end
    d.before[sequence]=row
   end
   return inner(object,...)
  end
  manager.RequestOperation=wrapper
  function d.Read()
   return Copy({count=s.count,errors=s.errors,drops=s.drops,samples=s.samples,before=d.before,
    filterErrors=d.filterErrors,metadataErrors=d.metadataErrors,ignored=d.ignored,retired=d.retired,
    binding=getManager()==manager and manager.RequestOperation==wrapper,
    originalBinding=getManager()==manager and manager.RequestOperation==original},0)
  end
  function d.Retire()
   if d.retired then return getManager()==manager and manager.RequestOperation==original end
   if getManager()~=manager or manager.RequestOperation~=wrapper then return false end
   -- Restore both the actual SDK leaf and the recorder's private proxy.
   manager.RequestOperation=original;s.Restore();d.retired=true
   return manager.RequestOperation==original and proxy.RequestCommand==original and published==nil
  end
  domains[#domains+1]=d;return d
 end
 local h={failed=false,cleanupKnown=false,eventRetired=false}
 local function RetireEvents()
  local p=ownedProduction
  if p==nil then h.eventRetired=true;return true end
  p.active=false
  local all=E.GetEvents()==events and E.GetProduction()==p
  for name,entry in pairs(eventBindings)do
   local callback=p.handlers and p.handlers[name]
   if callback and not(entry.removed)then
    if events[name]~=entry.event or entry.event.Remove~=entry.remove then all=false
    else
     local ok,value=pcall(entry.remove,callback)
     if ok and value~=false then entry.removed=true else all=false end
    end
   end
  end
  h.eventRetired=all;return all
 end
 function h.Retire()
  local all=RetireEvents()
  for _,d in ipairs(domains)do if not d.Retire()then all=false end end
  retired=all;h.cleanupKnown=all;return all
 end
 local ok,err=pcall(function()
  h.city=Domain(E.GetCities,false);h.unit=Domain(E.GetUnits,true)
  InstallProduction()
  local p=assert(E.GetProduction());ownedProduction=p
  assert(p.active==true and type(p.rows)=='table'and type(p.handlers)=='table')
 end)
 if not ok then
  if ownedProduction==nil then ownedProduction=E.GetProduction()end
  h.failed=true;h.error=tostring(err);h.Retire()
 end
 function h.Read()
  local p=ownedProduction
  local result={failed=h.failed,error=h.error,retired=retired,cleanupKnown=h.cleanupKnown,eventRetired=h.eventRetired,
   productionBinding=p~=nil and E.GetProduction()==p}
  if h.city then result.city=h.city.Read()end
  if h.unit then result.unit=h.unit.Read()end
  if p then result.production=Copy({rows=p.rows,dropped=p.dropped,errors=p.errors,active=p.active},0)end
  return result
 end
 return h
end
