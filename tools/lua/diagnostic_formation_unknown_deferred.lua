-- Private deferred fault: the real snapshot/getters still execute once per call.
return function(original, owner, id, unitType, limit)
  local function Integer(v, maximum)
    return type(v)=="number" and v==v and v>=0 and v<=maximum and v%1==0
  end
  assert(type(original)=="function" and Integer(owner,2147483647)
    and Integer(id,2147483647) and Integer(limit,64) and limit>=1)
  assert(unitType=="UNIT_BUILDER" or unitType=="UNIT_SETTLER" or unitType=="UNIT_MISSIONARY")
  local enabled,armed,retired,expired=false,false,false,false
  local calls,matching,masked=0,0,0
  local rows={}
  local api={}
  function api.Arm(expectedOwner,expectedID,expectedType)
    if expectedOwner~=owner or expectedID~=id or expectedType~=unitType then return false,"target_mismatch" end
    if retired then return false,"retired" end
    if expired then return false,"expired" end
    if armed then return false,"already_armed" end
    armed=true;enabled=true
    return true,"armed"
  end
  function api.Invoke(unit,state)
    calls=math.min(calls+1,2147483647)
    local snapshot=original(unit,state)
    if type(snapshot)~="table" or snapshot.owner~=owner or snapshot.id~=id
      or snapshot.type~=unitType then return snapshot end
    matching=math.min(matching+1,2147483647)
    if not enabled or retired or masked>=limit or snapshot.formationCount~=1 then return snapshot end
    local changed={};for k,v in pairs(snapshot)do changed[k]=v end
    changed.formationCount=nil
    masked=masked+1;rows[#rows+1]={owner=snapshot.owner,id=snapshot.id,type=snapshot.type,originalFormation=1}
    if masked==limit then enabled=false;expired=true end
    return changed
  end
  function api.Disable()
    enabled=false;retired=true
  end
  function api.Snapshot()
    local out={owner=owner,id=id,unitType=unitType,limit=limit,capacity=64,
      calls=calls,matching=matching,masked=masked,enabled=enabled,armed=armed,
      deferred=true,retired=retired,expired=expired,rows={}}
    for i,r in ipairs(rows)do
      out.rows[i]={owner=r.owner,id=r.id,type=r.type,originalFormation=r.originalFormation}
    end
    return out
  end
  return api
end
