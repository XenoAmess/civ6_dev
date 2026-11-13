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
  local function Unknown()
    h.qualificationErrors=h.qualificationErrors+1
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
    local turn=Read('Turn',Integer)
    if turn==nil then Unknown();return fn(...) end
    if turn<86 or turn>90 then return fn(...) end
    local pid=Read('LocalPlayer',Integer)
    if pid==nil then Unknown();return fn(...) end
    if pid~=0 then return fn(...) end
    local active=Read('Active',Boolean)
    if active==nil then Unknown();return fn(...) end
    if not active then return fn(...) end
    local anchor=h.anchors[turn]
    local now=Read('Now',Finite)
    if not Finite(anchor) or now==nil or now<anchor then Unknown();return fn(...) end
    if now>=anchor+10 then return fn(...) end
    local cities=Read('CityCount',Integer)
    if cities==nil then Unknown();return fn(...) end
    local count=#profile.samples
    local dropped,invalid=profile.dropped,profile.invalidClock
    local result=Pack(pcall(timed,...))
    -- Read diagnostics under pcall even when the gameplay function threw.
    local afterTurn=Read('Turn',Integer)
    local afterCities=Read('CityCount',Integer)
    local row=profile.samples[#profile.samples]
    if afterTurn==nil or afterCities==nil then Unknown() end
    if profile.dropped~=dropped or profile.invalidClock~=invalid or #profile.samples<=count
      or type(row)~='table' or row.name~=label then
      Unknown()
    else
      row.turnStart=turn;row.turnEnd=afterTurn
      row.cityStart=cities;row.cityEnd=afterCities
      row.anchor=anchor
      row.windowEligible=Finite(row.started) and row.started>=anchor and row.started<anchor+10
    end
    if not result[1] then error(result[2],0) end
    return unpack(result,2,result.n)
  end
end

return WrapWindow
