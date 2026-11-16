-- Private QA: run the real Native qualifier once, then mask a targeted true.
-- No unit operation, journal, movement, readiness or game property is written.
return function(U,I,owner,id,unitType,action,limit)
  local function Integer(n,max)return type(n)=='number'and n==n and n>=0 and n<=max and n%1==0 end
  assert(type(U)=='table'and type(U.CanStartOperation)=='function'and type(I)=='table')
  assert(Integer(owner,2147483647)and Integer(id,2147483647)and Integer(limit,64)and limit>=1)
  assert(unitType=='UNIT_MISSIONARY'and type(action)=='number'and action==action and action%1==0)
  local original=U.CanStartOperation
  local unpackValues=unpack or table.unpack
  local function Pack(...)return {n=select('#',...),...}end
  local armed,enabled,retired,expired=false,false,false,false
  local calls,matching,masked,identityErrors,probes=0,0,0,0,0
  local rows={};local api={};local wrapper
  local function Inc(n)return math.min(n+1,2147483647)end
  local function Target(u,code)
    if code~=action then return false end
    local ok,who,which,kind=pcall(function()
      local row=I.Units[u:GetUnitType()]
      return u:GetOwner(),u:GetID(),row and row.UnitType
    end)
    if not ok then identityErrors=Inc(identityErrors);return false end
    return who==owner and which==id and kind==unitType
  end
  wrapper=function(u,code,...)
    calls=Inc(calls)
    local result=Pack(original(u,code,...))
    if Target(u,code)then
      matching=Inc(matching)
      if enabled and not retired and masked<limit and result[1]==true then
        masked=masked+1;rows[#rows+1]={owner=owner,id=id,type=unitType,action=code,
          originalAllowed=true,argumentCount=select('#',...),resultCount=result.n}
        result[1]=nil
        if masked==limit then enabled=false;expired=true end
      end
    end
    return unpackValues(result,1,result.n)
  end
  function api.Arm(expectedOwner,expectedID,expectedType)
    if expectedOwner~=owner or expectedID~=id or expectedType~=unitType then return false,'target_mismatch' end
    if U.CanStartOperation~=wrapper then return false,'foreign_binding' end
    if retired then return false,'retired' end
    if expired then return false,'expired' end
    if armed then return false,'already_armed' end
    armed=true;enabled=true;return true,'armed'
  end
  function api.ReadOriginal(u,code,...)
    assert(U.CanStartOperation==wrapper and not retired,'Diagnostic no longer owns qualifier')
    assert(Target(u,code),'Only the exact target and operation can be probed')
    probes=Inc(probes)
    return original(u,code,...)
  end
  function api.Retire()
    if U.CanStartOperation==original and retired then return true,'already_retired' end
    if U.CanStartOperation~=wrapper then return false,'foreign_binding_preserved' end
    enabled=false;retired=true;U.CanStartOperation=original;return true,'restored'
  end
  function api.Snapshot()
    local out={owner=owner,id=id,unitType=unitType,action=action,limit=limit,calls=calls,matching=matching,
      masked=masked,enabled=enabled,armed=armed,retired=retired,expired=expired,identityErrors=identityErrors,
      probes=probes,binding=U.CanStartOperation==wrapper,originalBinding=U.CanStartOperation==original,rows={}}
    for i,r in ipairs(rows)do local c={};for k,v in pairs(r)do c[k]=v end;out.rows[i]=c end
    return out
  end
  U.CanStartOperation=wrapper
  return api
end
