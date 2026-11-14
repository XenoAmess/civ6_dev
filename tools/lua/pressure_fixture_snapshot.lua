-- Read-only private-fixture snapshot. Exporter must encode absent owner as JSON null.
local function Keys(value,names)
  assert(type(value)=='table','Expected layout table')
  local allowed={};for _,name in ipairs(names) do allowed[name]=true end
  local count=0;for name in pairs(value) do assert(allowed[name],'Unexpected layout field');count=count+1 end
  assert(count==#names,'Missing layout field')
end
local function Integer(value,maximum)
  assert(type(value)=='number' and value==value and value>=0 and value<=maximum and value%1==0,
    'Invalid integer')
  return value
end
local function Port(object,name)
  assert((type(object)=='table' or type(object)=='userdata') and type(object[name])=='function',
    'Missing snapshot port: '..name)
end
return function(E,layout)
  assert(type(E)=='table' and E.setup_stage=='READY','Private preparation ledger required')
  local paths={NO_SITE='P6PressureNoSite.lua',MANY='P6PressureMany.lua',MANY_WATER1='P6PressureManyWater1.lua'}
  assert(paths[E.variant]~=nil,'Invalid variant')
  Keys(layout,{'schema','fixture_id','width','height','wrap_x','slots'})
  assert(layout.schema=='civ6.pressure-layout/v1' and layout.fixture_id=='P6_PRESSURE_LAYOUT_V1'
    and layout.width==44 and layout.height==26 and layout.wrap_x==false,'Invalid layout')
  assert(type(layout.slots)=='table','Missing slots')
  local size=0
  for key in pairs(layout.slots) do Integer(key,11);assert(key>=1,'Invalid slot index');size=size+1 end
  assert(size==11,'Expected eleven slots')
  local expected,counts,starts={},{[0]=0,[1]=0},{[0]=0,[1]=0}
  for n=1,11 do
    local slot=layout.slots[n];Keys(slot,{'owner','x','y','start'})
    assert(slot.owner==0 or slot.owner==1,'Invalid owner')
    Integer(slot.x,43);Integer(slot.y,25);assert(type(slot.start)=='boolean','Invalid start flag')
    local index=slot.x+44*slot.y;assert(expected[index]==nil,'Duplicate slot')
    expected[index]=slot.owner;counts[slot.owner]=counts[slot.owner]+1
    if slot.start then starts[slot.owner]=starts[slot.owner]+1 end
  end
  assert(counts[0]==10 and counts[1]==1 and starts[0]==1 and starts[1]==1,'Invalid owners/starts')
  assert(type(E.GetTurn)=='function','Missing turn reader')
  Port(E.MapConfiguration,'GetValue');Port(E.Map,'GetGridSize');Port(E.Map,'GetPlotByIndex')
  assert(E.MapConfiguration.GetValue('MAP_SCRIPT')==
    '{e8b15363-c9b9-4dcb-b575-117d9308d426}Maps/'..paths[E.variant],'Wrong private map')
  local width,height=E.Map.GetGridSize();assert(width==44 and height==26,'Actual map mismatch')
  Port(E.Visibility,'IsVisible');assert(type(E.Players)=='table','Missing players')
  local turn=Integer(E.GetTurn(),2147483647)
  local plots={}
  -- No terrain, city or foreign owner reads until complete visibility is known.
  for index=0,1143 do
    local p=E.Map.GetPlotByIndex(index)
    for _,name in ipairs({'GetIndex','GetX','GetY','IsWater','IsCity','GetOwner'}) do Port(p,name) end
    assert(p:GetIndex()==index and p:GetX()==index%44 and p:GetY()==math.floor(index/44),
      'Incoherent actual geometry')
    assert(E.Visibility:IsVisible(index%44,math.floor(index/44))==true,'Entire map must be visible')
    plots[index]=p
  end
  local cities,actual,identities={},{},{}
  for owner=0,1 do
    local player=E.Players[owner];Port(player,'GetCities')
    local collection=player:GetCities();Port(collection,'GetCount');Port(collection,'Members')
    assert(collection:GetCount()==counts[owner],'Wrong city count')
    local count=0
    for _,city in collection:Members() do
      count=count+1;assert(count<=counts[owner],'Extra city iterator entry')
      for _,name in ipairs({'GetOwner','GetID','GetX','GetY'}) do Port(city,name) end
      assert(city:GetOwner()==owner,'Wrong city owner')
      local id=Integer(city:GetID(),2147483647)
      local x,y=Integer(city:GetX(),43),Integer(city:GetY(),25)
      local index=x+44*y;local key=owner..':'..id
      assert(expected[index]==owner and actual[index]==nil and not identities[key],
        'Wrong city identity/location')
      actual[index]=owner;identities[key]=true
      cities[#cities+1]={owner=owner,id=id,x=x,y=y}
    end
    assert(count==counts[owner],'Missing city iterator entry')
  end
  table.sort(cities,function(a,b)if a.owner~=b.owner then return a.owner<b.owner end;return a.id<b.id end)
  local rows={}
  for index=0,1143 do
    local p=plots[index];local water,city=p:IsWater(),p:IsCity()
    assert(type(water)=='boolean' and type(city)=='boolean','Unknown plot content')
    assert(city==(actual[index]~=nil),'City footprint mismatch')
    local owner=nil
    if city then
      owner=Integer(p:GetOwner(),1)
      assert(not water and owner==actual[index],'City terrain/owner mismatch')
    end
    rows[#rows+1]={index=index,x=index%44,y=math.floor(index/44),water=water,city=city,
      visible=true,owner=owner}
  end
  assert(Integer(E.GetTurn(),2147483647)==turn,'Turn changed during snapshot')
  return {source='baiqi-pressure-geometry-v1',fixture_id=layout.fixture_id,variant=E.variant,
    setup_stage='READY',turn=turn,width=44,height=26,cities=cities,plots=rows}
end
