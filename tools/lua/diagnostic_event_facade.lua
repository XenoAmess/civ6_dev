-- File-local subscription facade. Keep it for the diagnostic context lifetime.
-- Every matching removal must use this facade or its captured Remove closure.
local function Object(value) return type(value)=='table' or type(value)=='userdata' end
local function Limit(value,default)
  if value==nil then return default end
  assert(type(value)=='number' and value>=0 and value<=4096 and value%1==0,'invalid event cache limit')
  return value
end
local function NewEventFacade(nativeFamily,wrapCallback,prefix,limits)
  assert(type(wrapCallback)=='function' and type(prefix)=='string','invalid event wrapper')
  assert(limits==nil or type(limits)=='table','invalid event limits')
  local maxEvents=Limit(limits and limits.maxEvents,128)
  local maxCallbacks=Limit(limits and limits.maxCallbacks,512)
  local stats={events=0,callbacks=0,wrappedCallbacks=0,wrapErrors=0,probeErrors=0,droppedEvents=0,droppedCallbacks=0}
  if nativeFamily==nil then stats.unavailable=true;return nil,stats end
  assert(Object(nativeFamily),'invalid native event family')
  local cache={}

  local function Event(key,native,add,remove)
    local versions=cache[key]
    if versions then
      for _,entry in ipairs(versions) do if entry.native==native then return entry.proxy end end
    end
    if stats.events>=maxEvents then stats.droppedEvents=stats.droppedEvents+1;return native end
    local callbacks={}
    local function Add(fn,...)
      if type(fn)~='function' then return add(fn,...) end
      local callback=callbacks[fn]
      if callback==nil then
        if stats.callbacks>=maxCallbacks then
          stats.droppedCallbacks=stats.droppedCallbacks+1
          return add(fn,...)
        end
        local ok,wrapped=pcall(function() return wrapCallback(prefix..'.'..tostring(key),fn) end)
        callback=fn
        if ok and type(wrapped)=='function' then
          callback=wrapped;stats.wrappedCallbacks=stats.wrappedCallbacks+1
        else
          stats.wrapErrors=stats.wrapErrors+1
        end
        -- Cache fallback identities too. A later Add must not change identity.
        callbacks[fn]=callback;stats.callbacks=stats.callbacks+1
      end
      return add(callback,...)
    end
    local function Remove(fn,...)
      local callback=type(fn)=='function' and callbacks[fn] or nil
      return remove(callback or fn,...)
    end
    local proxy=setmetatable({},{
      __index=function(_,name)
        if name=='Add' then return Add end
        if name=='Remove' then return Remove end
        return native[name]
      end,
      __newindex=function(_,name,value) native[name]=value end,
      __call=function(_,...) return native(...) end
    })
    if not versions then versions={};cache[key]=versions end
    versions[#versions+1]={native=native,proxy=proxy}
    stats.events=stats.events+1
    return proxy
  end

  local family=setmetatable({},{
    __index=function(_,key)
      local native=nativeFamily[key]
      if not Object(native) then return native end
      local ok,add,remove=pcall(function() return native.Add,native.Remove end)
      if not ok then stats.probeErrors=stats.probeErrors+1;return native end
      if type(add)~='function' or type(remove)~='function' then return native end
      return Event(key,native,add,remove)
    end,
    __newindex=function(_,key,value) nativeFamily[key]=value end,
    __call=function(_,...) return nativeFamily(...) end
  })
  return family,stats
end
return NewEventFacade
