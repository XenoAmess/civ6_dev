local MARKER='baiqi67-paired-clock-v1'
local function IsInt(v) return type(v)=='number' and v>=0 and v<=2147483647 and v==math.floor(v) end
local function IsFinite(v) return type(v)=='number' and v==v and v>=0 and v<math.huge end
local function New(clock,getTurn,getLocal,event,capacity)
  assert(type(clock)=='function' and type(getTurn)=='function' and type(getLocal)=='function','Invalid clock/turn/local functions')
  assert(type(event)=='table' or type(event)=='userdata','Invalid event')
  local add,remove=event.Add,event.Remove
  assert(type(add)=='function' and type(remove)=='function','Invalid event methods')
  assert(IsInt(capacity) and capacity>=1 and capacity<=128,'Invalid capacity')
  local records,pending,errors,refused,subscribed,retired={},nil,0,0,false,false
  local callback
  local function OnTurn(pid)
    if retired or not pending or pid~=pending.pid then return end
    local ok,ended=pcall(clock)
    if not ok or not IsFinite(ended) then errors=errors+1;pending=nil;return end
    local okT,turn=pcall(getTurn)
    if not okT or not IsInt(turn) or turn~=pending.to_turn then errors=errors+1;pending=nil;return end
    local delta=ended-pending.started
    if not IsFinite(delta) or delta<0 then errors=errors+1;pending=nil;return end
    if #records>=capacity then errors=errors+1;pending=nil;return end
    records[#records+1]={from_turn=pending.from_turn,to_turn=pending.to_turn,pid=pending.pid,started=pending.started,ended=ended,seconds=delta}
    pending=nil
  end
  callback=OnTurn
  local okAdd=pcall(add,callback)
  if okAdd then subscribed=true else errors=errors+1 end
  local retireResult
  local h={marker=MARKER,capacity=capacity}
  function h:WrapActivation(fn)
    assert(type(fn)=='function','Invalid native activation callback')
    return function(...)
      local ok=pcall(OnTurn,...)
      if not ok then errors=errors+1;pending=nil end
      return fn(...)
    end
  end
  function h:Begin(turn)
    if retired or not subscribed or errors>0 or pending~=nil or #records>=capacity or not IsInt(turn) or turn>=2147483647 then refused=refused+1;return false end
    local okT,actualTurn=pcall(getTurn)
    if not okT or not IsInt(actualTurn) or actualTurn~=turn then errors=errors+1;return false end
    local okL,localPid=pcall(getLocal)
    if not okL or not IsInt(localPid) then errors=errors+1;return false end
    local okC,started=pcall(clock)
    if not okC or not IsFinite(started) then errors=errors+1;return false end
    pending={from_turn=turn,to_turn=turn+1,pid=localPid,started=started}
    return true
  end
  function h:Snapshot()
    return {marker=MARKER,capacity=capacity,records=records,pending=pending,errors=errors,refused=refused,subscribed=subscribed,retired=retired}
  end
  function h:Retire()
    if retired then return retireResult end
    retired=true;subscribed=false
    local okR=pcall(remove,callback)
    retireResult=okR
    if not okR then errors=errors+1 end
    return okR
  end
  return h
end
return New
