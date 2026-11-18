-- Private pure reader. Loading defines functions only; no hooks or game actions.
local M={version=1,marker='domestic-assets992-owner-v1'}
local function num(v)return type(v)=='number' and v==v and math.abs(v)<=9007199254740991 end
local function int(v,lo,hi)return num(v) and v%1==0 and v>=lo and v<=hi end
local function object(v)return type(v)=='table' or type(v)=='userdata' end
local function method(o,k,...)assert(object(o) and type(o[k])=='function','METHOD_'..k);return o[k](o,...)end
local function static(o,k,...)assert(object(o) and type(o[k])=='function','STATIC_'..k);return o[k](...)end
local function number(v)assert(num(v),'NUMBER');return v end
local function integer(v,lo,hi)assert(int(v,lo,hi),'INTEGER');return v end
local function boolean(v)assert(type(v)=='boolean','BOOLEAN');return v end
local function text(v)assert(type(v)=='string' and #v>0 and #v<=256,'TEXT');return v end
local function dense(a,bound)
 assert(type(a)=='table' and getmetatable(a)==nil,'ARRAY');local n=0;local used={}
 for k,v in pairs(a)do n=n+1;assert(int(k,1,bound) and int(v,0,2147483647) and not used[v],'ARRAY_MEMBER');used[v]=true end
 assert(n<=bound and #a==n,'DENSITY');local copy={};for i=1,n do assert(a[i]~=nil,'HOLE');copy[i]=a[i]end;return copy
end
local function ids(collection,pid,bound)
 local expected=integer(method(collection,'GetCount'),0,bound);local out={};local seen={}
 for _,o in collection:Members()do
  assert(#out<bound and method(o,'GetOwner')==pid,'COLLECTION_OWNER');local id=integer(method(o,'GetID'),0,2147483647)
  assert(not seen[id],'DUPLICATE_ID');seen[id]=true;out[#out+1]=id
 end
 assert(#out==expected and method(collection,'GetCount')==expected,'COLLECTION_CHANGED');table.sort(out);return out
end
local function same(a,b)if #a~=#b then return false end;for i=1,#a do if a[i]~=b[i]then return false end end;return true end
local function has(a,id)for _,v in ipairs(a)do if v==id then return true end end;return false end
function M.Read(E,request)
 local out={marker=M.marker,version=M.version,qualified_no_unknowns=false,errors=0,nodes=0,fields={}}
 local seen={};local keys={}
 local function encode(v,depth)
  out.nodes=out.nodes+1;assert(out.nodes<=262144 and depth<=10,'ENCODING_BOUND');local t=type(v)
  if t=='nil'then return{kind='nil'}end
  if t=='boolean'then return{kind=t,value=v}end
  if t=='number'then assert(num(v),'NONFINITE');return{kind=t,value=v}end
  if t=='string'then assert(#v<=4096,'STRING_BOUND');return{kind=t,value=v}end
  assert(t=='table' and getmetatable(v)==nil and not seen[v],'UNSUPPORTED_OR_CYCLE');seen[v]=true
  local order={};for k in pairs(v)do assert(#order<1024 and (type(k)=='string' and #k<=256 or int(k,-2147483648,2147483647)),'TABLE_KEY');order[#order+1]=k end
  table.sort(order,function(a,b)if type(a)~=type(b)then return type(a)=='number'end;return a<b end)
  local items={};for _,k in ipairs(order)do items[#items+1]={key=encode(k,depth+1),value=encode(v[k],depth+1)}end
  seen[v]=nil;return{kind='table',items=items}
 end
 local function put(k,getter)
  assert(not keys[k] and #out.fields<16384,'FIELD_BOUND');keys[k]=true
  -- Local assignment preserves a native zero-return property as explicit nil.
  local ok,v=pcall(function()local value=getter();return encode(value,0)end)
  if not ok then out.errors=out.errors+1;seen={};v={kind='UNKNOWN',reason=tostring(v):sub(1,512)}end
  out.fields[#out.fields+1]={key=k,value=v};return ok
 end
 local ok,err=pcall(function()
  assert(type(E)=='table' and type(request)=='table' and request.playerID==0,'REQUEST_PLAYER0')
  local pid=request.playerID;local turn=integer(request.turn,0,2147483647);local leader=text(request.expectedLeader)
  local citiesWanted=dense(request.cityIDs,64);local unitsWanted=dense(request.unitIDs,256);local plotsWanted=dense(request.plotIDs,256)
  local p=assert(E.Players[pid]);local config=assert(E.PlayerConfigurations[pid])
  assert(static(E.Game,'GetLocalPlayer')==pid and static(E.Game,'GetCurrentGameTurn')==turn,'CONTEXT')
  assert(method(config,'GetLeaderTypeName')==leader and method(p,'IsTurnActive')==true,'LEADER_OR_ACTIVE')
  if config.IsHuman~=nil then assert(method(config,'IsHuman')==true,'HUMAN')else assert(method(p,'IsHuman')==true,'HUMAN_FALLBACK')end
  assert(static(E.GameConfiguration,'IsAnyMultiplayer')==false,'MULTIPLAYER')
  if E.GameConfiguration.IsHotseat~=nil then assert(static(E.GameConfiguration,'IsHotseat')==false,'HOTSEAT')end
  local cities=method(p,'GetCities');local units=method(p,'GetUnits');local cityIDs=ids(cities,pid,64);local unitIDs=ids(units,pid,256)
  local gold=number(method(method(p,'GetTreasury'),'GetGoldBalance'));local faith=number(method(method(p,'GetReligion'),'GetFaithBalance'))
  put('context',function()return{playerID=pid,turn=turn,leader=leader,cityIDs=cityIDs,unitIDs=unitIDs}end)
  put('gold',function()return gold end);put('faith',function()return faith end)
  for _,cid in ipairs(citiesWanted)do
   local prefix='city.'..cid..'.';local city=method(cities,'FindID',cid);assert(has(cityIDs,cid)==(city~=nil),'CITY_LOOKUP_CHANGED')
   put(prefix..'present',function()return city~=nil end)
   if city~=nil then
    assert(method(city,'GetID')==cid and method(city,'GetOwner')==pid,'CITY_FULL_ID')
    for _,k in ipairs({'X','Y','Population'})do put(prefix..k,function()return integer(method(city,'Get'..k),0,2147483647)end)end
    put(prefix..'queue',function()
     local head=E.QueueSnapshot.Queue(E,city);assert(type(head)=='table' and (head.status=='EMPTY' or head.status=='KNOWN'),'QUEUE_HEAD_UNKNOWN')
     local q=method(city,'GetBuildQueue');local count=integer(method(q,'GetSize'),0,7);assert(count==head.size,'QUEUE_SIZE_CHANGED')
     local directives=assert(E.CityProductionDirectives);local rows={}
     for i=0,count-1 do
      local entry=method(q,'GetAt',i);assert(type(entry)=='table','QUEUE_PARTIAL');local found
      for _,spec in ipairs({{'UNIT','TRAIN','UnitType','Units'},{'BUILDING','CONSTRUCT','BuildingType','Buildings'},{'DISTRICT','ZONE','DistrictType','Districts'},{'PROJECT','PROJECT','ProjectType','Projects'}})do
       assert(num(directives[spec[2]]),'QUEUE_DIRECTIVE_PORT')
       if entry.Directive==directives[spec[2]]then
        assert(not found,'DUPLICATE_DIRECTIVE');local index=integer(entry[spec[3]],0,2147483647);local row=assert(E.GameInfo[spec[4]][index]);assert(row.Index==index,'QUEUE_DATABASE_INDEX');found={kind=spec[1],index=index}
       end
      end
      assert(found,'QUEUE_UNKNOWN_DIRECTIVE')
      if i==0 then assert(found.kind==head.kind and found.index==head.index,'QUEUE_HEAD_MISMATCH');if found.kind=='UNIT'then assert(entry.MilitaryFormationType==head.modifier,'QUEUE_FORMATION_MISMATCH')end end
      rows[#rows+1]={slot=i,entry=entry}
     end
     assert((method(q,'GetAt',count))==nil and method(q,'GetSize')==count and method(q,'GetCurrentProductionTypeHash')==head.hash,'QUEUE_CHANGED')
     return{head=head,items=rows}
    end)
    put(prefix..'focus',function()
     local c=method(city,'GetCitizens');local result={}
     for _,yield in ipairs({'FOOD','PRODUCTION','GOLD','SCIENCE','CULTURE','FAITH'})do
      local id=integer(E.YieldTypes[yield],0,2147483647)
      result[#result+1]={yield=yield,index=id,favored=boolean(method(c,'IsFavoredYield',id)),disfavored=boolean(method(c,'IsDisfavoredYield',id))}
     end;return result
    end)
    put(prefix..'citizens',function()
     local t=E.CityCommandTypes;local r=E.CityCommandResults;local parameter=static(E.UI,'GetInterfaceModeParameter',t.PARAM_MANAGE_CITIZEN)
     assert(parameter==nil or type(parameter)=='boolean' or type(parameter)=='string' or num(parameter),'MANAGE_PARAMETER')
     local params={};if parameter~=nil then params[t.PARAM_MANAGE_CITIZEN]=parameter end
     local target=static(E.CityManager,'GetCommandTargets',city,t.MANAGE,params);assert(type(target)=='table','TARGETS')
     local plots,counts,locked=target[r.PLOTS],target[r.CITIZENS],target[r.LOCKED_CITIZENS]
     assert(type(plots)=='table' and type(counts)=='table' and type(locked)=='table','MANAGE_ARRAYS')
     local result={};local present={};local count=0
     for key,id in pairs(plots)do
      count=count+1;assert(count<=128 and int(id,0,2147483647) and not present[id],'MANAGE_PLOT');present[id]=true
      result[#result+1]={key=key,plotID=id,count=integer(counts[key],-1,256),locked=integer(locked[key],-1,256)}
     end
     for key in pairs(counts)do assert(plots[key]~=nil,'EXTRA_CITIZEN_KEY')end
     for key in pairs(locked)do assert(plots[key]~=nil,'EXTRA_LOCK_KEY')end
     table.sort(result,function(a,b)return a.plotID<b.plotID end);return result
    end)
    put(prefix..'purchasedPlots',function()
     local a=method(static(E.Map,'GetCityPlots'),'GetPurchasedPlots',city);assert(type(a)=='table','PURCHASED_PLOTS')
     local result={};local present={}
     for key,id in pairs(a)do assert(#result<128 and int(id,0,2147483647) and not present[id],'PURCHASED_PLOT');present[id]=true;result[#result+1]={key=key,plotID=id}end
     table.sort(result,function(a,b)return a.plotID<b.plotID end);return result
    end)
   end
  end
  for _,uid in ipairs(unitsWanted)do
   local prefix='unit.'..uid..'.';local u=method(units,'FindID',uid);assert(has(unitIDs,uid)==(u~=nil),'UNIT_LOOKUP_CHANGED');put(prefix..'present',function()return u~=nil end)
   if u~=nil then
    assert(method(u,'GetID')==uid and method(u,'GetOwner')==pid,'UNIT_FULL_ID')
    local index
    if u.GetUnitType~=nil then index=integer(method(u,'GetUnitType'),0,2147483647)else index=integer(method(u,'GetType'),0,2147483647)end
    local row=assert(E.GameInfo.Units[index]);assert(row.Index==index,'UNIT_DATABASE_INDEX');local kind=text(row.UnitType)
    put(prefix..'type',function()return{index=index,type=kind}end)
    for _,k in ipairs({'X','Y','MovesRemaining','Damage','FormationUnitCount','BuildCharges'})do put(prefix..k,function()return number(method(u,'Get'..k))end)end
    put(prefix..'cooldown',function()return (method(u,'GetProperty','BAIQI_REQUISITION_TURN'))end)
    if kind=='UNIT_MISSIONARY' or kind=='UNIT_APOSTLE' or kind=='UNIT_INQUISITOR' or kind=='UNIT_GURU'then
     put(prefix..'religion',function()local r=method(u,'GetReligion');return{type=integer(method(r,'GetReligionType'),-1,2147483647),charges=integer(method(r,'GetSpreadCharges'),0,2147483647)}end)
    end
   end
  end
  for _,id in ipairs(plotsWanted)do
   put('plot.'..id,function()
    local plot=assert(static(E.Map,'GetPlotByIndex',id));assert(method(plot,'GetIndex')==id,'PLOT_FULL_ID')
    return{owner=integer(method(plot,'GetOwner'),-1,2147483647),x=integer(method(plot,'GetX'),0,2147483647),y=integer(method(plot,'GetY'),0,2147483647),improvement=integer(method(plot,'GetImprovementType'),-1,2147483647),district=integer(method(plot,'GetDistrictType'),-1,2147483647)}
   end)
  end
  assert(static(E.Game,'GetLocalPlayer')==pid and static(E.Game,'GetCurrentGameTurn')==turn and method(config,'GetLeaderTypeName')==leader and method(p,'IsTurnActive')==true,'CONTEXT_CHANGED')
  assert(same(cityIDs,ids(cities,pid,64)) and same(unitIDs,ids(units,pid,256)),'OWNED_COLLECTION_CHANGED')
  assert(method(method(p,'GetTreasury'),'GetGoldBalance')==gold and method(method(p,'GetReligion'),'GetFaithBalance')==faith,'BALANCES_CHANGED_DURING_READ')
 end)
 if not ok then put('snapshot.failure',function()error(err)end)end
 out.qualified_no_unknowns=out.errors==0
 return out
end
return M
