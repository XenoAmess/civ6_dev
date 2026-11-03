-- External diagnostic only. Object methods keep their real native receiver.
local Unpack=(table and table.unpack) or unpack
local function Pack(...) return {n=select('#',...),...} end
local function Object(value) return type(value)=='table' or type(value)=='userdata' end
local function Bound(native,overrides)
  local methods={}
  return setmetatable({},{
    __index=function(_,key)
      if overrides and overrides[key] then return overrides[key] end
      local value=native[key]
      if type(value)~='function' then return value end
      local prior=methods[key]
      if not prior or prior.original~=value then
        prior={original=value,call=function(_,...) return value(native,...) end}
        methods[key]=prior
      end
      return prior.call
    end,
    __newindex=function(_,key,value) native[key]=value end
  })
end

local function InstallCultureWrites(env,newCounter,getBucket,pid)
  assert(type(env)=='table' and type(env.Players)=='table','invalid Players environment')
  assert(type(newCounter)=='function' and type(getBucket)=='function','invalid counter')
  assert(type(Unpack)=='function','missing unpack')
  assert(type(pid)=='number' and pid>=0 and pid<=2147483647 and pid%1==0,'invalid player ID')
  local original=env.Players
  local active=true
  local stats={players=0,cultures=0,missing=0,wrapErrors=0,droppedPlayers=0,droppedCultures=0,counters={}}
  local playerCache,cultureCache={},{}
  local names={'RequestChangeGovernment','SetGovernmentChangeConsidered','RequestPolicyChanges'}

  local function Culture(native)
    if cultureCache[native] then return cultureCache[native] end
    if stats.cultures>=128 then stats.droppedCultures=stats.droppedCultures+1;return native end
    for _,name in ipairs(names) do
      if type(native[name])~='function' then stats.missing=stats.missing+1;return native end
    end
    local facade=Bound(native)
    local counter,count=newCounter(facade,names,'Culture',getBucket)
    assert(type(counter)=='table' and type(count)=='table','invalid counter result')
    for _,name in ipairs(names) do assert(type(counter[name])=='function','missing counter method') end
    local selected={}
    for _,name in ipairs(names) do
      local counted,plain=counter[name],facade[name]
      selected[name]=function(...)
        if active then return counted(...) end
        return plain(...)
      end
    end
    local proxy=Bound(native,selected)
    stats.cultures=stats.cultures+1
    stats.counters[#stats.counters+1]=count
    cultureCache[native]=proxy
    return proxy
  end

  local function Player(native)
    if playerCache[native] then return playerCache[native] end
    if stats.players>=16 then stats.droppedPlayers=stats.droppedPlayers+1;return native end
    if type(native.GetCulture)~='function' then stats.missing=stats.missing+1;return native end
    local overrides={}
    overrides.GetCulture=function(_,...)
      -- Getter errors propagate directly; only diagnostic wrapping is isolated.
      local values=Pack(native.GetCulture(native,...))
      if not active then return Unpack(values,1,values.n) end
      if Object(values[1]) then
        local ok,result=pcall(Culture,values[1])
        if ok then values[1]=result else stats.wrapErrors=stats.wrapErrors+1 end
      else
        stats.missing=stats.missing+1
      end
      return Unpack(values,1,values.n)
    end
    local proxy=Bound(native,overrides)
    stats.players=stats.players+1
    playerCache[native]=proxy
    return proxy
  end

  local proxy=setmetatable({},{
    __index=function(_,key)
      local native=original[key]
      if not active or key~=pid then return native end
      if not Object(native) then stats.missing=stats.missing+1;return native end
      local ok,result=pcall(Player,native)
      if ok then return result end
      stats.wrapErrors=stats.wrapErrors+1
      return native
    end,
    __newindex=function(_,key,value) original[key]=value end
  })
  local handle={original=original,proxy=proxy,stats=stats}
  function handle:Restore()
    active=false
    if env.Players~=proxy then return false end
    env.Players=original
    return true
  end
  env.Players=proxy
  return handle
end
return InstallCultureWrites
