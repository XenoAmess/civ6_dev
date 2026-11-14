-- Private TEST_PLAYER stopwatch bridge. Never submits a game action.
local function NewEndBridge(env)
  local key='P6BaiqiPairEndBridge'
  local marker='baiqi-paired-end-bridge-v1'
  local pressureMarker='baiqi-paired-end-bridge-pressure-v1'
  local h={active=false,errors=0,refused=0,entry=nil}
  local exposed,clock,entry
  local sourceVersion=140
  local pressureInitialTurn=nil
  local attempts={}
  local function Error() h.errors=math.min(2147483647,h.errors+1) end
  local function Refused() h.refused=math.min(2147483647,h.refused+1);return false end
  local function Integer(v)
    return type(v)=='number' and v>=0 and v<=2147483647 and v==math.floor(v)
  end
  local function Finite(v)
    return type(v)=='number' and v==v and v>=0 and v<math.huge
  end
  local function SnapshotValid(s,count,pending)
    return type(s)=='table' and s.marker=='baiqi67-paired-clock-v1'
      and s.subscribed==true and s.retired==false and s.errors==0 and s.refused==0
      and type(s.records)=='table' and #s.records==count
      and (pending or s.pending==nil)
  end
  local function Begin(turn,token)
    if not Integer(turn) or type(token)~='string'
      or #token~=32 or not string.match(token,'^[0-9a-f]+$') then return Refused() end
    if pressureInitialTurn~=nil then
      if turn<pressureInitialTurn or turn>pressureInitialTurn+4 then return Refused() end
    else
      if turn<85 or turn>89 then return Refused() end
    end
    local ok,result=pcall(function()
      if not h.active or h.errors~=0 or h.refused~=0 or exposed[key]~=entry
        or attempts[turn]~=nil then return false end
      local stage=env.GetStage()
      if type(stage)~='table' or stage.phase~='RECORDING' or stage.token~=token
        or stage.normal_end~=true or stage.source_version~=sourceVersion or entry.source_version~=sourceVersion or type(stage.ends)~='table'
        or stage.ends[turn]~=true then return false end
      if pressureInitialTurn~=nil then
        if stage.source~='baiqi142-pressure-paired-v1' or stage.initial_turn~=pressureInitialTurn
          or entry.marker~=pressureMarker or entry.source~='baiqi142-pressure-paired-v1'
          or entry.initial_turn~=pressureInitialTurn then return false end
      end
      if env.GetTurn()~=turn or env.GetLocal()~=0 or env.GetClock()~=clock then return false end
      local expectedCount
      if pressureInitialTurn~=nil then expectedCount=turn-pressureInitialTurn else expectedCount=turn-85 end
      if not SnapshotValid(clock:Snapshot(),expectedCount,false) then return false end
      -- Reservation precedes the potentially uncertain clock operation. The
      -- READY ledger and game-action issuance are owned by the external driver.
      attempts[turn]=token
      if clock:Begin(turn)~=true then Error();return false end
      local after=clock:Snapshot()
      if not SnapshotValid(after,expectedCount,true) then Error();return false end
      local p=after.pending
      if type(p)~='table' or p.from_turn~=turn or p.to_turn~=turn+1 or p.pid~=0
        or not Finite(p.started) or env.GetTurn()~=turn or env.GetLocal()~=0 then
        Error();return false
      end
      return true
    end)
    if not ok then Error();return false end
    if result~=true then return Refused() end
    return true
  end
  local retired,result=false,false
  function h.Retire()
    if retired then return result end
    retired=true;h.active=false
    local ok=pcall(function()
      if exposed and entry and exposed[key]==entry then exposed[key]=nil end
    end)
    if not ok then Error() end
    result=ok
    return result
  end
  local ok=pcall(function()
    assert(type(env)=='table' and type(env.ExposedMembers)=='table')
    for _,name in ipairs({'GetStage','GetClock','GetTurn','GetLocal'}) do
      assert(type(env[name])=='function')
    end
    if env.source_version~=nil then sourceVersion=env.source_version end
    assert(type(sourceVersion)=='number'and(sourceVersion==140 or sourceVersion==141 or sourceVersion==142),'Unknown source version')
    if env.initial_turn~=nil then
      if not Integer(env.initial_turn) or env.initial_turn<0 or env.initial_turn>2147483641 then Error();return end
      if sourceVersion~=142 then Error();return end
      pressureInitialTurn=env.initial_turn
    end
    exposed=env.ExposedMembers
    assert(exposed[key]==nil,'Foreign paired end bridge')
    clock=env.GetClock()
    assert(type(clock)=='table' and clock.marker=='baiqi67-paired-clock-v1'
      and type(clock.Begin)=='function' and type(clock.Snapshot)=='function')
    if pressureInitialTurn~=nil then
      entry={marker=pressureMarker,source='baiqi142-pressure-paired-v1',initial_turn=pressureInitialTurn,source_version=sourceVersion,Begin=Begin}
    else
      entry={marker=marker,source_version=sourceVersion,Begin=Begin}
    end
    exposed[key]=entry
    assert(exposed[key]==entry)
    h.entry=entry;h.active=true
  end)
  if not ok then Error();h.active=false end
  return h
end

return NewEndBridge
