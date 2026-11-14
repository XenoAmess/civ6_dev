local function Pack(...)return{n=select('#',...),...}end
local function Integer(v)return type(v)=='number'and v==v and v>=0 and v<=2147483647 and v==math.floor(v)end
local function NewNamedNested(NewProfile,WrapChild,Now,Qualify,rootLabel)
  assert(type(rootLabel)=='string'and(rootLabel=='Admin.Run'or rootLabel=='Controller.RunNow'),'Invalid root label')
  assert(type(NewProfile)=='function'and type(WrapChild)=='function'and type(Now)=='function'and type(Qualify)=='function','Missing diagnostic port')
  local h={enabled=false,retired=false,errors=0,serial=0,profile=NewProfile(Now,4096)}
  h.profile.metadataErrors=0
  local function Unknown()h.errors=math.min(2147483647,h.errors+1)end
  function h.SetEnabled(value)
    if type(value)~='boolean'or h.retired or(value and h.errors~=0)then return false end
    h.enabled=value;return true
  end
  function h.WrapRoot(fn)
    assert(type(fn)=='function','Invalid diagnostic root')
    local timed=h.profile:Wrap(rootLabel,fn)
    return function(...)
      if not h.enabled or h.currentEntry~=nil then return fn(...)end
      local ok,snapshot=pcall(function()
        local q=Qualify()
        if q==nil then return nil end
        assert(type(q)=='table')
        local t,c=q.turnBefore,q.citiesBefore
        assert(Integer(t)and Integer(c))
        return{turnBefore=t,citiesBefore=c}
      end)
      if not ok then Unknown();return fn(...)end
      if snapshot==nil then return fn(...)end
      if not Integer(h.serial)or h.serial>=2147483647 then Unknown();return fn(...)end
      h.serial=h.serial+1;snapshot.id=h.serial;h.currentEntry=snapshot
      local p=h.profile
      local count,dropped,invalid=#p.samples,p.dropped,p.invalidClock
      local result=Pack(pcall(timed,...))
      h.currentEntry=nil
      local annotated=pcall(function()
        assert(#p.samples>count and p.dropped==dropped and p.invalidClock==invalid)
        local row=p.samples[#p.samples]
        assert(type(row)=='table'and row.name==rootLabel)
        row.rootId=snapshot.id;row.rootTurn=snapshot.turnBefore;row.rootCities=snapshot.citiesBefore
      end)
      if not annotated then Unknown()end
      if not result[1]then error(result[2],0)end
      return unpack(result,2,result.n)
    end
  end
  function h.WrapChild(label,fn)
    assert(type(label)=='string'and label~=rootLabel and type(fn)=='function','Invalid child target')
    return WrapChild(h.profile,label,fn,function()return h.currentEntry end)
  end
  return h
end
return NewNamedNested