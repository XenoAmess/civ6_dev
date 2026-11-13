-- Complete, retained pre-anchor intervals remain pending until a real Native
-- callback supplies the exact anchor. No SDK reads, actions, or invented clock.
local function NewDeferred(profile,anchors,unknown)
  local function Finite(v)return type(v)=='number'and v==v and v>-math.huge and v<math.huge end
  local function Integer(v)return Finite(v)and v>=0 and v<=2147483647 and v==math.floor(v)end
  assert(type(profile)=='table'and type(profile.samples)=='table'and Integer(profile.capacity)
    and profile.capacity>=1 and profile.capacity<=4096 and type(anchors)=='table'and type(unknown)=='function')
  local s={pending=0,recorded=0,validated=0,errors=0}
  local queues,seen={},{}
  local function Error(turn)
    s.errors=math.min(2147483647,s.errors+1)
    pcall(unknown,'before_anchor',turn)
    return false
  end
  local function Proof(row,turn,anchor)
    row.anchor=anchor;row.windowEligible=false
    if row.name~='Controller.RunNow' or row.preAnchor~=true or row.argumentCount~=1
      or row.allowOrders~='false' or row.failed~=false or not Finite(row.started)
      or not Finite(row.ended) or row.ended<row.started or row.started>=anchor
      or row.ended>anchor or row.turnStart~=turn or row.turnEnd~=turn
      or not Integer(row.cityStart) or not Integer(row.cityEnd) then return Error(turn)end
    s.validated=s.validated+1
    return true
  end
  function s:Resolve(turn,anchor)
    local ok,result=pcall(function()
      if not Integer(turn)or turn<86 or turn>90 or not Finite(anchor)
        or anchors[turn]~=anchor then return Error(turn)end
      local q=queues[turn]
      if q==nil then return true end
      queues[turn]=nil
      local valid=true
      for _,row in ipairs(q)do
        s.pending=s.pending-1;seen[row]='resolved'
        if not Proof(row,turn,anchor)then valid=false end
      end
      return valid
    end)
    if not ok then return Error(turn)end
    return result
  end
  function s:Record(row,turn)
    local ok,result=pcall(function()
      if not Integer(turn)or turn<86 or turn>90 or type(row)~='table'
        or row~=profile.samples[#profile.samples] or seen[row]~=nil
        or s.recorded>=profile.capacity or row.name~='Controller.RunNow'
        or row.preAnchor~=true or row.argumentCount~=1 or row.allowOrders~='false' then return Error(turn)end
      s.recorded=s.recorded+1;seen[row]='pending'
      local q=queues[turn]or{};queues[turn]=q;q[#q+1]=row;s.pending=s.pending+1
      local anchor=anchors[turn]
      if anchor~=nil then return s:Resolve(turn,anchor)end
      return true
    end)
    if not ok then return Error(turn)end
    return result
  end
  return s
end

return NewDeferred
