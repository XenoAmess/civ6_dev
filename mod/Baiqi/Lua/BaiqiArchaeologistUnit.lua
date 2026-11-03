BaiqiArchaeologistUnit={}
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
function BaiqiArchaeologistUnit.Read(player,pid,id)
  if not Integer(pid,2147483647) or not Integer(id,2147483647) then return nil end
  local ok,result=pcall(function()
    local units=Method(player,"GetUnits")(player)
    local unit=Method(units,"FindID")(units,id)
    assert(Method(unit,"GetID")(unit)==id and Method(unit,"GetOwner")(unit)==pid)
    assert(Object(GameInfo) and Object(GameInfo.Units))
    local row=GameInfo.Units[Method(unit,"GetType")(unit)]
    assert(Object(row) and row.UnitType=="UNIT_ARCHAEOLOGIST")
    local x,y=Method(unit,"GetX")(unit),Method(unit,"GetY")(unit)
    local moves=Method(unit,"GetMovesRemaining")(unit)
    local formation=Method(unit,"GetFormationUnitCount")(unit)
    assert(Integer(x,2147483647) and Integer(y,2147483647))
    assert(type(moves)=="number" and moves>=0 and moves<math.huge and moves==moves)
    assert(Integer(formation,64) and formation>=1)
    assert(unit:GetID()==id and unit:GetOwner()==pid)
    return {unitID=id,unitType="UNIT_ARCHAEOLOGIST",x=x,y=y,moves=moves,formation=formation}
  end)
  if ok then return result end
end
return BaiqiArchaeologistUnit