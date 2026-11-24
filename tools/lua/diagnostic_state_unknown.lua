-- Private F07 diagnostic. Real reads run first; no SDK getter is replaced.
return function(snapshot,qualifier,owner,id,kind,operation,limit)
  local function integer(v,max)return type(v)=='number'and v==v and v>=0 and v<=max and v%1==0 end
  assert(type(snapshot)=='function'and type(qualifier)=='function')
  assert(integer(owner,2147483647)and integer(id,2147483647))
  assert(kind=='UNIT_MISSIONARY'and operation==1592408602 and integer(limit,64)and limit>=1)
  local unpack_=unpack or table.unpack
  local function pack(...)return{n=select('#',...),...}end
  local modes={owner=true,formation=true,legality=true}
  local state={owner=owner,id=id,unitType=kind,operation=operation,limit=limit,capacity=limit*3,
    enabled=false,armed=false,retired=false,expired=false,snapshotCalls=0,qualifierCalls=0,
    identityErrors=0,dropped=0,used={},masked={owner=0,formation=0,legality=0},rows={}}
  local api={}
  local function increment(v)return math.min(v+1,2147483647)end
  local function target(s)
    return type(s)=='table'and s.owner==owner and s.id==id and s.type==kind
      and s.formationCount==1 and type(s.moves)=='number'and s.moves==s.moves and s.moves>0 and s.moves<math.huge
  end
  local function record(s,mode,native)
    state.masked[mode]=state.masked[mode]+1
    local row={mode=mode,owner=s.owner,id=s.id,type=s.type,formation=s.formationCount,moves=s.moves,masked_to_nil=true}
    if mode=='legality'then row.actual_native_qualifier=native end
    if #state.rows<state.capacity then state.rows[#state.rows+1]=row else state.dropped=increment(state.dropped)end
    if state.masked[mode]==limit then state.enabled=false;state.expired=true end
  end
  function api.Snapshot(unit,context)
    state.snapshotCalls=increment(state.snapshotCalls)
    local s=snapshot(unit,context)
    local mode=state.mode
    if state.enabled and not state.retired and(mode=='owner'or mode=='formation')and target(s)then
      local changed={};for k,v in pairs(s)do changed[k]=v end
      if mode=='owner'then changed.owner=nil else changed.formationCount=nil end
      record(s,mode)
      return changed
    end
    return s
  end
  function api.Qualify(unit,code,...)
    state.qualifierCalls=increment(state.qualifierCalls)
    local results=pack(qualifier(unit,code,...))
    if state.enabled and not state.retired and state.mode=='legality'and code==operation and results[1]==true then
      local ok,s=pcall(snapshot,unit,{})
      if not ok then state.identityErrors=increment(state.identityErrors)
      elseif target(s)then record(s,'legality',true);return nil end
    end
    return unpack_(results,1,results.n)
  end
  function api.Arm(who,which,unitType,mode)
    if who~=owner or which~=id or unitType~=kind or not modes[mode]then return false,'target_or_mode' end
    if state.retired then return false,'retired' end
    if state.used[mode]then return false,'already_used' end
    state.used[mode]=true;state.mode=mode;state.armed=true;state.enabled=true;state.expired=false
    return true,'armed'
  end
  function api.Disable()state.enabled=false;state.retired=true;state.mode=nil end
  local function clone(v)
    if type(v)~='table'then return v end
    local out={};for k,x in pairs(v)do out[k]=clone(x)end;return out
  end
  function api.Read()return clone(state)end
  return api
end
