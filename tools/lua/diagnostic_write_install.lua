-- External diagnostic static-API subset; counter factory owns transparent forwarding.
local function InstallWrites(env, newCounter, getBucket)
  if type(env)~="table" then error("env must be table",0) end
  if type(newCounter)~="function" then error("newCounter must be function",0) end
  if type(getBucket)~="function" then error("getBucket must be function",0) end

  local specs = {
    {name="UnitManager", methods={"RequestOperation","RequestCommand"}},
    {name="CityManager", methods={"RequestOperation","RequestCommand"}},
    {name="UI", methods={"RequestPlayerOperation"}}
  }

  local originals = {}
  local proxies = {}
  local stats = {}

  for _, spec in ipairs(specs) do
    local name = spec.name
    local orig = env[name]
    if type(orig)~="table" then error("missing table for "..name,0) end
    originals[name] = orig

    local proxy, stat = newCounter(orig, spec.methods, name, getBucket)
    if type(proxy)~="table" then error("invalid proxy for "..name,0) end
    if type(stat)~="table" then error("invalid stats for "..name,0) end
    proxies[name] = proxy
    stats[name] = stat
  end

  for _, spec in ipairs(specs) do
    env[spec.name] = proxies[spec.name]
  end

  local function Restore(self)
    local result = {}
    for _, spec in ipairs(specs) do
      local name = spec.name
      if env[name] == proxies[name] then
        env[name] = originals[name]
        result[name] = true
      else
        result[name] = false
      end
    end
    return result
  end

  return {
    originals = originals,
    proxies = proxies,
    stats = stats,
    Restore = Restore
  }
end
return InstallWrites
