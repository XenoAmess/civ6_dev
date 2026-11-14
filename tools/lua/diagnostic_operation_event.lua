-- External passive observer only; never included by the playable mod.
local function Integer(v,lo,hi)
  return type(v)=='number' and v==v and v>=lo and v<=hi and v==math.floor(v)
end
local function New(env,capacity)
  assert(type(env)=='table' and Integer(capacity,1,4096),'Invalid observer configuration')
  for _,name in ipairs({'Add','Remove','Now','GetLocal','GetTurn'}) do
    assert(type(env[name])=='function','Missing observer dependency')
  end
  local h={samples={},capacity=capacity,seen=0,ignored=0,invalid=0,dropped=0,
           errors=0,enabled=false,subscribed=false,retired=false,cleanupKnown=true,
           structuralInvalid=0,unexpectedArity=0}
  local function Count(key)h[key]=math.min(2147483647,h[key]+1)end
  local function Record(...)
    local argc=select('#',...)
    local ownerID,unitID,operationID=...
    if not Integer(ownerID,0,2147483647) then Count('invalid');Count('structuralInvalid');return end
    local pid=env.GetLocal()
    if pid~=0 then Count('invalid');Count('structuralInvalid');return end
    if ownerID~=pid then Count('ignored');return end
    if not Integer(unitID,0,2147483647)
      or not Integer(operationID,-2147483648,4294967295) then Count('invalid');Count('structuralInvalid');return end
    local turn,now=env.GetTurn(),env.Now()
    if not Integer(turn,0,2147483647) or type(now)~='number'
      or now~=now or now<0 or now>=math.huge then Count('invalid');Count('structuralInvalid');return end
    local types={}
    for i=1,math.min(argc,8)do types[i]=type((select(i,...)))end
    local qualified=argc==3
    if not qualified then Count('invalid');Count('unexpectedArity')end
    if #h.samples>=capacity then Count('dropped');return end
    local values,lengths={},{}
    for i=1,math.min(argc,8)do
      local value=select(i,...)
      if types[i]=='number' or types[i]=='boolean' then values[i]=value
      elseif types[i]=='string' then
        lengths[i]=#value;values[i]=string.sub(value,1,256)
      end
    end
    h.samples[#h.samples+1]={ownerID=ownerID,unitID=unitID,operationID=operationID,
      turn=turn,time=now,argc=argc,qualified=qualified,argtypes=types,
      argvalues=values,arglengths=lengths}
  end
  local function Observer(...)
    if not h.enabled then return end
    Count('seen')
    if not pcall(Record,...) then Count('errors')end
  end
  local attempted=false
  local retired,result=false,false
  function h.Retire()
    if retired then return result end
    retired=true;h.retired=true;h.enabled=false
    if not attempted then result=true;return result end
    local ok=pcall(env.Remove,Observer)
    h.cleanupKnown=ok
    if ok then h.subscribed=false else h.subscribed=nil;Count('errors')end
    result=ok
    return result
  end
  attempted=true;h.subscribed=nil;h.cleanupKnown=false
  if pcall(env.Add,Observer) then
    h.subscribed=true;h.enabled=true
  else
    Count('errors');h.Retire()
  end
  return h
end
return New
