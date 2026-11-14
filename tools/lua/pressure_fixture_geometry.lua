-- Private new-map geometry only. City setup and pressure qualification are separate.
local function Keys(value, names)
  assert(type(value)=='table','Expected layout table')
  local allowed={};for _,name in ipairs(names) do allowed[name]=true end
  local count=0
  for name in pairs(value) do assert(allowed[name],'Unexpected layout field');count=count+1 end
  assert(count==#names,'Missing layout field')
end
local function Integer(value, maximum)
  assert(type(value)=='number' and value==value and value>=0 and value<math.huge
    and value%1==0 and (maximum==nil or value<=maximum),'Invalid integer')
  return value
end
local function Port(object,name)
  assert((type(object)=='table' or type(object)=='userdata')
    and type(object[name])=='function','Missing generation port: '..name)
end
return function(E,layout,variant)
  assert(type(E)=='table' and E.in_generation==true,'Generation context required')
  assert(variant=='NO_SITE' or variant=='MANY','Invalid geometry variant')
  Keys(layout,{'schema','fixture_id','width','height','wrap_x','slots'})
  assert(layout.schema=='civ6.pressure-layout/v1' and layout.fixture_id=='P6_PRESSURE_LAYOUT_V1',
    'Unexpected fixture')
  assert(layout.width==44 and layout.height==26 and layout.wrap_x==false,'Invalid dimensions')
  assert(type(layout.slots)=='table','Missing slots')
  local count=0
  for key in pairs(layout.slots) do Integer(key,11);assert(key>=1,'Invalid slot index');count=count+1 end
  assert(count==11,'Expected eleven slots')
  local occupied,starts,counts={},{},{[0]=0,[1]=0}
  for n=1,11 do
    local slot=layout.slots[n];Keys(slot,{'owner','x','y','start'})
    assert(slot.owner==0 or slot.owner==1,'Invalid slot owner')
    Integer(slot.x,43);Integer(slot.y,25)
    assert(type(slot.start)=='boolean','Invalid start flag')
    local index=slot.x+44*slot.y
    assert(not occupied[index],'Duplicate slot');occupied[index]=true
    counts[slot.owner]=counts[slot.owner]+1
    if slot.start then
      assert(starts[slot.owner]==nil,'Duplicate starting plot');starts[slot.owner]=index
    end
  end
  assert(counts[0]==10 and counts[1]==1 and starts[0]~=nil and starts[1]~=nil,'Invalid owners/starts')
  Integer(E.grass);Integer(E.ocean);Integer(E.hills)
  assert(E.grass~=E.ocean and E.grass~=E.hills and E.ocean~=E.hills,'Terrain indices must differ')
  Port(E.Map,'GetGridSize');Port(E.Map,'GetPlotByIndex')
  Port(E.TerrainBuilder,'SetTerrainType');Port(E.TerrainBuilder,'AnalyzeChokepoints')
  Port(E.TerrainBuilder,'StampContinents');Port(E.AreaBuilder,'Recalculate')
  assert(type(E.Players)=='table','Missing players')
  Port(E.Players[0],'SetStartingPlot');Port(E.Players[1],'SetStartingPlot')
  local width,height=E.Map.GetGridSize()
  assert(width==44 and height==26,'Actual grid mismatch')
  local plots={}
  for index=0,1143 do
    local plot=E.Map.GetPlotByIndex(index)
    Port(plot,'GetIndex');Port(plot,'GetX');Port(plot,'GetY')
    assert(plot:GetIndex()==index and plot:GetX()==index%44
      and plot:GetY()==math.floor(index/44),'Actual plot mismatch')
    plots[index]=plot
  end
  for index=0,1143 do
    local terrain=occupied[index] and E.grass or (variant=='NO_SITE' and E.ocean or E.hills)
    E.TerrainBuilder.SetTerrainType(plots[index],terrain)
  end
  E.AreaBuilder.Recalculate()
  E.TerrainBuilder.AnalyzeChokepoints()
  E.TerrainBuilder.StampContinents()
  E.Players[0]:SetStartingPlot(plots[starts[0]])
  E.Players[1]:SetStartingPlot(plots[starts[1]])
  return {status='MAP_GEOMETRY_READY',variant=variant,width=44,height=26,
    land_tiles=variant=='NO_SITE' and 11 or 1144,city_setup_complete=false}
end
