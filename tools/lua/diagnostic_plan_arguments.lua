-- Isolated argument evidence; does not submit game actions or qualify latency.
local function Install(controller,env,targetTurn)
  local h={active=false,rows={},native_events={},errorCounter=0,droppedCounter=0,
    nativeDropped=0,bindingsRestored=false,subscribed=false}
  local original,wrapper,remove,callback
  local addAttempted,stopAttempted,stopResult=false,false,false
  local function Add(v)return math.min(2147483647,v+1)end
  local function Error()h.errorCounter=Add(h.errorCounter)end
  local function Finite(v)return type(v)=='number'and v==v and v>=0 and v<math.huge end
  local function Turn(v)return Finite(v)and v<=2147483647 and v==math.floor(v)end
  local function Observe(first,n)
    local ok=pcall(function()
      local t=env.GetTurn();assert(Turn(t))
      if t~=targetTurn then return end
      local at=env.Now();assert(Finite(at))
      if #h.rows>=64 then h.droppedCounter=Add(h.droppedCounter);return end
      local row={turn=t,time=at,arg_count=n,first_type=type(first)}
      if type(first)=='boolean'then row.first_boolean=first end
      h.rows[#h.rows+1]=row
    end)
    if not ok then Error()end
  end
  function h.Stop()
    if stopAttempted then return stopResult end
    stopAttempted=true;h.active=false
    local ok=pcall(function()
      if original and controller.RunNow==original then h.bindingsRestored=true
      elseif wrapper and controller.RunNow==wrapper then
        controller.RunNow=original;h.bindingsRestored=controller.RunNow==original
      end
    end)
    if not ok then Error()end
    local removed=not addAttempted
    if addAttempted and type(remove)=='function'then
      removed=pcall(remove,callback)
      if removed then h.subscribed=false else Error()end
    end
    stopResult=ok and removed and h.bindingsRestored
    return stopResult
  end
  local ok=pcall(function()
    assert(type(controller)=='table'and type(controller.RunNow)=='function'and type(env)=='table')
    assert(Turn(targetTurn)and type(env.GetTurn)=='function'and type(env.Now)=='function')
    original=controller.RunNow
    wrapper=function(...)
      if h.active then Observe(select(1,...),select('#',...))end
      return original(...)
    end
    callback=function(pid)
      if not h.active or pid~=0 then return end
      local observed=pcall(function()
        local t=env.GetTurn();assert(Turn(t));if t~=targetTurn then return end
        local at=env.Now();assert(Finite(at))
        if #h.native_events>=8 then h.nativeDropped=Add(h.nativeDropped);return end
        h.native_events[#h.native_events+1]={pid=pid,turn=t,time=at}
      end)
      if not observed then Error()end
    end
    local event=env.Event;local add=event.Add;remove=event.Remove
    assert(type(add)=='function'and type(remove)=='function')
    addAttempted=true;add(callback);h.subscribed=true
    assert(controller.RunNow==original,'Original target changed during subscription')
    controller.RunNow=wrapper;h.active=true
  end)
  if not ok then Error();h.Stop()end
  return h
end

return Install
