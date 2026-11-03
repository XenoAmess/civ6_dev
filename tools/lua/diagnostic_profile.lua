-- External diagnostic helper, not included by the playable mod.
-- Durations are inclusive. Do not sum nested samples as total mod CPU time.
local function Pack(...)
  return {n=select("#",...),...}
end

local function Finite(value)
  return type(value)=="number" and value==value and value>-math.huge and value<math.huge
end

local function NewProfile(clock,capacity,options)
  assert(Finite(capacity) and capacity>=1 and capacity==math.floor(capacity),"Invalid sample capacity")
  local aggregateZero=false
  if options~=nil then
    assert(type(options)=="table","Invalid options")
    if options.aggregate_zero~=nil then
      assert(type(options.aggregate_zero)=="boolean","Invalid aggregate_zero flag")
      aggregateZero=options.aggregate_zero
    end
  end
  local state={samples={},totalCalls=0,dropped=0,invalidClock=0,capacity=capacity,aggregateZero=aggregateZero,zeroSuccess=0}
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
        if aggregateZero and seconds==0 and result[1] then
          state.zeroSuccess=state.zeroSuccess+1
        else
          if #state.samples<capacity then
            state.samples[#state.samples+1]={name=name,seconds=seconds,failed=not result[1],started=started,ended=ended}
          else
            state.dropped=state.dropped+1
          end
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
