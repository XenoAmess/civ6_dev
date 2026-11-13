-- Owned lifecycle for an independent private planning-function experiment.
local function Finite(v)
  return type(v)=='number' and v==v and v>-math.huge and v<math.huge
end

local function NewPlanA(env,NewProfile,WrapWindow,NewTrace)
  local h={source='baiqi140-stageA-v1',enabled=false,anchors={},qualificationErrors=0,
    bound=false,retired=false,subscribed=false,anchorCount=0}
  if type(NewTrace)=='function' then
    local ready
    h.RecordUnknown,ready=NewTrace(h)
    if ready~=true then h.qualificationErrors=h.qualificationErrors+1 end
  else h.RecordUnknown=function() h.qualificationErrors=h.qualificationErrors+1 end end
  local function Unknown(reason,turn,clock) h.RecordUnknown(reason,'lifecycle',turn,clock) end
  h.profile=NewProfile(function() return env.Automation.GetTime() end,4096)
  local ports={
    Now=function() return env.Automation.GetTime() end,
    Turn=function() return env.Game.GetCurrentGameTurn() end,
    LocalPlayer=function() return env.Game.GetLocalPlayer() end,
    Active=function() return env.Players[0]:IsTurnActive() end,
    CityCount=function() return env.Players[0]:GetCities():GetCount() end,
  }
  local function OnActivate(pid)
    if h.enabled~=true or pid~=0 then return end
    local knownTurn,knownClock
    local ok=pcall(function()
      local player=ports.LocalPlayer()
      assert(type(player)=='number' and player==0)
      local turn=ports.Turn()
      assert(Finite(turn) and turn==math.floor(turn))
      knownTurn=turn
      if turn<85 or turn>91 then return end
      local now=ports.Now();assert(Finite(now))
      knownClock=now
      if h.anchors[turn]==nil then
        h.anchors[turn]=now;h.anchorCount=h.anchorCount+1
      end
    end)
    if not ok then Unknown('anchor_event',knownTurn,knownClock) end
  end
  function h.WrapActivation(fn)
    assert(type(fn)=='function','Invalid native activation callback')
    return function(...)
      local ok=pcall(OnActivate,...)
      if not ok then pcall(Unknown,'anchor_event') end
      return fn(...)
    end
  end
  local event,remove
  local addOk=pcall(function()
    event=env.Events.PlayerTurnActivated
    assert(type(event.Add)=='function' and type(event.Remove)=='function')
    remove=event.Remove
    event.Add(OnActivate)
  end)
  if addOk then h.subscribed=true else h.subscribed=nil;Unknown('subscribe') end
  local bindings={}
  function h.Bind(admin,controller)
    if h.bound or h.retired or not addOk then return false end
    local ok=pcall(function()
      assert(type(admin)=='table' and type(controller)=='table')
      assert(type(admin.Run)=='function' and type(controller.RunNow)=='function')
      bindings={
        {owner=admin,key='Run',original=admin.Run,label='Admin.Run'},
        {owner=controller,key='RunNow',original=controller.RunNow,label='Controller.RunNow'},
      }
      for _,b in ipairs(bindings) do b.wrapped=WrapWindow(h,b.label,b.original,ports) end
    end)
    if not ok then Unknown('bind');return false end
    for _,b in ipairs(bindings) do b.owner[b.key]=b.wrapped end
    h.bound=true
    return true
  end
  function h.SetEnabled(value)
    if type(value)~='boolean' or h.retired or not h.bound or not h.subscribed
      or (value and h.qualificationErrors~=0) then return false end
    h.enabled=value
    return true
  end
  local removeAttempted,removed=false,false
  function h.Restore()
    h.enabled=false;h.retired=true
    local same={}
    for i,b in ipairs(bindings) do
      same[i]=b.owner[b.key]==b.wrapped
      if same[i] then b.owner[b.key]=b.original end
    end
    if not removeAttempted and type(remove)=='function' then
      removeAttempted=true
      local ok=pcall(remove,OnActivate)
      if ok then h.subscribed=false;removed=true else Unknown('unsubscribe') end
    end
    return removed,same
  end
  return h
end

return NewPlanA
