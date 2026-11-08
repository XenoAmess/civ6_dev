BaiqiMissionaryPurchaseSnapshot={}
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

function BaiqiMissionaryPurchaseSnapshot.Read(player,pid,cityID)
  if not Integer(pid,0,MAX) or not Integer(cityID,0,MAX) then return nil end
  local ok,result=pcall(function()
    assert(Object(GameInfo) and Object(GameInfo.Units))

    local cities=Method(player,"GetCities")(player)
    local city=Method(cities,"FindID")(cities,cityID)
    assert(Object(city))
    assert(Method(city,"GetOwner")(city)==pid and Method(city,"GetID")(city)==cityID)
    local x,y=Method(city,"GetX")(city),Method(city,"GetY")(city)
    assert(Integer(x,0,MAX) and Integer(y,0,MAX))

    local religion=Method(player,"GetReligion")(player)
    assert(Object(religion))
    local balance=Method(religion,"GetFaithBalance")(religion)
    assert(type(balance)=="number" and balance==balance and balance>=0 and balance<math.huge)
    local created=Method(religion,"GetReligionTypeCreated")(religion)
    assert(Integer(created,0,MAX))

    local cityReligion=Method(city,"GetReligion")(city)
    assert(Object(cityReligion))
    local majority=Method(cityReligion,"GetMajorityReligion")(cityReligion)
    assert(Integer(majority,-1,MAX))

    local units=Method(player,"GetUnits")(player)
    local missionaries={}
    local seenIDs={}
    local count=0
    for _,unit in Method(units,"Members")(units) do
      count=count+1
      if count>4096 then return nil end
      assert(Object(unit))
      local owner=Method(unit,"GetOwner")(unit)
      assert(Integer(owner,0,MAX))
      if owner==pid then
        local id=Method(unit,"GetID")(unit)
        assert(Integer(id,0,MAX))
        if seenIDs[id] then return nil end
        seenIDs[id]=true
        local typeIndex=Method(unit,"GetType")(unit)
        assert(Integer(typeIndex,0,MAX))
        local row=GameInfo.Units[typeIndex]
        assert(Object(row) and type(row.UnitType)=="string")
        if row.UnitType=="UNIT_MISSIONARY" then
          local isDelayed=Method(unit,"IsDelayedDeath")(unit)
          assert(type(isDelayed)=="boolean")
          if not isDelayed then
            local unitReligion=Method(unit,"GetReligion")(unit)
            assert(Object(unitReligion))
            local rIndex=Method(unitReligion,"GetReligionType")(unitReligion)
            assert(Integer(rIndex,0,MAX))
            local charges=Method(unitReligion,"GetSpreadCharges")(unitReligion)
            assert(Integer(charges,0,1000000))
            local ux,uy=Method(unit,"GetX")(unit),Method(unit,"GetY")(unit)
            assert(Integer(ux,0,MAX) and Integer(uy,0,MAX))
            local moves=Method(unit,"GetMovesRemaining")(unit)
            assert(type(moves)=="number" and moves==moves and moves>=0 and moves<math.huge)
            local formation
            if type(unit.GetFormationUnitCount)=="function" then formation=Method(unit,"GetFormationUnitCount")(unit) end
            assert(Integer(formation,1,64))
            if #missionaries>=256 then return nil end
            missionaries[#missionaries+1]={
              unitID=id,
              unitType="UNIT_MISSIONARY",
              religionIndex=rIndex,
              charges=charges,
              x=ux,
              y=uy,
              moves=moves,
              formation=formation
            }
          end
        end
      end
    end

    local freshCities=Method(player,"GetCities")(player)
    local city2=Method(freshCities,"FindID")(freshCities,cityID)
    assert(Object(city2))
    assert(Method(city2,"GetOwner")(city2)==pid and Method(city2,"GetID")(city2)==cityID)
    assert(Method(city2,"GetX")(city2)==x and Method(city2,"GetY")(city2)==y)
    local freshReligion=Method(player,"GetReligion")(player)
    local balance2=Method(freshReligion,"GetFaithBalance")(freshReligion)
    assert(balance2==balance)
    local created2=Method(freshReligion,"GetReligionTypeCreated")(freshReligion)
    assert(created2==created)
    local freshCityReligion=Method(city2,"GetReligion")(city2)
    local majority2=Method(freshCityReligion,"GetMajorityReligion")(freshCityReligion)
    assert(majority2==majority)

    table.sort(missionaries,function(a,b) return a.unitID<b.unitID end)
    return {
      cityID=cityID,
      owner=pid,
      x=x,
      y=y,
      faithBalance=balance,
      religionIndex=created,
      majorityReligion=majority,
      missionaries=missionaries
    }
  end)
  if ok then return result end
end
return BaiqiMissionaryPurchaseSnapshot
