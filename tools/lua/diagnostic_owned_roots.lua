-- Inclusive owned entry envelopes; Native/vanilla child time is included.
-- This helper does not prove source coverage, CPU time or clock synchronization.
local function Pack(...)
  return {n=select('#',...),...}
end

local function NewOwnedRoots(NewProfile,clock,capacity)
  assert(type(NewProfile)=='function','Missing canonical profiler')
  local profile=NewProfile(clock,capacity)
  local enabled=false
  local active=false
  local handle={profile=profile}
  function handle:SetEnabled(value)
    assert(type(value)=='boolean','Invalid enabled flag')
    enabled=value
  end
  function handle:Wrap(label,fn)
    assert(type(label)=='string' and type(fn)=='function','Invalid owned target')
    local timed=profile:Wrap(label,fn)
    return function(...)
      if not enabled or active then return fn(...) end
      active=true
      local result=Pack(pcall(timed,...))
      active=false
      if not result[1] then error(result[2],0) end
      return unpack(result,2,result.n)
    end
  end
  return handle
end

return NewOwnedRoots
