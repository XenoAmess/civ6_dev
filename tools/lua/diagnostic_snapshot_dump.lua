-- Read-only detached observation export; never changes the caller's recording.
local function Dump(registry,keys,emit)
  local status={contexts=0,samples=0,anchors=0,writes=0,errors=0}
  local stopped=false
  local function Bad() status.errors=status.errors+1 end
  local function Number(v) return type(v)=='number' and v==v and v>=0 and v<math.huge end
  local function Integer(v) return Number(v) and v==math.floor(v) end
  local function Array(t,limit)
    if type(t)~='table' then Bad();return nil end
    local count,highest=0,0
    for k in pairs(t) do
      count=count+1
      if count>limit or not Integer(k) or k<1 or k>limit then Bad();return nil end
      highest=math.max(highest,k)
    end
    if highest~=count then Bad();return nil end
    return count
  end
  local function Sorted(t,limit,predicate)
    if type(t)~='table' then Bad();return nil end
    local out={}
    for key in pairs(t) do
      if #out>=limit or not predicate(key) then Bad();return nil end
      out[#out+1]=key
    end
    table.sort(out);return out
  end
  local function Emit(...)
    if stopped then return false end
    local ok=pcall(emit,...)
    if not ok then Bad();stopped=true end
    return ok
  end
  if type(emit)~='function' or type(registry)~='table' or registry.marker~='baiqi67-q19'
    or type(registry.entries)~='table' or registry.enabled~=false then Bad();return status end
  local count=Array(keys,80)
  if not count then return status end
  local function Context(key)
    local entry=registry.entries[key]
    if type(entry)~='table' or entry.marker~='baiqi67-q19' or type(entry.Snapshot)~='function' then Bad();return end
    local ok,snap=pcall(entry.Snapshot)
    if not ok or type(snap)~='table' or snap.marker~='baiqi67-q19' or snap.key~=key
      or snap.enabled~=false or snap.retired~=false or type(snap.subscribed)~='boolean' then Bad();return end
    local p,s,l=snap.profile,snap.stats,snap.leaves
    if type(p)~='table' or type(s)~='table' or type(l)~='table' then Bad();return end
    local meta={}
    for _,pair in ipairs({{p,'totalCalls'},{p,'dropped'},{p,'invalidClock'},
      {s,'registryErrors'},{s,'anchorErrors'},{s,'anchorDropped'},{s,'bucketErrors'},{s,'bucketDropped'},
      {l,'entries'},{l,'dropped'},{l,'wrapErrors'},{l,'enabledErrors'}}) do
      local value=pair[1][pair[2]]
      if not Integer(value) then Bad();return end
      meta[#meta+1]=value
    end
    local nc=Array(l.counters,512)
    if not nc then return end
    local ce,ct=0,0
    for i=1,nc do
      local c=l.counters[i]
      if type(c)~='table' or not Integer(c.callbackErrors) or not Integer(c.totalCalls) then Bad();return end
      ce=ce+c.callbackErrors;ct=ct+c.totalCalls
      if not Integer(ce) or not Integer(ct) then Bad();return end
    end
    meta[13]=ce;meta[14]=ct;meta[15]=snap.subscribed;meta[16]=snap.retired
    if not Emit('META',key,unpack(meta,1,16)) then return end
    status.contexts=status.contexts+1
    if p.aggregateZero==true then
      if not Integer(p.zeroSuccess) or not Integer(p.capacity) or p.capacity<1 then Bad();return end
      if not Emit('ZERO',key,p.zeroSuccess,p.capacity) then return end
    end
    local n=Array(p.samples,30000)
    if n then for i=1,n do
      local row=p.samples[i]
      if type(row)~='table' or type(row.name)~='string' or not Number(row.started)
        or not Number(row.ended) or row.ended<row.started or not Number(row.seconds) or type(row.failed)~='boolean' then Bad()
      elseif Emit('SAMPLE',key,i,row.name,row.started,row.ended,row.seconds,row.failed) then status.samples=status.samples+1 end
      if stopped then return end
    end end
    n=Array(snap.anchors,128)
    if n then for i=1,n do
      local row=snap.anchors[i]
      if type(row)~='table' or not Integer(row.pid) or not Integer(row.turn) or not Number(row.time) then Bad()
      elseif Emit('ANCHOR',key,i,row.pid,row.turn,row.time) then status.anchors=status.anchors+1 end
      if stopped then return end
    end end
    local turns=Sorted(snap.buckets,128,Integer)
    if turns then for _,turn in ipairs(turns) do
      local bucket=snap.buckets[turn]
      local apis=Sorted(bucket,512,function(v) return type(v)=='string' end)
      if apis then for _,api in ipairs(apis) do
        if not Integer(bucket[api]) then Bad()
        elseif Emit('WRITE',key,turn,api,bucket[api]) then status.writes=status.writes+1 end
        if stopped then return end
      end end
    end end
  end
  local seen={}
  for i=1,count do
    local key=keys[i]
    if type(key)~='string' or seen[key] then Bad()
    else
      seen[key]=true
      local ok=pcall(Context,key)
      if not ok then Bad() end
    end
    if stopped then break end
  end
  return status
end

return Dump
