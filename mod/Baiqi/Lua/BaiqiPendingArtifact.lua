-- UI-only readback. A descriptor is not permission to choose or excavate.
local function Integer(value)
  return type(value)=="number" and value>=0 and value<=2147483647 and value%1==0
end
local function Object(value)
  return type(value)=="table" or type(value)=="userdata"
end
local function Method(object,name)
  assert(Object(object) and type(object[name])=="function")
  return object[name]
end
return function(pid,player,game,gameInfo,configurations)
  if not Integer(pid) then return nil,"unavailable" end
  local ok,descriptor,status=pcall(function()
    local units=Method(player,"GetUnits")(player)
    local unit=Method(units,"GetNextExtractingArchaeologist")(units)
    -- Other unit components can expose an artifact index without an extraction.
    -- Only the engine's pending queue establishes the phase in which it is read.
    if unit==nil then return nil,"none" end
    assert(Object(unit))
    local id=Method(unit,"GetID")(unit)
    assert(Integer(id) and Method(unit,"GetOwner")(unit)==pid)
    assert(Object(gameInfo) and Object(gameInfo.Units))
    local function Archaeologist(value)
      local definition=gameInfo.Units[Method(value,"GetUnitType")(value)]
      return Object(definition) and definition.UnitType=="UNIT_ARCHAEOLOGIST"
    end
    assert(Archaeologist(unit))
    local live=Method(units,"FindID")(units,id)
    assert(Object(live) and Method(live,"GetID")(live)==id
      and Method(live,"GetOwner")(live)==pid and Archaeologist(live))
    local home=Method(live,"GetArchaeologyHomeCity")(live)
    assert(Integer(home))
    local cities=Method(player,"GetCities")(player)
    local city=Method(cities,"FindID")(cities,home)
    assert(Object(city) and Method(city,"GetID")(city)==home and Method(city,"GetOwner")(city)==pid)
    local x,y=Method(live,"GetX")(live),Method(live,"GetY")(live)
    assert(Integer(x) and Integer(y))
    local archaeology=Method(live,"GetArchaeology")(live)
    local index=Method(archaeology,"GetArtifactIndex")(archaeology)
    assert(Integer(index))
    local artifact=Method(game,"GetArtifactByIndex")(index)
    assert(Object(artifact) and Integer(artifact.Type) and artifact.Type<=5)
    local acting=artifact.ActingPlayerID
    assert(Integer(acting) and Object(configurations) and Object(configurations[acting]))
    local target
    if artifact.Type==0 or artifact.Type==3 or artifact.Type==4 then
      target=artifact.TargetPlayerID
      assert(Integer(target) and Object(configurations[target]))
    end
    return {unitID=id,unitType="UNIT_ARCHAEOLOGIST",homeCityID=home,x=x,y=y,
      artifactIndex=index,artifactType=artifact.Type,actingPlayerID=acting,
      choicePlayerID=acting,targetPlayerID=target},"pending"
  end)
  if not ok then return nil,"unavailable" end
  return descriptor,status
end
