-- External diagnostics only. Install once on an owned query-counter proxy.
-- Qualification times are inclusive, not additive exclusive mod CPU time.
local function InstallQualificationTiming(s, NewProfile, clock)
  if not s or not s.managerProxy or not NewProfile then return end
  local function pack(...) return {n=select('#',...),...} end
  local profile = NewProfile(clock, 4096)
  s.qualProfile = profile
  local names = {'CanStartOperation', 'CanStartCommand'}
  for _, name in ipairs(names) do
    local original = s.managerProxy[name]
    if type(original) == 'function' then
      local timed = profile:Wrap(name, original)
      s.managerProxy[name] = function(...)
        local e = s.currentEntry
        if not e then return original(...) end
        if not e.qual then e.qual = {} end
        local q = e.qual
        if not q[name] then q[name] = {seconds=0, samples=0, unknown=0} end
        local bucket = q[name]
        local count, dropped = #profile.samples, profile.dropped
        local out = pack(pcall(timed, ...))
        if #profile.samples > count and profile.dropped == dropped then
          local sample = profile.samples[#profile.samples]
          if sample.name == name then
            bucket.seconds = bucket.seconds + sample.seconds
            bucket.samples = bucket.samples + 1
          else
            bucket.unknown = bucket.unknown + 1
          end
        else
          bucket.unknown = bucket.unknown + 1
        end
        if not out[1] then error(out[2], 0) end
        return unpack(out, 2, out.n)
      end
    end
  end
end

return InstallQualificationTiming
