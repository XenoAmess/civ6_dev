-- Read-only compatibility metadata; not a proof that game behavior is closed.
local function Object(v) return type(v)=='table' or type(v)=='userdata' end
local function Value(v) if v==nil then return 'UNAVAILABLE' end;return v end
local BRIDGES={
 {'BaiqiGreatPersonIntentBridge',{'Inspect','Prepare','Observe'}},
 {'BaiqiCreativeIntentBridge',{'Inspect','Prepare'}},
 {'BaiqiReligiousIntentBridge',{'Inspect','Prepare'}},
 {'BaiqiNaturalistIntentBridge',{'Inspect','Prepare'}},
 {'BaiqiNaturalistPurchaseBridge',{'Inspect','Prepare'}},
 {'BaiqiArchaeologyBridge',{'Inspect','PrepareExcavation','PrepareChoice','PreparePendingChoice'}}
}
local function Specs(version)
  if version==nil then version=67 end
  assert(type(version)=='number' and version%1==0 and (version==67 or version==68 or version==69),'Invalid SourceVersion')
  if version==67 then return BRIDGES end
  local list={}
  for i,spec in ipairs(BRIDGES) do list[i]=spec end
  list[#list+1]={'BaiqiProphetIntentBridge',{'Inspect','Prepare','Observe'}}
  return list
end
local function Dump(env,emit)
  assert(type(env)=='table' and type(emit)=='function','Invalid metadata consumer')
  local localSpec=Specs(env.SourceVersion)
  local status={context_ok=false,clock_ok=false,available=0,unavailable=#localSpec,scope='metadata_only'}
  local function Summary() emit('SUMMARY',status.available,status.unavailable,status.context_ok,status.clock_ok,status.scope);return status end
  local ok,pid,turn,cities,idle=pcall(function()
    local pid,turn=env.Game.GetLocalPlayer(),env.Game.GetCurrentGameTurn()
    if pid~=0 or turn~=85 then return pid,turn end
    return pid,turn,env.Players[0]:GetCities():GetCount(),env.UI.IsGameCoreBusy()==false and env.UI.IsProcessingMessages()==false
  end)
  if not ok then emit('CONTEXT','UNAVAILABLE');return Summary() end
  emit('CONTEXT',Value(pid),Value(turn),Value(cities),Value(idle))
  status.context_ok=pid==0 and turn==85 and cities==10 and idle==true
  if not status.context_ok then return Summary() end
  local good,s=pcall(function() return env.Clock:Snapshot() end)
  if not good or type(s)~='table' then emit('CLOCK','UNAVAILABLE');return Summary() end
  local count=type(s.records)=='table' and #s.records or 'UNAVAILABLE'
  emit('CLOCK',Value(s.marker),Value(s.capacity),count,s.pending==nil,Value(s.subscribed),Value(s.retired),Value(s.errors),Value(s.refused))
  status.clock_ok=s.marker=='baiqi67-paired-clock-v1' and s.capacity==16 and count==0 and s.pending==nil
    and s.subscribed==true and s.retired==false and s.errors==0 and s.refused==0
  if not status.clock_ok then return Summary() end
  status.unavailable=0
  for _,spec in ipairs(localSpec) do
    local success,version,marker,types,qualified=pcall(function()
      local bridge=env.ExposedMembers[spec[1]];assert(Object(bridge))
      local version,marker=bridge.version,bridge.marker
      local qualified=version==1 and type(marker)=='string' and marker~=''
      local types={}
      for _,field in ipairs(spec[2]) do
        local kind=type(bridge[field]);types[#types+1]=field..':'..kind
        if kind~='function' then qualified=false end
      end
      return version,marker,table.concat(types,','),qualified
    end)
    if not success then emit('BRIDGE',spec[1],'UNAVAILABLE');status.unavailable=status.unavailable+1
    else
      emit('BRIDGE',spec[1],Value(version),Value(marker),types,qualified)
      if qualified then status.available=status.available+1 else status.unavailable=status.unavailable+1 end
    end
  end
  return Summary()
end
return Dump
