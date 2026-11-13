-- QA timing transitions only. The caller qualifies its capture and fixed window.
-- An unknown result may leave some flags changed: stop global recording, never
-- replay or guess a rollback. No game action, counter reset, or event is issued.
local MARKER='baiqi67-q19'
local function Integer(v)return type(v)=='number'and v>=0 and v<math.huge and v==math.floor(v)end
local function Clock(v)return type(v)=='number'and v==v and v>=0 and v<math.huge end
local function Apply(registry,keys,enabled,turn,getTurn,emit)
  local ok,count=pcall(function()
    assert(type(enabled)=='boolean'and Integer(turn)and type(getTurn)=='function'and type(emit)=='function')
    assert(type(registry)=='table'and registry.marker==MARKER and registry.enabled==true
      and type(registry.entries)=='table'and type(keys)=='table'and getmetatable(keys)==nil)
    local n,maximum=0,0
    for k in pairs(keys)do
      n=n+1;assert(n<=80 and Integer(k)and k>=1 and k<=80);maximum=math.max(maximum,k)
    end
    assert(n>0 and n==maximum)
    local entries=registry.entries
    local items,seen={},{}
    for i=1,n do
      local key=keys[i];assert(type(key)=='string'and #key>0 and not seen[key]);seen[key]=true
      local e=entries[key]
      assert(type(e)=='table'and e.marker==MARKER and type(e.Snapshot)=='function'
        and type(e.SetTimingEnabled)=='function'and type(e.ReadClock)=='function')
      items[i]={key=key,entry=e,snapshot=e.Snapshot,set=e.SetTimingEnabled,clock=e.ReadClock}
    end
    local actual=0;for k in pairs(entries)do actual=actual+1;assert(actual<=80 and seen[k])end
    assert(actual==n)
    local function Bound(v)
      if registry.entries~=entries then return false end
      local count=0;for k in pairs(entries)do count=count+1;if count>n or not seen[k]then return false end end
      return count==n and registry.marker==MARKER and registry.enabled==true and getTurn()==turn
        and entries[v.key]==v.entry and v.entry.marker==MARKER and v.entry.Snapshot==v.snapshot
        and v.entry.SetTimingEnabled==v.set and v.entry.ReadClock==v.clock
    end
    local function State(v,flag,changes)
      assert(Bound(v));local s=v.snapshot()
      assert(type(s)=='table'and s.marker==MARKER and s.key==v.key and s.enabled==true
        and s.subscribed==true and s.retired==false and s.timingEnabled==flag and type(s.stats)=='table')
      local c=s.stats.timingChanges;assert(Integer(c)and c<=128 and (changes==nil or c==changes))
      assert(Bound(v));return c
    end
    -- Qualify every entry before changing any of them; copy all bindings/counts.
    for _,v in ipairs(items)do v.before=State(v,not enabled);assert(v.before<=127)end
    for _,v in ipairs(items)do
      assert(State(v,not enabled,v.before)==v.before)
      local a=v.clock();assert(Clock(a)and Bound(v))
      assert(v.set(enabled)==true)
      State(v,enabled,v.before+1)
      local z=v.clock();assert(Clock(z)and z>=a and Bound(v))
      assert(emit(v.key,turn,enabled,a,z)~=false)
      assert(Bound(v))
    end
    for _,v in ipairs(items)do State(v,enabled,v.before+1)end
    return n
  end)
  if ok then return true,count end
  return nil,'unknown'
end
return Apply
