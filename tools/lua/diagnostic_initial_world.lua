-- Private passive observer: no requests, game setters or controller invocations.
return function(E,controller)
 assert(type(E)=='table'and type(controller)=='table')
 local names={'RunNow','Update'};local original,wrappers={},{}
 for _,name in ipairs(names)do assert(type(controller[name])=='function');original[name]=controller[name]end
 local unpackValues=table.unpack or unpack
 local function Pack(...)return{n=select('#',...),...}end
 local s={active=true,retired=false,calls={RunNow=0,Update=0},captureCalls=0,errors={},foreign={},complete=false}
 local function ByHash(info,hash)
  local n=0
  for row in info()do n=n+1;assert(n<=2048);if row.Hash==hash then return row end end
 end
 local function Snapshot(phase,geometry)
  local pid=E.Game.GetLocalPlayer();assert(pid==0)
  local config=assert(E.PlayerConfigurations[pid]);assert(config:GetLeaderTypeName()=='LEADER_BAIQI'and config:IsHuman()==true)
  local player=assert(E.Players[pid]);local cities=player:GetCities()
  local r={phase=phase,turn=E.Game.GetCurrentGameTurn(),player=pid,leader=config:GetLeaderTypeName(),human=true,cities={},units={}}
  if type(cities.GetCapitalCity)=='function'then r.capitalGetterKnown=true;local capital=cities:GetCapitalCity();r.capitalID=capital and capital:GetID()else r.capitalGetterKnown=false end
  for _,city in cities:Members()do
   assert(#r.cities<32);local q=city:GetBuildQueue();local n=q:GetSize();local entry={id=city:GetID(),owner=city:GetOwner(),x=city:GetX(),y=city:GetY(),population=city:GetPopulation(),queueSize=n,headHash=q:GetCurrentProductionTypeHash()}
   if n>0 then
    local row=ByHash(E.GameInfo.Buildings,entry.headHash)
    if row then entry.kind='BUILDING';entry.type=row.BuildingType;entry.index=row.Index;entry.progress=q:GetBuildingProgress(row.Index);entry.cost=q:GetBuildingCost(row.Index)
    else row=ByHash(E.GameInfo.Units,entry.headHash);if row then entry.kind='UNIT';entry.type=row.UnitType;entry.index=row.Index;entry.progress=q:GetUnitProgress(row.Index);entry.cost=q:GetUnitCost(row.Index)end end
   end
   r.cities[#r.cities+1]=entry
  end
  table.sort(r.cities,function(a,b)return a.id<b.id end)
  local settlers={}
  for _,unit in player:GetUnits():Members()do
   assert(#r.units<256);local row=assert(E.GameInfo.Units[unit:GetUnitType()]);local u={id=unit:GetID(),owner=unit:GetOwner(),type=row.UnitType,x=unit:GetX(),y=unit:GetY(),moves=unit:GetMovesRemaining(),formation=unit:GetFormationUnitCount()}
   if row.UnitType=='UNIT_SETTLER'then
    local p=assert(E.Map.GetPlot(u.x,u.y));u.plot=p:GetIndex();u.visible=E.PlayersVisibility[pid]:IsVisible(u.x,u.y);u.revealed=E.PlayersVisibility[pid]:IsRevealed(u.x,u.y)
    u.nativeCanFound=E.UnitManager.CanStartOperation(unit,E.UnitOperationTypes.FOUND_CITY,nil,false,E.OperationResultsTypes.ALL)
    settlers[#settlers+1]=u
   end
   r.units[#r.units+1]=u
  end
  table.sort(r.units,function(a,b)return a.id<b.id end)
  if geometry then
   r.visiblePlots={};local seen={}
   for _,u in ipairs(settlers)do for x=u.x-4,u.x+4 do for y=u.y-4,u.y+4 do
    local plot=E.Map.GetPlot(x,y)
    if plot then local px,py=plot:GetX(),plot:GetY();if E.PlayersVisibility[pid]:IsVisible(px,py)and E.PlayersVisibility[pid]:IsRevealed(px,py)then
     local index=plot:GetIndex();if not seen[index]then seen[index]=true;assert(#r.visiblePlots<256);r.visiblePlots[#r.visiblePlots+1]={index=index,x=px,y=py,owner=plot:GetOwner(),city=plot:IsCity(),water=plot:IsWater(),terrain=plot:GetTerrainType(),feature=plot:GetFeatureType(),resource=plot:GetResourceType(),improvement=plot:GetImprovementType()}end
    end end
   end end end
   table.sort(r.visiblePlots,function(a,b)return a.index<b.index end)
  end
  return r
 end
 local function Capture(phase)
  if not s.active or s.complete or s.captureCalls>=128 then return end
  s.captureCalls=s.captureCalls+1
  local ok,r=pcall(Snapshot,phase,s.initial==nil)
  if not ok then if #s.errors<16 then s.errors[#s.errors+1]=tostring(r)end;return end
  if not s.initial then s.initial=r;E.print('BAIQI_INITIAL173_PASSIVE_INITIAL',r.phase,r.turn,#r.cities,#r.units,r.capitalGetterKnown,tostring(r.capitalID))end
  if not s.firstCity and #r.cities>0 then s.firstCity=r;E.print('BAIQI_INITIAL173_PASSIVE_CITY',r.phase,r.turn,#r.cities,tostring(r.capitalID))end
  if not s.production then for _,city in ipairs(r.cities)do if city.queueSize>0 then s.production=r;E.print('BAIQI_INITIAL173_PASSIVE_PRODUCTION',r.phase,r.turn,city.id,city.headHash,city.kind,city.progress,city.cost);break end end end
  s.complete=s.initial~=nil and s.firstCity~=nil and s.production~=nil
 end
 for _,name in ipairs(names)do
  local key=name;local native=original[key]
  wrappers[key]=function(...)
   s.calls[key]=s.calls[key]+1;Capture('before_'..key)
   local result=Pack(native(...));Capture('after_'..key)
   return unpackValues(result,1,result.n)
  end
  controller[key]=wrappers[key]
 end
 local api={}
 function api.Read()return s end
 function api.Retire()
  s.active=false;local known=true
  for _,name in ipairs(names)do
   if controller[name]==wrappers[name]then controller[name]=original[name]
   elseif controller[name]~=original[name]then known=false;s.foreign[name]=true end
  end
  s.retired=known;return known
 end
 return api
end
