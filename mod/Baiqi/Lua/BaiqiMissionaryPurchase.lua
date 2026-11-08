BaiqiMissionaryPurchase={}
local MAX=2147483647
local function Integer(value,low,high)
  return type(value)=="number" and value>=low and value<=high and value%1==0
end
local function Number(value)
  return type(value)=="number" and value==value and value>-math.huge and value<math.huge
end
local function Object(value)
  return type(value)=="table" or type(value)=="userdata"
end
local function Method(object,name)
  assert(Object(object) and type(object[name])=="function")
  return object[name]
end
local function NativeNumber(value)
  assert(Integer(value,-2147483648,4294967295))
  return value
end
local function Read(E,player,pid,id,x,y,reserve)
  assert(Object(E) and Object(E.GameInfo) and Object(E.GameInfo.Units) and Object(E.GameInfo.Yields))
  local unit=E.GameInfo.Units.UNIT_MISSIONARY
  local faith=E.GameInfo.Yields.YIELD_FAITH
  assert(Object(unit) and unit.UnitType=="UNIT_MISSIONARY" and unit.MustPurchase==true and unit.PurchaseYield=="YIELD_FAITH" and Object(faith))
  local hash=NativeNumber(unit.Hash)
  assert(Integer(faith.Index,0,MAX))
  local yieldIndex=faith.Index
  assert(Object(E.MilitaryFormationTypes) and Object(E.CityCommandTypes))
  local formation=NativeNumber(E.MilitaryFormationTypes.STANDARD_MILITARY_FORMATION)
  local operation=NativeNumber(E.CityCommandTypes.PURCHASE)
  local unitKey=NativeNumber(E.CityCommandTypes.PARAM_UNIT_TYPE)
  local yieldKey=NativeNumber(E.CityCommandTypes.PARAM_YIELD_TYPE)
  local formationKey=NativeNumber(E.CityCommandTypes.PARAM_MILITARY_FORMATION_TYPE)
  assert(unitKey~=yieldKey and unitKey~=formationKey and yieldKey~=formationKey)
  local cities=Method(player,"GetCities")(player)
  local city=Method(cities,"FindID")(cities,id)
  assert(Method(city,"GetID")(city)==id and Method(city,"GetOwner")(city)==pid)
  assert(Method(city,"GetX")(city)==x and Method(city,"GetY")(city)==y)
  local gold=Method(city,"GetGold")(city)
  local cost=Method(gold,"GetPurchaseCost")(gold,yieldIndex,hash,formation)
  local religion=Method(player,"GetReligion")(player)
  local balance=Method(religion,"GetFaithBalance")(religion)
  assert(Number(cost) and cost>0 and Number(balance) and balance>=0 and balance-cost>=reserve)
  local pr=religion
  local created=Method(pr,"GetReligionTypeCreated")(pr)
  assert(Integer(created,0,MAX))
  local cr=Method(city,"GetReligion")(city)
  local majority=Method(cr,"GetMajorityReligion")(cr)
  assert(majority==created)
  return {city=city,operation=operation,unitKey=unitKey,yieldKey=yieldKey,formationKey=formationKey,
    quote={cityID=id,owner=pid,x=x,y=y,unitType="UNIT_MISSIONARY",unitHash=hash,religionIndex=created,
      faithYieldIndex=yieldIndex,formationType=formation,cost=cost,faithBalance=balance,operation=operation,unitKey=unitKey,yieldKey=yieldKey,formationKey=formationKey}}
end
function BaiqiMissionaryPurchase.Quote(E,player,pid,city,reserve)
  if not Integer(pid,0,MAX) or not Number(reserve) or reserve<0 then return nil end
  local ok,result=pcall(function()
    local id=Method(city,"GetID")(city)
    local owner=Method(city,"GetOwner")(city)
    local x,y=Method(city,"GetX")(city),Method(city,"GetY")(city)
    assert(Integer(id,0,MAX) and owner==pid and Integer(x,0,MAX) and Integer(y,0,MAX))
    local before=Read(E,player,pid,id,x,y,reserve)
    local q=before.quote
    local params={[before.unitKey]=q.unitHash,[before.yieldKey]=q.faithYieldIndex,[before.formationKey]=q.formationType}
    local qualify=Method(E.CityManager,"CanStartCommand")
    assert(qualify(before.city,before.operation,false,params,true)==true)
    local after=Read(E,player,pid,id,x,y,reserve)
    for _,key in ipairs({"operation","unitKey","yieldKey","formationKey"}) do assert(before[key]==after[key]) end
    for key,value in pairs(q) do assert(after.quote[key]==value) end
    return after.quote
  end)
  if ok then return result end
end
return BaiqiMissionaryPurchase
