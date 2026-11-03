-- Exact Native leaf forwarding; all observations use the canonical counter.
local function NewWriteLeaves(NewCounter,isEnabled,getBucket,limits)
  assert(type(NewCounter)=='function' and type(isEnabled)=='function'
    and type(getBucket)=='function','Invalid leaf observer callbacks')
  if limits~=nil then assert(type(limits)=='table','Invalid leaf limits') end
  local maxEntries=limits and limits.maxEntries
  if maxEntries==nil then maxEntries=512 end
  assert(type(maxEntries)=='number' and maxEntries>=0 and maxEntries<=4096
    and maxEntries==math.floor(maxEntries),'Invalid leaf capacity')
  local stats={entries=0,dropped=0,wrapErrors=0,enabledErrors=0,counters={}}
  local cache={}
  local handle={stats=stats}
  local function Find(label,native,fn,method)
    for i=1,#cache do
      local row=cache[i]
      if row.label==label and row.native==native and row.fn==fn and row.method==method then
        return row.wrapped
      end
    end
  end
  local function Build(label,native,fn,method)
    local existing=Find(label,native,fn,method)
    if existing then return existing end
    local forward=fn
    if method then forward=function(...) return fn(native,...) end end
    if stats.entries>=maxEntries then
      stats.dropped=stats.dropped+1
      return forward
    end
    local ok,proxy,counter=pcall(NewCounter,{Call=forward},{'Call'},label,getBucket)
    if not ok or type(proxy)~='table' or type(proxy.Call)~='function' or type(counter)~='table' then
      stats.wrapErrors=stats.wrapErrors+1
      return forward
    end
    local counted=proxy.Call
    local wrapped=function(...)
      local valid,enabled=pcall(isEnabled)
      if not valid or type(enabled)~='boolean' then
        stats.enabledErrors=stats.enabledErrors+1
        return forward(...)
      end
      if not enabled then return forward(...) end
      return counted(...)
    end
    stats.entries=stats.entries+1
    cache[#cache+1]={label=label,native=native,fn=fn,method=method,wrapped=wrapped}
    stats.counters[#stats.counters+1]=counter
    return wrapped
  end
  function handle:Static(label,fn)
    assert(type(label)=='string','Invalid static label')
    if type(fn)~='function' then return fn end
    return Build(label,nil,fn,nil)
  end
  function handle:Method(label,native,method)
    assert(type(label)=='string' and type(method)=='string','Invalid method label')
    local fn=native[method]
    if type(fn)~='function' then return fn end
    return Build(label,native,fn,method)
  end
  return handle
end

return NewWriteLeaves
