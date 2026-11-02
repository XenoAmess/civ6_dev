-- External diagnostics only; the two clocks remain separate domains.
local function NewDualProfile(NewProfile, wallClock, cpuClock, capacity)
  local state={wall=NewProfile(wallClock,capacity),cpu=NewProfile(cpuClock,capacity)}
  function state:Wrap(name,fn)
    return self.wall:Wrap(name,self.cpu:Wrap(name,fn))
  end
  return state
end
return NewDualProfile
