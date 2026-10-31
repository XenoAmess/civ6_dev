-- Shared read-only quote, usable from gameplay or either native map-input context.
include("BaiqiConfig")
include("BaiqiPolicy")
BaiqiRequisition = {}
local C = BaiqiConfig
local classes = {PROMOTION_CLASS_MELEE=true, PROMOTION_CLASS_ANTI_CAVALRY=true,
  PROMOTION_CLASS_LIGHT_CAVALRY=true, PROMOTION_CLASS_HEAVY_CAVALRY=true}
local function integer(n) return BaiqiPolicy.Number(n) and n >= 0 and n == math.floor(n) end

function BaiqiRequisition.RequestID(q)
  return table.concat({q.kind or "city",q.playerID,q.turn,q.unitID,q.targetOwner,q.cityID,q.x,q.y}, ":")
end

function BaiqiRequisition.Player(playerID)
  if not integer(playerID) or GameConfiguration.IsAnyMultiplayer()
    or (GameConfiguration.IsHotseat~=nil and GameConfiguration.IsHotseat()) then return nil end
  local player, config = Players[playerID], PlayerConfigurations[playerID]
  if player == nil or config == nil then return nil end
  local human
  if config.IsHuman~=nil then human=config:IsHuman()
  elseif player.IsHuman~=nil then human=player:IsHuman() end
  if human~=true or config:GetLeaderTypeName() ~= C.leader or player:IsTurnActive() ~= true then return nil end
  if UI ~= nil and playerID ~= Game.GetLocalPlayer() then return nil end
  return player
end

function BaiqiRequisition.Quote(playerID, unitID, targetOwner, cityID, kind)
  kind=kind or "city"
  if kind~="city" then return nil,"invalid_target" end
  local player = BaiqiRequisition.Player(playerID)
  if player == nil or not C.cityRequisition then return nil, "unavailable" end
  if not integer(unitID) or not integer(targetOwner) or not integer(cityID) or targetOwner == playerID then return nil, "invalid_target" end
  local targetPlayer = Players[targetOwner]
  local unit = player:GetUnits():FindID(unitID)
  local city = targetPlayer and targetPlayer:GetCities():FindID(cityID)
  if not BaiqiPolicy.MatchesID(unit,unitID) or not BaiqiPolicy.MatchesID(city,cityID)
    or unit:GetOwner() ~= playerID or city:GetOwner() ~= targetOwner then return nil, "owner_changed" end
  local visibility = PlayersVisibility[playerID]
  if visibility == nil or visibility:IsVisible(city:GetX(),city:GetY()) ~= true then return nil,"not_visible" end
  local unitType
  if unit.GetUnitType~=nil then unitType=unit:GetUnitType()
  elseif unit.GetType~=nil then unitType=unit:GetType() end
  local definition = unitType~=nil and GameInfo.Units[unitType]
  if definition == nil or definition.Domain ~= "DOMAIN_LAND" or classes[definition.PromotionClass] ~= true then return nil, "wrong_unit" end
  if unit.GetFormationUnitCount == nil or unit:GetFormationUnitCount() ~= 1 then return nil, "formation" end
  local moves = unit:GetMovesRemaining()
  if not BaiqiPolicy.Number(moves) or moves <= 0 then return nil, "no_moves" end
  local currentTurn = Game.GetCurrentGameTurn()
  if unit.GetProperty == nil or unit:GetProperty("BAIQI_REQUISITION_TURN") == currentTurn then return nil, "cooldown" end
  if player:GetDiplomacy():IsAtWarWith(targetOwner) ~= true then return nil, "not_at_war" end
  if Map.GetPlotDistance(unit:GetX(),unit:GetY(),city:GetX(),city:GetY()) ~= 1 then return nil, "not_adjacent" end
  local district
  if city.GetDistrictID~=nil then
    local id=city:GetDistrictID()
    district=targetPlayer:GetDistricts():FindID(id)
    if not BaiqiPolicy.MatchesID(district,id) then return nil,"defense_unknown" end
  elseif city.GetDistricts~=nil then district=city:GetDistricts():GetDistrict(GameInfo.Districts.DISTRICT_CITY_CENTER.Index) end
  if district == nil then return nil, "defense_unknown" end
  local maxHP, damage = district:GetMaxDamage(DefenseTypes.DISTRICT_GARRISON), district:GetDamage(DefenseTypes.DISTRICT_GARRISON)
  local maxOuter, outerDamage = district:GetMaxDamage(DefenseTypes.DISTRICT_OUTER), district:GetDamage(DefenseTypes.DISTRICT_OUTER)
  if not BaiqiPolicy.Number(maxHP) or not BaiqiPolicy.Number(damage) or maxHP <= 0 or damage < 0
    or not BaiqiPolicy.Number(maxOuter) or not BaiqiPolicy.Number(outerDamage) or maxOuter < 0 or outerDamage < 0 then return nil, "defense_unknown" end
  if maxOuter - outerDamage > 0 then return nil, "walls_remaining" end
  if math.max(0,maxHP-damage)*100 > maxHP*C.cityHealthPercent then return nil, "city_healthy" end
  local population = city:GetPopulation()
  if not integer(population) or population < 1 or not integer(currentTurn) then return nil, "state_unknown" end
  local cost = C.cityCostBase + C.cityCostPerPopulation*population
  local gold = player:GetTreasury():GetGoldBalance()
  if not BaiqiPolicy.Number(gold) or gold < cost then return nil, "insufficient_gold" end
  local quote={kind=kind,playerID=playerID, unitID=unitID, targetOwner=targetOwner, cityID=cityID,
    x=city:GetX(), y=city:GetY(), population=population, cost=cost, turn=currentTurn}
  return quote,"eligible"
end

function BaiqiRequisition.Conflict(journal, unitID, x, y)
  if journal == nil then return false end
  if type(journal) ~= "table" or journal.version ~= 1 or type(journal.operations) ~= "table" then return true end
  for _,record in pairs(journal.operations) do
    if type(record) ~= "table" then return true end
    local retired=record.kind=="granary" or (type(record.id)=="string" and record.id:sub(1,8)=="granary:")
    if not retired and record.stage ~= "COMMITTED" and record.stage ~= "REJECTED" then
      if record.unitID == unitID or (record.x == x and record.y == y) then return true end
    end
  end
  return false
end
