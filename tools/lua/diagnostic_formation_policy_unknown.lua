-- Private QA: copy a positive-move policy input with missing formationCount.
-- Actual Controller snapshot/getters have already run. Never modifies the input.
return function(P,owner,id,unitType,limit)
  local function Integer(n,max)return type(n)=='number'and n==n and n>=0 and n<=max and n%1==0 end
  local function Positive(n)return type(n)=='number'and n==n and n>0 and n<math.huge end
  local function Pack(...)return{n=select('#',...),...}end
  local Unpack=table.unpack or unpack
  assert(type(P)=='table'and type(P.CanCivilian)=='function'and type(P.Context)=='function')
  assert(Integer(owner,2147483647)and Integer(id,2147483647)and Integer(limit,64)and limit>=1)
  assert(unitType=='UNIT_BUILDER'or unitType=='UNIT_SETTLER'or unitType=='UNIT_MISSIONARY')
  local original,context=P.CanCivilian,P.Context
  local armed,enabled,retired,expired=false,false,false,false
  local calls,matching,masked=0,0,0
  local rows={};local api={};local wrapper
  local function Inc(n)return math.min(n+1,2147483647)end
  wrapper=function(ctx,snapshot,...)
    calls=Inc(calls)
    local target=type(snapshot)=='table'and getmetatable(snapshot)==nil
      and snapshot.owner==owner and snapshot.id==id and snapshot.type==unitType
    if target then matching=Inc(matching)end
    if target and enabled and not retired and masked<limit and P.Context==context
      and context(ctx)==true and snapshot.formationCount==1 and Positive(snapshot.moves)then
      local changed={};for k,v in pairs(snapshot)do changed[k]=v end
      changed.formationCount=nil;masked=masked+1
      local row={owner=snapshot.owner,id=snapshot.id,type=snapshot.type,
        formation=snapshot.formationCount,moves=snapshot.moves,plot=snapshot.plot}
      rows[#rows+1]=row
      if masked==limit then enabled=false;expired=true end
      local result=Pack(original(ctx,changed,...))
      row.returnCount=result.n;row.allowed=result[1];row.reason=result[2]
      return Unpack(result,1,result.n)
    end
    return original(ctx,snapshot,...)
  end
  function api.Arm(expectedOwner,expectedID,expectedType)
    if expectedOwner~=owner or expectedID~=id or expectedType~=unitType then return false,'target_mismatch' end
    if P.CanCivilian~=wrapper or P.Context~=context then return false,'foreign_binding' end
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
    local out={owner=owner,id=id,unitType=unitType,limit=limit,capacity=64,calls=calls,matching=matching,
      masked=masked,enabled=enabled,armed=armed,retired=retired,expired=expired,
      binding=P.CanCivilian==wrapper,originalBinding=P.CanCivilian==original,
      contextBinding=P.Context==context,positiveOnly=true,field='formationCount',rows={}}
    for i,r in ipairs(rows)do local c={};for k,v in pairs(r)do c[k]=v end;out.rows[i]=c end
    return out
  end
  P.CanCivilian=wrapper
  return api
end
