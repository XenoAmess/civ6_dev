-- Passive, context-local getter trace. Never infer that an engine queue is empty.
local M={}
local function Pack(...)return {n=select("#",...),...}end
local function Finite(v)return type(v)=="number"and v==v and math.abs(v)<math.huge end
local function Integer(v)return Finite(v)and v>=0 and v<=2147483647 and v%1==0 end
local function Scalar(v)
  return type(v)=="boolean"or(type(v)=="string"and #v<=4096)or Finite(v)
end
local function CopySnapshot(value)
  assert(type(value)=="table"and getmetatable(value)==nil,"Invalid snapshot")
  assert(Integer(value.id)and value.owner==0 and value.unitType=="UNIT_BUILDER","Invalid actor")
  local copy,n={},0
  for k,v in pairs(value)do
    n=n+1
    assert(n<=32 and type(k)=="string"and #k>=1 and #k<=64 and Scalar(v),"Invalid snapshot field")
    copy[k]=v
  end
  return copy
end
function M.Install(o)
  assert(type(o)=="table")
  for _,k in ipairs({"getManager","getPublished","publish","unpack","scope","snapshot"})do
    assert(type(o[k])=="function","Missing observer port")
  end
  local maxRecords=o.maxRecords
  if maxRecords==nil then maxRecords=128 end
  assert(Integer(maxRecords)and maxRecords>=1 and maxRecords<=4096,"Invalid maxRecords")
  assert(o.getPublished()==nil,"Observer namespace occupied")
  local manager=o.getManager()
  assert(type(manager)=="table"and type(manager.GetQueuedDestination)=="function")
  local original=manager.GetQueuedDestination
  local s={calls=0,errors=0,ignored=0,drops=0,reentrant=0,samples={},maxRecords=maxRecords}
  local sensing=false
  local function Capture(args,result)
    local turn=o.scope()
    if turn==nil then s.ignored=s.ignored+1;return end
    assert(Integer(turn),"Invalid scope turn")
    local snapshot=o.snapshot(args[1])
    if snapshot==nil then s.ignored=s.ignored+1;return end
    local actor=CopySnapshot(snapshot)
    if #s.samples>=maxRecords then s.drops=s.drops+1;return end
    local record={turn=turn,snapshot=actor,returnCount=result.n,values={},valueTypes={},
      truncated=result.n>4,nonScalarReturn=false}
    for i=1,math.min(4,result.n)do
      local v=result[i]
      record.valueTypes[i]=type(v)
      if Scalar(v)then record.values[i]=v
      elseif v~=nil then record.nonScalarReturn=true end
    end
    s.samples[#s.samples+1]=record
  end
  local wrapper=function(...)
    s.calls=s.calls+1
    local args=Pack(...)
    -- An original exception propagates before the diagnostic guard is entered.
    local result=Pack(original(...))
    if sensing then s.reentrant=s.reentrant+1
    else
      sensing=true
      local ok=pcall(Capture,args,result)
      sensing=false
      if not ok then s.errors=s.errors+1 end
    end
    return o.unpack(result,1,result.n)
  end
  local function Owned()
    assert(o.getManager()==manager,"Foreign API table preserved")
    assert(o.getPublished()==s,"Foreign namespace preserved")
    assert(manager.GetQueuedDestination==wrapper,"Foreign binding preserved")
  end
  function s.Restore()
    Owned()
    local ok,err=pcall(function()
      manager.GetQueuedDestination=original
      o.publish(nil)
      assert(o.getPublished()==nil,"Namespace removal not retained")
      assert(o.getManager()==manager and manager.GetQueuedDestination==original,"Foreign binding preserved")
    end)
    if not ok then
      -- Retry is possible only while all remaining state is still ours.
      local known,published=pcall(o.getPublished)
      local same,current=pcall(o.getManager)
      if known and published==s and same and current==manager and manager.GetQueuedDestination==original then
        manager.GetQueuedDestination=wrapper
      end
      error(err,0)
    end
    s.restored=true
    return true
  end
  local ok,err=pcall(function()
    assert(manager.GetQueuedDestination==original)
    manager.GetQueuedDestination=wrapper
    o.publish(s)
    Owned()
  end)
  if not ok then
    if manager.GetQueuedDestination==wrapper then manager.GetQueuedDestination=original end
    local known,published=pcall(o.getPublished)
    if known and published==s then pcall(o.publish,nil)end
    error(err,0)
  end
  return s
end
return M
