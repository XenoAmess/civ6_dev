-- Private QA: mask the owner in the copied snapshot passed to the real policy.
-- The Controller's original snapshot and engine getters have already executed.
return function(P,owner,id,unitType,limit)
  local function Integer(n,max)return type(n)=='number'and n==n and n>=0 and n<=max and n%1==0 end
  assert(type(P)=='table'and type(P.CanCivilian)=='function')
  assert(Integer(owner,2147483647)and Integer(id,2147483647)and Integer(limit,64)and limit>=1)
  assert(unitType=='UNIT_BUILDER'or unitType=='UNIT_SETTLER'or unitType=='UNIT_MISSIONARY')
  local original=P.CanCivilian
  local armed,enabled,retired,expired=false,false,false,false
  local calls,matching,masked=0,0,0
  local rows={};local api={};local wrapper
  local function Inc(n)return math.min(n+1,2147483647)end
  wrapper=function(ctx,snapshot,...)
    calls=Inc(calls)
    local target=type(snapshot)=='table'and snapshot.owner==owner and snapshot.id==id and snapshot.type==unitType
    if target then matching=Inc(matching)end
    if target and enabled and not retired and masked<limit then
      local changed={};for k,v in pairs(snapshot)do changed[k]=v end
      changed.owner=nil;masked=masked+1
      rows[#rows+1]={owner=snapshot.owner,id=snapshot.id,type=snapshot.type,
        formation=snapshot.formationCount,moves=snapshot.moves,plot=snapshot.plot}
      if masked==limit then enabled=false;expired=true end
      return original(ctx,changed,...)
    end
    return original(ctx,snapshot,...)
  end
  function api.Arm(expectedOwner,expectedID,expectedType)
    if expectedOwner~=owner or expectedID~=id or expectedType~=unitType then return false,'target_mismatch' end
    if P.CanCivilian~=wrapper then return false,'foreign_binding' end
    if retired then return false,'retired' end
    if expired then return false,'expired' end
    if armed then return false,'already_armed' end
    armed=true;enabled=true;return true,'armed'
  end
  function api.Retire()
    if P.CanCivilian==original and retired then return true,'already_retired' end
    if P.CanCivilian~=wrapper then return false,'foreign_binding_preserved' end
    enabled=false;retired=true;P.CanCivilian=original;return true,'restored'
  end
  function api.Snapshot()
    local out={owner=owner,id=id,unitType=unitType,limit=limit,calls=calls,matching=matching,
      masked=masked,enabled=enabled,armed=armed,retired=retired,expired=expired,
      binding=P.CanCivilian==wrapper,originalBinding=P.CanCivilian==original,rows={}}
    for i,r in ipairs(rows)do local c={};for k,v in pairs(r)do c[k]=v end;out.rows[i]=c end
    return out
  end
  P.CanCivilian=wrapper
  return api
end
