-- External static-API observation only; native results pass through unchanged.
local function NewQueryCounter(original,names,prefix,getBucket)
  if type(original)~="table" then error("original must be table",0) end
  if type(names)~="table" then error("names must be array",0) end
  if type(prefix)~="string" then error("prefix must be string",0) end
  if type(getBucket)~="function" then error("getBucket must be function",0) end
  local stats={totalCalls=0,callbackErrors=0}
  local proxy={}
  local function Count(key)
    local bucket=getBucket()
    if bucket==nil then return true end
    if type(bucket)~="table" then return false end
    local value=bucket[key]
    if value==nil then
      bucket[key]=1
    elseif type(value)=="number" and value>=0 and value<math.huge and value==math.floor(value) then
      local nextValue=value+1
      if nextValue<=value or nextValue==math.huge then return false end
      bucket[key]=nextValue
    else
      return false
    end
    return true
  end
  for i=1,#names do
    local name=names[i]
    if type(name)~="string" then error("name must be string",0) end
    local fn=original[name]
    if type(fn)~="function" then error("missing function for "..name,0) end
    local key=prefix.."."..name
    proxy[name]=function(...)
      stats.totalCalls=stats.totalCalls+1
      local ok,counted=pcall(Count,key)
      if not ok or counted~=true then stats.callbackErrors=stats.callbackErrors+1 end
      return fn(...)
    end
  end
  setmetatable(proxy,{__index=original})
  return proxy,stats
end
return NewQueryCounter
