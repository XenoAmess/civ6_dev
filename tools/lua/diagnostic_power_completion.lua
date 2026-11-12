-- Own completion callbacks are best-effort observations, not planner inputs or
-- atomic snapshots. Only this observer's two subscriptions may be changed.
local M={}
local function finite(v)return type(v)=='number'and v==v and v~=math.huge and v~=-math.huge end
local function integer(v)return finite(v)and v>=0 and v<=2147483647 and v%1==0 end
local fields={'freePower','temporaryPower','requiredPower','fullyPowered','activeProject',
  'coal','oil','uranium','queueHash','queueSize','busy','messages'}

function M.Install(E)
  assert(type(E)=='table'and getmetatable(E)==nil,'plain environment required')
  local G,GC,UI=assert(E.Game),assert(E.GameConfiguration),assert(E.UI)
  local players,cfgs=assert(E.Players),assert(E.PlayerConfigurations)
  local ids=E.cityIDs;assert(type(ids)=='table'and getmetatable(ids)==nil,'plain city list required')
  local count=0
  for key in pairs(ids)do
    count=count+1;assert(count<=64 and integer(key)and key>=1 and key<=64,'bounded dense list required')
  end
  assert(count>=1,'empty city list')
  local listed,targets={},{}
  for i=1,count do
    local id=ids[i];assert(integer(id)and not listed[id],'unique finite city IDs required')
    listed[id]=true;targets[i]=id
  end
  local maximum,first,last=E.maxRecords,E.minTurn,E.maxTurn
  assert(integer(maximum)and maximum>=1 and maximum<=128,'invalid record limit')
  assert(integer(first)and integer(last)and first<=last,'invalid turn range')
  local function scope(id)
    assert(G.GetLocalPlayer()==0 and GC.IsAnyMultiplayer()==false,'local scope changed')
    local t=G.GetCurrentGameTurn();assert(integer(t)and t>=first and t<=last,'turn unavailable')
    local cfg=assert(cfgs[0]);assert(cfg:IsHuman()==true and cfg:GetLeaderTypeName()=='LEADER_BAIQI','actor changed')
    local p=assert(players[0]);local city=assert(p:GetCities():FindID(id))
    assert(city:GetID()==id and city:GetOwner()==0,'city scope changed')
    return p,t,city
  end
  for i=1,count do scope(targets[i])end
  local eventFamily=assert(E.Events)
  local bindings={}
  for _,kind in ipairs({'CityProductionCompleted','CityProjectCompleted'})do
    local event=assert(eventFamily[kind]);local add,remove=event.Add,event.Remove
    assert(type(add)=='function'and type(remove)=='function','event ports unavailable')
    bindings[#bindings+1]={kind=kind,add=add,remove=remove}
  end
  local samples={}
  local h={samples=samples,matches=0,errors=0,drops=0,removeErrors=0,active=false,restored=false}
  local active,stored,restoreAttempted,restoreResult=false,0,false,false
  local function read(city,p)
    local power=assert(city:GetPower());local resources=assert(p:GetResources());local queue=assert(city:GetBuildQueue())
    local r={freePower=power:GetFreePower(),temporaryPower=power:GetTemporaryPower(),requiredPower=power:GetRequiredPower(),
      fullyPowered=power:IsFullyPowered(),activeProject=power:IsFullyPoweredByActiveProject(),
      coal=resources:GetResourceAmount('RESOURCE_COAL'),oil=resources:GetResourceAmount('RESOURCE_OIL'),
      uranium=resources:GetResourceAmount('RESOURCE_URANIUM'),queueHash=queue:GetCurrentProductionTypeHash(),
      queueSize=queue:GetSize(),busy=UI.IsGameCoreBusy(),messages=UI.IsProcessingMessages()}
    for _,key in ipairs({'freePower','temporaryPower','requiredPower','coal','oil','uranium'})do
      assert(finite(r[key])and r[key]>=0,'unavailable numeric read')
    end
    for _,key in ipairs({'fullyPowered','activeProject','busy','messages'})do assert(type(r[key])=='boolean','unavailable boolean read')end
    assert(finite(r.queueHash)and r.queueHash%1==0,'unavailable signed hash')
    assert(integer(r.queueSize)and r.queueSize<=128,'unavailable queue size')
    return r
  end
  for _,binding in ipairs(bindings)do
    local kind=binding.kind
    binding.callback=function(playerID,cityID)
      if not active or playerID~=0 or not integer(cityID)or not listed[cityID]then return end
      -- Match/cap accounting does not call into native code.
      h.matches=h.matches+1
      if stored>=maximum then h.drops=h.drops+1;return end
      local ok,row=pcall(function()
        local p,t,city=scope(cityID)
        local a,b=read(city,p),read(city,p)
        for _,key in ipairs(fields)do assert(a[key]==b[key],'state changed across reads')end
        local p2,t2=scope(cityID);assert(p2==p and t2==t,'scope changed across reads')
        a.eventKind=kind;a.turn=t;a.cityID=cityID;a.status='KNOWN'
        return a
      end)
      if not ok then
        h.errors=h.errors+1
        row={eventKind=kind,cityID=cityID,status='UNKNOWN',reason='scope_or_snapshot_unavailable_or_changed'}
      end
      stored=stored+1;samples[stored]=row
    end
  end
  function h.Restore()
    if restoreAttempted then return restoreResult end
    restoreAttempted=true;active=false;h.active=false
    local good=true
    for _,binding in ipairs(bindings)do
      local ok,result=pcall(binding.remove,binding.callback)
      if not ok or result==false then good=false;h.removeErrors=h.removeErrors+1 end
    end
    restoreResult=good;h.restored=good
    return good
  end
  local attempted={}
  for _,binding in ipairs(bindings)do
    attempted[#attempted+1]=binding
    local ok,result=pcall(binding.add,binding.callback)
    if not ok or result==false then
      active=false;h.active=false
      local cleanupErrors=0
      for _,entry in ipairs(attempted)do
        local cleaned,value=pcall(entry.remove,entry.callback)
        if not cleaned or value==false then cleanupErrors=cleanupErrors+1 end
      end
      error('Observer Add uncertain; disabled callbacks; cleanup_errors='..cleanupErrors)
    end
  end
  active=true;h.active=true
  return h
end
return M
