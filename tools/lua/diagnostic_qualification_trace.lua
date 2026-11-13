-- Bounded QA evidence only. No SDK reads or gameplay operations.
local function NewQualificationTrace(h)
  if type(h)~='table' then return function() return false end end
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
  rawset(h,'qualificationReasons',reasons)
  rawset(h,'qualificationEvents',events)
  rawset(h,'qualificationEventDropped',0)
  rawset(h,'qualificationSaturated',false)
  rawset(h,'qualificationTraceMalformed',false)
  return function(reason,label,turn,knownClock)
    local ok=pcall(function()
      rawset(h,'qualificationErrors',Add(rawget(h,'qualificationErrors')))
      if type(reason)~='string' or not allowed[reason] then reason='unknown' end
      if type(label)~='string' or not labels[label] then label='unknown' end
      local count=rawget(reasons,reason)
      if count==nil then count=0 end
      rawset(reasons,reason,Add(count))
      if eventCount<16 then
        eventCount=eventCount+1
        local event={reason=reason,label=label}
        if Integer(turn) then event.turn=turn end
        if Finite(knownClock) then event.clock=knownClock end
        rawset(events,eventCount,event)
      else dropped=Add(dropped) end
      if rawget(h,'qualificationReasons')~=reasons or rawget(h,'qualificationEvents')~=events then
        malformed=true
      end
      rawset(h,'qualificationReasons',reasons);rawset(h,'qualificationEvents',events)
      rawset(h,'qualificationEventDropped',dropped)
      rawset(h,'qualificationSaturated',saturated)
      rawset(h,'qualificationTraceMalformed',malformed)
    end)
    return ok
  end
end

return NewQualificationTrace
