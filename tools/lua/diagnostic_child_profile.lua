-- External diagnostics only; getRoot identifies an already measured caller.
local function Pack(...)
  return {n=select("#",...),...}
end

local function WrapChild(profile,name,fn,getRoot)
  assert(type(profile)=="table" and type(name)=="string" and type(fn)=="function","Invalid child profile target")
  local timed=profile:Wrap(name,fn)
  return function(...)
    local ok,root=pcall(getRoot)
    if not ok then profile.metadataErrors=(profile.metadataErrors or 0)+1 end
    if not ok or type(root)~="table" then return fn(...) end
    local rootId,rootTurn,rootCities=root.id,root.turnBefore,root.citiesBefore
    local beforeCount,beforeDropped,beforeInvalid=#profile.samples,profile.dropped,profile.invalidClock
    local result=Pack(pcall(timed,...))
    if #profile.samples>beforeCount and profile.dropped==beforeDropped and profile.invalidClock==beforeInvalid then
      local sample=profile.samples[#profile.samples]
      if sample.name==name then
        sample.rootId=rootId
        sample.rootTurn=rootTurn
        sample.rootCities=rootCities
      end
    end
    if not result[1] then error(result[2],0) end
    return unpack(result,2,result.n)
  end
end
return WrapChild
