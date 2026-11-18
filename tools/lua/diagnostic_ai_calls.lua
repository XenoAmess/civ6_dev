-- Passive diagnostic only. Does not submit orders or alter AI admission.
-- pcall preserves error objects/arity; Lua 5.1 yielding through it is unsupported.
return function(E, capacity)
  assert(type(E)=='table' and type(E.Controller)=='table' and type(E.Admin)=='table')
  assert(type(E.Now)=='function' and type(E.Turn)=='function')
  assert(type(capacity)=='number' and capacity%1==0 and capacity>=1 and capacity<=4096)
  local unpack=unpack or table.unpack
  local function pack(...) return {n=select('#',...),...} end
  local function finite(v) return type(v)=='number' and v==v and v>=0 and v<math.huge end
  local targets={{object=E.Controller,key='RunNow',label='Controller'},
                 {object=E.Admin,key='Run',label='Admin'}}
  for _,t in ipairs(targets) do t.original=assert(t.object[t.key]);assert(type(t.original)=='function') end
  local rows,total,dropped,invalid,depth,active={},0,0,false,0,0
  local retired,reading=false,false
  local function clock()
    if reading then invalid=true;return nil end
    reading=true
    local a=pack(pcall(E.Now));local b=pack(pcall(E.Turn))
    reading=false
    if a.n~=2 or a[1]~=true or not finite(a[2]) or b.n~=2 or b[1]~=true
       or not finite(b[2]) or b[2]%1~=0 then invalid=true;return nil end
    return a[2],b[2]
  end
  local function check()
    if not retired then
      for _,t in ipairs(targets) do if t.object[t.key]~=t.wrapper then invalid=true end end
    end
  end
  for _,t in ipairs(targets) do
    t.wrapper=function(...)
      -- A retained wrapper reference still delegates after retirement.
      if retired then return t.original(...) end
      total=total+1;depth=depth+1;active=active+1
      local row
      if #rows<capacity then
        row={sequence=total,label=t.label,depth=depth,completed=false}
        rows[#rows+1]=row
      else dropped=dropped+1 end
      local a,turn
      if row then a,turn=clock();row.started=a;row.turn=turn end
      local result=pack(pcall(t.original,...))
      if row then
        local z,last=clock();row.finished=z;row.last_turn=last
        row.completed=true;row.original_ok=result[1];row.return_count=result.n-1
        if a==nil or z==nil or z<a or turn~=last then invalid=true;row.clock_valid=false
        else row.clock_valid=true end
      end
      active=active-1;depth=depth-1
      check()
      if not result[1] then error(result[2],0) end
      return unpack(result,2,result.n)
    end
  end
  -- Preflight completed for both originals before either assignment.
  for _,t in ipairs(targets) do t.object[t.key]=t.wrapper end
  local api={}
  function api.Snapshot()
    check()
    local out={capacity=capacity,total_calls=total,dropped=dropped,invalid=invalid,
               active=active,retired=retired,rows={}}
    for i,row in ipairs(rows) do
      local copy={};for k,v in pairs(row) do copy[k]=v end;out.rows[i]=copy
    end
    return out
  end
  function api.Retire()
    check();retired=true
    local restored=0
    for _,t in ipairs(targets) do
      if t.object[t.key]==t.wrapper then t.object[t.key]=t.original;restored=restored+1
      else invalid=true end
    end
    return restored==2
  end
  return api
end
