-- UI inventory proposal only; no excavation or artifact-choice permission.
BaiqiArchaeologyHome={}
local MAX=2147483647
local function Integer(value,maximum)
  return type(value)=="number" and value>=0 and value<=maximum and value%1==0
end
local function Object(value)
  return type(value)=="table" or type(value)=="userdata"
end
local function Method(object,name)
  assert(Object(object) and type(object[name])=="function")
  return object[name]
end
local function Identity(player,pid,id)
  local units=Method(player,"GetUnits")(player)
  local unit=Method(units,"FindID")(units,id)
  assert(Method(unit,"GetID")(unit)==id and Method(unit,"GetOwner")(unit)==pid)
  local unitType=Method(unit,"GetUnitType")(unit)
  assert(Integer(unitType,MAX))
  local row=GameInfo.Units[unitType]
  assert(Object(row) and row.UnitType=="UNIT_ARCHAEOLOGIST")
  local home=Method(unit,"GetArchaeologyHomeCity")(unit)
  assert(Integer(home,MAX))
  local cities=Method(player,"GetCities")(player)
  local city=Method(cities,"FindID")(cities,home)
  assert(Method(city,"GetID")(city)==home and Method(city,"GetOwner")(city)==pid)
  local x,y=Method(city,"GetX")(city),Method(city,"GetY")(city)
  assert(Integer(x,MAX) and Integer(y,MAX))
  local building=GameInfo.Buildings.BUILDING_ARCHAEOLOGICAL_MUSEUM
  assert(Object(building) and building.BuildingType=="BUILDING_ARCHAEOLOGICAL_MUSEUM"
    and Integer(building.Index,MAX))
  return {unitID=id,unitType="UNIT_ARCHAEOLOGIST",homeCityID=home,
    cityX=x,cityY=y,buildingIndex=building.Index},city
end
local function Inventory(city,index)
  local buildings=Method(city,"GetBuildings")(city)
  assert(Method(buildings,"HasBuilding")(buildings,index)==true
    and Method(buildings,"IsPillaged")(buildings,index)==false)
  local count=Method(buildings,"GetNumGreatWorkSlots")(buildings,index)
  assert(Integer(count,64) and count>=1)
  local slots,empty,works,seen={},{},{},{}
  for slot=0,count-1 do
    local kind=Method(buildings,"GetGreatWorkSlotType")(buildings,index,slot)
    assert(Integer(kind,MAX))
    local row=GameInfo.GreatWorkSlotTypes[kind]
    assert(Object(row) and row.GreatWorkSlotType=="GREATWORKSLOT_ARTIFACT")
    local work=Method(buildings,"GetGreatWorkInSlot")(buildings,index,slot)
    assert(work==-1 or (Integer(work,MAX) and not seen[work]))
    slots[#slots+1]={kind=kind,work=work}
    if work==-1 then empty[#empty+1]=slot
    else seen[work]=true;works[#works+1]=work end
  end
  table.sort(works)
  return {count=count,slots=slots,empty=empty,works=works}
end
local function SameIdentity(a,b)
  for key,value in pairs(a) do if b[key]~=value then return false end end
  return true
end
function BaiqiArchaeologyHome.Read(player,pid,id)
  if not Integer(pid,MAX) or not Integer(id,MAX) then return nil,"unavailable" end
  local ok,result=pcall(function()
    local first,city=Identity(player,pid,id)
    local inventory=Inventory(city,first.buildingIndex)
    local second,fresh=Identity(player,pid,id)
    assert(SameIdentity(first,second))
    local after=Inventory(fresh,second.buildingIndex)
    assert(inventory.count==after.count)
    for slot,entry in ipairs(inventory.slots) do
      assert(after.slots[slot].kind==entry.kind and after.slots[slot].work==entry.work)
    end
    local final=Identity(player,pid,id)
    assert(SameIdentity(first,final))
    first.slotCount=inventory.count
    first.emptySlots=inventory.empty
    first.workIndices=inventory.works
    return first
  end)
  if ok then return result,"ok" end
  return nil,"unavailable"
end
return BaiqiArchaeologyHome
