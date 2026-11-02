-- External diagnostic helper, not included by the playable mod.
-- Durations are inclusive. Do not sum nested samples as total mod CPU time.
local function Pack(...)
  return {n=select("#",...),...}
end

local function Finite(value)
  return type(value)=="number" and value==value and value>-math.huge and value<math.huge
end

local function NewProfile(clock,capacity)
  assert(Finite(capacity) and capacity>=1 and capacity==math.floor(capacity),"Invalid sample capacity")
  local state={samples={},totalCalls=0,dropped=0,invalidClock=0,capacity=capacity}
  local function ReadClock()
    if type(clock)~="function" then return nil end
    local ok,value=pcall(clock)
    if ok and Finite(value) then return value end
  end
  function state:Wrap(name,fn)
    assert(type(name)=="string" and type(fn)=="function","Invalid profile target")
    return function(...)
      state.totalCalls=state.totalCalls+1
      local started=ReadClock()
      local result=Pack(pcall(fn,...))
      local ended=ReadClock()
      local seconds=started and ended and ended-started
      if Finite(seconds) and seconds>=0 then
        if #state.samples<capacity then
          state.samples[#state.samples+1]={name=name,seconds=seconds,failed=not result[1]}
        else
          state.dropped=state.dropped+1
        end
      else
        state.invalidClock=state.invalidClock+1
      end
      if not result[1] then error(result[2],0) end
      return unpack(result,2,result.n)
    end
  end
  return state
end

return NewProfile
