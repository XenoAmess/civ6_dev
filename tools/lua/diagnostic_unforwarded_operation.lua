-- Private QA fault: an attempted SDK call is deliberately NOT sent to Native.
-- Keep that fact separate from engine rejection, acceptance or completion.
return function(U,I,owner,id,unitType,operation,capacity)
  local function Integer(n,max)return type(n)=='number'and n==n and n>=0 and n<=max and n%1==0 end
  assert(type(U)=='table'and type(U.RequestOperation)=='function'and type(I)=='table')
  assert(Integer(owner,2147483647)and Integer(id,2147483647)and Integer(capacity,64)and capacity>=1)
  assert(unitType=='UNIT_MISSIONARY'and type(operation)=='number'and operation==operation and operation%1==0)
  local original=U.RequestOperation
  local armed,enabled,retired=false,false,false
  local calls,intercepted,targetForwarded,identityErrors,dropped=0,0,0,0,0
  local rows={};local api={};local wrapper
  local function Inc(n)return math.min(n+1,2147483647)end
  local function Target(u,code)
    if code~=operation then return false end
    local ok,who,which,kind=pcall(function()
      local row=I.Units[u:GetUnitType()]
      return u:GetOwner(),u:GetID(),row and row.UnitType
    end)
    if not ok then identityErrors=Inc(identityErrors);return false end
    if who~=owner or which~=id then return false end
    if kind~=unitType then identityErrors=Inc(identityErrors);return false end
    return true
  end
  wrapper=function(u,code,...)
    calls=Inc(calls)
    if Target(u,code)then
      if enabled and not retired then
        intercepted=Inc(intercepted)
        if #rows<capacity then
          rows[#rows+1]={owner=owner,id=id,unitType=unitType,operation=code,
            argumentCount=select('#',...),NativeForwarded=false}
        else dropped=Inc(dropped)end
        -- Never turn an overflow or a second attempted replay into a live order.
        return
      end
      targetForwarded=Inc(targetForwarded)
    end
    return original(u,code,...)
  end
  function api.Arm(expectedOwner,expectedID,expectedType,expectedOperation)
    if expectedOwner~=owner or expectedID~=id or expectedType~=unitType or expectedOperation~=operation then return false,'target_mismatch' end
    if U.RequestOperation~=wrapper then return false,'foreign_binding' end
    if retired then return false,'retired' end
    if armed then return false,'already_armed' end
    armed=true;enabled=true;return true,'armed'
  end
  function api.Read()
    local out={owner=owner,id=id,unitType=unitType,operation=operation,capacity=capacity,
      calls=calls,intercepted=intercepted,targetNativeForwarded=targetForwarded,
      identityErrors=identityErrors,dropped=dropped,armed=armed,enabled=enabled,
      retired=retired,binding=U.RequestOperation==wrapper,originalBinding=U.RequestOperation==original,rows={}}
    for i,r in ipairs(rows)do local c={};for k,v in pairs(r)do c[k]=v end;out.rows[i]=c end
    return out
  end
  function api.Retire()
    if U.RequestOperation==original and retired then return true,'already_retired' end
    if U.RequestOperation~=wrapper then return false,'foreign_binding_preserved' end
    enabled=false;retired=true;U.RequestOperation=original;return true,'restored'
  end
  U.RequestOperation=wrapper
  return api
end
