-- Private natural-call observer; never included by the release mod.
return function(api, env)
  local observing=true
  local Unpack=unpack or table.unpack
  local stop,retire=api.Stop,api.Retire
  local function Pack(...) return {n=select('#',...),...} end
  local function Read(fn)
    local ok,value=pcall(fn)
    if ok then return value end
  end
  function api.Stop() observing=false;return stop() end
  function api.Retire() observing=false;return retire() end
  function api.Run(fn,caller,player,state,firstOnly,excluded,unitID,preferredIndex,oneValidation)
    if not observing then
      return fn(player,state,firstOnly,excluded,unitID,preferredIndex,oneValidation,nil)
    end
    local row={caller=caller or 'UNSPECIFIED',first_only=firstOnly==true,
      one_validation=oneValidation==true,preferred_supplied=preferredIndex~=nil,
      excluded_supplied=excluded~=nil,ai_available=false,hints_kind='NOT_CALLED',
      raw_hints=0,admitted=0,visited=0,cheap_pass=0,support_true=0,
      support_false=0,support_unknown=0,returned=0,exhausted=false,failed=false}
    row.turn_start=Read(env.turn)
    row.cities_start=Read(function() return player:GetCities():GetCount() end)
    row.started=Read(env.clock)
    local result=Pack(pcall(fn,player,state,firstOnly,excluded,unitID,preferredIndex,oneValidation,row))
    row.ended=Read(env.clock)
    row.turn_end=Read(env.turn)
    row.cities_end=Read(function() return player:GetCities():GetCount() end)
    row.failed=not result[1]
    if result[1] and type(result[2])=='table' then row.returned=#result[2] end
    row.exhausted=row.visited==row.admitted
    api.Record(row)
    if not result[1] then error(result[2],0) end
    return Unpack(result,2,result.n)
  end
end
