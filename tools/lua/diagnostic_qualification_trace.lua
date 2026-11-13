-- Bounded QA evidence only. No SDK reads or gameplay operations.
local function NewQualificationTrace(h)
  if type(h)~='table' then return function() return false end,false end
  local maximum=2147483647
  local allowed={turn=true,player=true,active=true,anchor_missing=true,clock=true,
    before_anchor=true,city_before=true,city_after=true,turn_after=true,
    sample_missing=true,anchor_event=true,bind=true,subscribe=true,unsubscribe=true}
  local labels={['Admin.Run']=true,['Controller.RunNow']=true,lifecycle=true}
  local reasons,events={},{}
  local eventCount,dropped,saturated,malformed=0,0,false,false
  local function Finite(v)
    return type(v)=='number' and v==v and v>-math.huge and v<math.huge
  end
  local function Integer(v)
    return Finite(v) and v>=0 and v<=maximum and v==math.floor(v)
  end
  local function Add(v)
    if not Integer(v) then malformed=true;saturated=true;return maximum end
    if v==maximum then saturated=true;return maximum end
    return v+1
  end
  local initialized=pcall(function()
    h.qualificationReasons=reasons;h.qualificationEvents=events
    h.qualificationEventDropped=0;h.qualificationSaturated=false;h.qualificationTraceMalformed=false
  end)
  local function Record(reason,label,turn,knownClock)
    if not initialized then return false end
    local ok=pcall(function()
      h.qualificationErrors=Add(h.qualificationErrors)
      if type(reason)~='string' or not allowed[reason] then reason='unknown' end
      if type(label)~='string' or not labels[label] then label='unknown' end
      local count=reasons[reason]
      if count==nil then count=0 end
      reasons[reason]=Add(count)
      if eventCount<16 then
        eventCount=eventCount+1
        local event={reason=reason,label=label}
        if Integer(turn) then event.turn=turn end
        if Finite(knownClock) then event.clock=knownClock end
        events[eventCount]=event
      else dropped=Add(dropped) end
      if h.qualificationReasons~=reasons or h.qualificationEvents~=events then
        malformed=true
      end
      h.qualificationReasons=reasons;h.qualificationEvents=events
      h.qualificationEventDropped=dropped
      h.qualificationSaturated=saturated
      h.qualificationTraceMalformed=malformed
    end)
    if not ok then
      pcall(function()
        h.qualificationErrors=maximum;h.qualificationTraceMalformed=true;h.qualificationSaturated=true
      end)
    end
    return ok
  end
  return Record,initialized
end

return NewQualificationTrace
