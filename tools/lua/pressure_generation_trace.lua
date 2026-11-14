-- Private generation boundaries only; logger failure never changes a native call.
local Unpack=unpack or table.unpack
local function Pack(...)return {n=select('#',...),...}end
local function Port(object,name)
  assert((type(object)=='table' or type(object)=='userdata') and type(object[name])=='function',
    'Missing actual generation port: '..name)
end
local function Enum(value)
  assert(type(value)=='number' and value==value and value>=0 and value<math.huge and value%1==0,
    'Invalid actual terrain index')
end
return function(E,emit)
  assert(type(E)=='table' and E.in_generation==true and type(emit)=='function','Invalid trace inputs')
  Port(E.Map,'GetGridSize');Port(E.Map,'GetPlotByIndex')
  Port(E.TerrainBuilder,'SetTerrainType');Port(E.TerrainBuilder,'AnalyzeChokepoints')
  Port(E.TerrainBuilder,'StampContinents');Port(E.AreaBuilder,'Recalculate')
  assert(type(E.Players)=='table','Missing actual players')
  Port(E.Players[0],'SetStartingPlot');Port(E.Players[1],'SetStartingPlot')
  Enum(E.grass);Enum(E.ocean);Enum(E.hills)
  assert(E.grass~=E.ocean and E.grass~=E.hills and E.ocean~=E.hills,'Repeated terrain index')
  local attempted,completed,loggingErrors=0,0,0
  local function Emit(stage,n)
    local ok=pcall(emit,stage,n)
    if not ok then loggingErrors=loggingErrors+1 end
  end
  local function Invoke(stage,fn,...)
    Emit(stage..'_BEGIN',0)
    local result=Pack(pcall(fn,...))
    if not result[1] then Emit(stage..'_ERROR',0);error(result[2],0) end
    Emit(stage..'_END',0)
    return Unpack(result,2,result.n)
  end
  local setTerrain=E.TerrainBuilder.SetTerrainType
  local terrain={SetTerrainType=function(...)
    assert(attempted<1144,'Extra terrain attempt rejected')
    if attempted==0 then Emit('TERRAIN_BEGIN',0) end
    attempted=attempted+1
    local result=Pack(pcall(setTerrain,...))
    if not result[1] then Emit('TERRAIN_ERROR',attempted);error(result[2],0) end
    completed=completed+1
    if completed%128==0 then Emit('TERRAIN_PROGRESS',completed) end
    if completed==1144 then Emit('TERRAIN_END',1144) end
    return Unpack(result,2,result.n)
  end}
  local choke,continents=E.TerrainBuilder.AnalyzeChokepoints,E.TerrainBuilder.StampContinents
  terrain.AnalyzeChokepoints=function(...)return Invoke('CHOKE',choke,...)end
  terrain.StampContinents=function(...)return Invoke('CONTINENTS',continents,...)end
  local recalculate=E.AreaBuilder.Recalculate
  local area={Recalculate=function(...)return Invoke('AREA',recalculate,...)end}
  local players={}
  for owner=0,1 do
    local original=E.Players[owner];local setStart=original.SetStartingPlot;local stage='START'..owner
    players[owner]={SetStartingPlot=function(self,...)return Invoke(stage,setStart,original,...)end}
  end
  local wrapped={in_generation=E.in_generation,Map=E.Map,TerrainBuilder=terrain,AreaBuilder=area,
    Players=players,grass=E.grass,ocean=E.ocean,hills=E.hills}
  local function Snapshot()
    return {terrain_attempts=attempted,terrain_completed=completed,logging_errors=loggingErrors}
  end
  return wrapped,Snapshot
end
