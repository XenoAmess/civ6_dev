-- Private diagnostic of one already-read snapshot; no engine calls or commands.
return function(original, owner, id, unitType, limit)
  local function Integer(v, maximum)
    return type(v)=="number" and v==v and v>=0 and v<=maximum and v%1==0
  end
  assert(type(original)=="function" and Integer(owner,2147483647)
    and Integer(id,2147483647) and Integer(limit,64) and limit>=1)
  assert(unitType=="UNIT_BUILDER" or unitType=="UNIT_SETTLER" or unitType=="UNIT_MISSIONARY")
  local enabled, retired, expired=true,false,false
  local calls, matching, masked=0,0,0
  local rows={}
  local api={}
  function api.Invoke(unit,state)
    calls=math.min(calls+1,2147483647)
    local snapshot=original(unit,state)
    if type(snapshot)~="table" or snapshot.owner~=owner or snapshot.id~=id
      or snapshot.type~=unitType then return snapshot end
    matching=math.min(matching+1,2147483647)
    if not enabled or retired or masked>=limit or snapshot.formationCount~=1 then return snapshot end
    local row={owner=snapshot.owner,id=snapshot.id,type=snapshot.type,originalFormation=1}
    -- The source owns the snapshot table; copy before altering the diagnostic view.
    local changed={};for k,v in pairs(snapshot)do changed[k]=v end
    changed.formationCount=nil
    masked=masked+1;rows[#rows+1]=row
    if masked==limit then enabled=false;expired=true end
    return changed
  end
  function api.Disable()
    enabled=false;retired=true
  end
  function api.Snapshot()
    local out={owner=owner,id=id,unitType=unitType,limit=limit,capacity=64,
      calls=calls,matching=matching,masked=masked,enabled=enabled,
      retired=retired,expired=expired,rows={}}
    for i,r in ipairs(rows)do
      out.rows[i]={owner=r.owner,id=r.id,type=r.type,originalFormation=r.originalFormation}
    end
    return out
  end
  return api
end
