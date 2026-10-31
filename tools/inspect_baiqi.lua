-- Read-only native-engine snapshot. Run in the GameCore_Tuner context of an isolated test game.
-- Not imported by the mod and never issues a game action.
local pid=Game.GetLocalPlayer()
local player=pid~=nil and Players[pid]
assert(player,"No local player")
local function Read(object,key)
  if object==nil or object[key]==nil then return "UNAVAILABLE" end
  local ok,value=pcall(object[key],object)
  return ok and tostring(value) or "ERROR"
end
print("BAIQI_SNAPSHOT",Game.GetCurrentGameTurn(),pid,PlayerConfigurations[pid]:GetLeaderTypeName(),player:GetTreasury():GetGoldBalance())
for _,city in player:GetCities():Members() do
  local queue=city:GetBuildQueue()
  print("BAIQI_CITY",city:GetID(),city:GetX(),city:GetY(),city:GetPopulation(),Read(queue,"GetSize"),Read(queue,"GetCurrentProductionTypeHash"),
    city:GetYield(YieldTypes.FOOD),city:GetGrowth():GetHousing(),city:GetBuildings():HasBuilding(GameInfo.Buildings.BUILDING_GRANARY.Index),
    city:GetBuildings():HasBuilding(GameInfo.Buildings.BUILDING_MONUMENT.Index))
end
for _,unit in player:GetUnits():Members() do
  local unitType=unit.GetType and unit:GetType() or unit:GetUnitType()
  print("BAIQI_UNIT",unit:GetID(),GameInfo.Units[unitType].UnitType,unit:GetX(),unit:GetY(),unit:GetMovesRemaining(),unit:GetFormationUnitCount())
end
local rights=Game.GetProperty("BAIQI_RIGHTS_V1")
if type(rights)=="table" and type(rights.leases)=="table" then
  for key,lease in pairs(rights.leases) do
    print("BAIQI_RIGHT",key,lease.id,lease.status,lease.sourceOwner,lease.sourceCityID,lease.recipientPlayer,lease.recipientCityID)
    local plot=Map.GetPlotByIndex(lease.sourceIndex)
    local city=plot and CityManager.GetCityAt(plot:GetX(),plot:GetY())
    if city then print("BAIQI_SOURCE_CITY",city:GetOwner(),city:GetID(),city:GetX(),city:GetY(),city:GetYield(YieldTypes.FOOD),city:GetGrowth():GetHousing(),
      city:GetBuildings():HasBuilding(GameInfo.Buildings.BUILDING_GRANARY.Index),plot:GetProperty("BAIQI_GRANARY_OUT")) end
  end
end
local journal=player:GetProperty("BAIQI_REQUISITION_V1")
if type(journal)=="table" and type(journal.operations)=="table" then
  for id,record in pairs(journal.operations) do
    if type(record)=="table" then print("BAIQI_OPERATION",id,record.kind,record.stage,record.phase,record.cost,record.balanceBefore,record.balanceAfter,record.reason) end
  end
end
