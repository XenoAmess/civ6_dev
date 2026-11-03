BaiqiNaturalistPurchaseSnapshot={}
local MAX=2147483647
local function Integer(value,low,high)
  return type(value)=="number" and value>=low and value<=high and value%1==0
end
local function Object(value)
  return type(value)=="table" or type(value)=="userdata"
end
local function Method(object,name)
  assert(Object(object) and type(object[name])=="function")
  return object[name]
end

function BaiqiNaturalistPurchaseSnapshot.Read(player,pid,cityID)
  if not Integer(pid,0,MAX) or not Integer(cityID,0,MAX) then return nil end
  local ok,result=pcall(function()
    assert(Object(GameInfo) and Object(GameInfo.Units))
    assert(Object(BaiqiNaturalistUnit) and type(BaiqiNaturalistUnit.Read)=="function")

    local cities=Method(player,"GetCities")(player)
    local city=Method(cities,"FindID")(cities,cityID)
    assert(Object(city))
    assert(Method(city,"GetID")(city)==cityID and Method(city,"GetOwner")(city)==pid)
    local x,y=Method(city,"GetX")(city),Method(city,"GetY")(city)
    assert(Integer(x,0,MAX) and Integer(y,0,MAX))

    local religion=Method(player,"GetReligion")(player)
    assert(Object(religion))
    local balance=Method(religion,"GetFaithBalance")(religion)
    assert(type(balance)=="number" and balance==balance and balance>=0 and balance<math.huge)

    local units=Method(player,"GetUnits")(player)
    local naturalists={}
    local seenIDs={}
    local count=0
    for _,unit in Method(units,"Members")(units) do
      count=count+1
      if count>4096 then return nil end
      assert(Object(unit))
      local id=Method(unit,"GetID")(unit)
      assert(Integer(id,0,MAX))
      assert(Method(unit,"GetOwner")(unit)==pid)
      if seenIDs[id] then return nil end
      seenIDs[id]=true
      local typeIndex=Method(unit,"GetType")(unit)
      assert(Integer(typeIndex,0,MAX))
      local row=GameInfo.Units[typeIndex]
      assert(Object(row) and type(row.UnitType)=="string")
      if row.UnitType=="UNIT_NATURALIST" then
        local isDelayed=Method(unit,"IsDelayedDeath")(unit)
        assert(type(isDelayed)=="boolean")
        if not isDelayed then
          local snap=BaiqiNaturalistUnit.Read(player,pid,id)
          assert(snap)
          if snap then
            assert(snap.unitID==id)
            if #naturalists>=256 then return nil end
            naturalists[#naturalists+1]={
              unitID=snap.unitID,
              unitType=snap.unitType,
              charges=snap.charges,
              x=snap.x,
              y=snap.y,
              moves=snap.moves,
              formation=snap.formation
            }
          end
        end
      end
    end

    local freshCities=Method(player,"GetCities")(player)
    local city2=Method(freshCities,"FindID")(freshCities,cityID)
    assert(Object(city2))
    assert(Method(city2,"GetID")(city2)==cityID and Method(city2,"GetOwner")(city2)==pid)
    assert(Method(city2,"GetX")(city2)==x and Method(city2,"GetY")(city2)==y)
    local freshReligion=Method(player,"GetReligion")(player)
    local balance2=Method(freshReligion,"GetFaithBalance")(freshReligion)
    assert(balance2==balance)

    table.sort(naturalists,function(a,b) return a.unitID<b.unitID end)
    return {cityID=cityID,owner=pid,x=x,y=y,faithBalance=balance,naturalists=naturalists}
  end)
  if ok then return result end
end
return BaiqiNaturalistPurchaseSnapshot
