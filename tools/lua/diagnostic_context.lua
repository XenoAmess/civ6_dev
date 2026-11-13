-- Private diagnostic lifetime only; not imported by the release package.
local MARKER='baiqi67-q19'
local function Integer(v)
  return type(v)=='number' and v>=0 and v<math.huge and v==math.floor(v)
end
local function Finite(v)
  return type(v)=='number' and v==v and v>=0 and v<math.huge
end
local function NewContext(key,env,NewProfile,NewRoots,NewCounter,NewLeaves)
  assert(type(key)=='string' and key~='' and type(env)=='table','Invalid diagnostic context')
  local clock=env.Automation and env.Automation.GetTime
  local getTurn=env.Game and env.Game.GetCurrentGameTurn
  local capacity=env.SampleQuota
  if capacity==nil then capacity=30000 end
  local aggregate=env.AggregateZero==true
  local root=NewRoots(NewProfile,clock,capacity,{aggregate_zero=aggregate})
  local quotaAllowed=env.UnknownQuota~=true
  local enabled,retired=false,false
  local timingEnabled=true
  local buckets,anchors={},{}
  local bucketCount=0
  local stats={registryErrors=0,anchorErrors=0,anchorDropped=0,bucketErrors=0,bucketDropped=0,timingChanges=0}
  if not quotaAllowed then stats.registryErrors=stats.registryErrors+1 end
  local function Bucket()
    local ok,turn=pcall(getTurn)
    if not ok or not Integer(turn) then stats.bucketErrors=stats.bucketErrors+1;return nil end
    if buckets[turn] then return buckets[turn] end
    if bucketCount>=128 then stats.bucketDropped=stats.bucketDropped+1;return nil end
    buckets[turn]={};bucketCount=bucketCount+1
    return buckets[turn]
  end
  local leaves=NewLeaves(NewCounter,function() return enabled end,Bucket,{maxEntries=512})
  local h={marker=MARKER,key=key,profile=root.profile,Leaves=leaves,stats=stats}
  local subscribed=false
  local remove,callback,registry,entry
  function h:Wrap(label,fn) return root:Wrap(label,fn) end
  function h:SetEnabled(value)
    assert(type(value)=='boolean','Invalid diagnostic record flag')
    if retired then return false end
    if value and not quotaAllowed then return false end
    enabled=value;root:SetEnabled(enabled and timingEnabled);return true
  end
  -- Only function timing changes. Native write buckets and activation anchors
  -- continue to follow enabled for the entire turn.
  function h:SetTimingEnabled(value)
    assert(type(value)=='boolean','Invalid diagnostic timing flag')
    if retired then return false end
    if value~=timingEnabled then
      if stats.timingChanges>=128 then return false end
      stats.timingChanges=stats.timingChanges+1
    end
    timingEnabled=value;root:SetEnabled(enabled and timingEnabled);return true
  end
  function h:Snapshot()
    return {key=key,marker=MARKER,profile=root.profile,leaves=leaves.stats,
      buckets=buckets,anchors=anchors,stats=stats,enabled=enabled,retired=retired,subscribed=subscribed,
      timingEnabled=timingEnabled}
  end
  function h:Reset()
    assert(not enabled,'Disable diagnostic recording before Reset')
    local p=root.profile
    p.samples={};p.totalCalls=0;p.dropped=0;p.invalidClock=0
    p.zeroSuccess=0
    buckets={};anchors={};bucketCount=0
    stats.anchorErrors=0;stats.anchorDropped=0;stats.bucketErrors=0;stats.bucketDropped=0
    stats.timingChanges=0
    for _,c in ipairs(leaves.stats.counters) do c.totalCalls=0;c.callbackErrors=0 end
  end
  function h:Retire()
    enabled=false;root:SetEnabled(false);retired=true
    if subscribed then
      local ok=pcall(remove,callback)
      if ok then subscribed=false else stats.anchorErrors=stats.anchorErrors+1 end
    end
    if registry and entry and registry.entries[key]==entry then registry.entries[key]=nil end
    return not subscribed
  end
  local ok=pcall(function()
    local exposed=env.ExposedMembers
    if type(exposed)~='table' then error('Missing ExposedMembers',0) end
    local candidate=exposed.P6BaiqiOwnRegistry
    if candidate==nil then
      candidate={marker=MARKER,entries={},enabled=false}
      exposed.P6BaiqiOwnRegistry=candidate
    end
    assert(type(candidate)=='table' and candidate.marker==MARKER
      and type(candidate.entries)=='table' and type(candidate.enabled)=='boolean','Foreign diagnostic registry')
    local prior=candidate.entries[key]
    if prior~=nil then
      assert(type(prior)=='table' and prior.marker==MARKER and type(prior.Retire)=='function','Foreign diagnostic entry')
      assert(prior.Retire()==true,'Prior diagnostic anchor not retired')
      assert(candidate.entries[key]==nil,'Diagnostic entry ownership changed')
    end
    local count=0
    for _ in pairs(candidate.entries) do count=count+1 end
    assert(count<80,'Diagnostic registry full')
    registry=candidate
    entry={marker=MARKER,Snapshot=function() return h:Snapshot() end,
      SetEnabled=function(v) return h:SetEnabled(v) end,SetTimingEnabled=function(v) return h:SetTimingEnabled(v) end,
      Reset=function() return h:Reset() end,
      Retire=function() return h:Retire() end,ReadClock=function() return clock() end}
    registry.entries[key]=entry
  end)
  if not ok then stats.registryErrors=stats.registryErrors+1;return h end
  callback=function(pid)
    if not enabled then return end
    local valid,turn=pcall(getTurn)
    local timed,at=pcall(clock)
    if not valid or not Integer(turn) or not timed or not Finite(at) or not Integer(pid) then
      stats.anchorErrors=stats.anchorErrors+1;return
    end
    if #anchors>=128 then stats.anchorDropped=stats.anchorDropped+1;return end
    anchors[#anchors+1]={pid=pid,turn=turn,time=at}
  end
  local hooked=pcall(function()
    local event=env.Events.PlayerTurnActivated
    local add=event.Add
    remove=event.Remove
    assert(type(add)=='function' and type(remove)=='function','Missing Native anchor methods')
    subscribed=true
    add(callback)
  end)
  if not hooked then stats.anchorErrors=stats.anchorErrors+1 end
  h:SetEnabled(registry.enabled)
  return h
end

return NewContext
