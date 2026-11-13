-- Private Stage A helper. The playable mod never includes this file.
local function Pack(...)
  return {n=select('#',...),...}
end

local function Finite(v)
  return type(v)=='number' and v==v and v>-math.huge and v<math.huge
end

local function Integer(v)
  return Finite(v) and v>=0 and v==math.floor(v)
end

local function WrapWindow(h,label,fn,env)
  assert(type(h)=='table' and type(h.profile)=='table' and type(h.anchors)=='table')
  assert(type(fn)=='function' and type(label)=='string' and type(env)=='table')
  local profile=h.profile
  local timed=profile:Wrap(label,fn)
  local function Unknown(reason,turn,now)
    if type(h.RecordUnknown)=='function' then h.RecordUnknown(reason,label,turn,now)
    else h.qualificationErrors=h.qualificationErrors+1 end
  end
  local function Read(name,valid)
    local getter=env[name]
    if type(getter)~='function' then return nil end
    local ok,value=pcall(getter)
    if ok and valid(value) then return value end
  end
  local function Boolean(v) return type(v)=='boolean' end
  return function(...)
    if h.enabled~=true then return fn(...) end
    local argumentCount=select('#',...)
    local first=select(1,...)
    local allowance='other'
    if first==nil then allowance='nil'
    elseif type(first)=='boolean'then allowance=tostring(first)end
    local turn=Read('Turn',Integer)
    if turn==nil then Unknown('turn');return fn(...) end
    if turn<86 or turn>90 then return fn(...) end
    local pid=Read('LocalPlayer',Integer)
    if pid==nil then Unknown('player',turn);return fn(...) end
    if pid~=0 then return fn(...) end
    local active=Read('Active',Boolean)
    if active==nil then Unknown('active',turn);return fn(...) end
    if not active then return fn(...) end
    local anchor=h.anchors[turn]
    local now=Read('Now',Finite)
    local preAnchor=false
    if not Finite(anchor) then
      if h.deferPreAnchor==true and label=='Controller.RunNow'and argumentCount==1
        and first==false and now~=nil then preAnchor=true
      else Unknown('anchor_missing',turn,now);return fn(...)end
    end
    if now==nil then Unknown('clock',turn);return fn(...) end
    if not preAnchor and now<anchor then Unknown('before_anchor',turn,now);return fn(...) end
    if not preAnchor and now>=anchor+10 then return fn(...) end
    local cities=Read('CityCount',Integer)
    if cities==nil then Unknown('city_before',turn,now);return fn(...) end
    local count=#profile.samples
    local dropped,invalid=profile.dropped,profile.invalidClock
    local result=Pack(pcall(timed,...))
    -- Read diagnostics under pcall even when the gameplay function threw.
    local afterTurn=Read('Turn',Integer)
    local afterCities=Read('CityCount',Integer)
    local row=profile.samples[#profile.samples]
    if afterTurn==nil then Unknown('turn_after',turn,now)
    elseif afterCities==nil then Unknown('city_after',turn,now) end
    if profile.dropped~=dropped or profile.invalidClock~=invalid or #profile.samples<=count
      or type(row)~='table' or row.name~=label then
      Unknown('sample_missing',turn,now)
    else
      row.turnStart=turn;row.turnEnd=afterTurn
      row.cityStart=cities;row.cityEnd=afterCities
      row.anchor=anchor
      row.windowEligible=not preAnchor and Finite(row.started) and row.started>=anchor and row.started<anchor+10
      if h.deferPreAnchor==true then
        row.preAnchor=preAnchor;row.argumentCount=argumentCount;row.allowOrders=allowance
        if preAnchor then h.preAnchor:Record(row,turn)end
      end
    end
    if not result[1] then error(result[2],0) end
    return unpack(result,2,result.n)
  end
end

return WrapWindow
