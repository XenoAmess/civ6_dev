-- Read-only UI-context evidence. A snapshot does not prove training causality.
local M = {}

local function finite(value)
  return type(value) == "number" and value == value
    and value ~= math.huge and value ~= -math.huge
end

local function integer(value, minimum)
  return finite(value) and value % 1 == 0 and math.abs(value) <= 9007199254740991
    and (minimum == nil or value >= minimum)
end

local function need(condition)
  if not condition then error("READ_FAILED", 0) end
end

local function read(env, cityId)
  need(integer(cityId, 1))
  local game, players, info = env.Game, env.Players, env.GameInfo
  local pid = game.GetLocalPlayer()
  need(integer(pid, 0) and pid == 0)
  need(env.GameConfiguration.IsAnyMultiplayer() == false)
  need(env.PlayerConfigurations[pid]:GetLeaderTypeName() == "LEADER_BAIQI")
  local player = players[pid]
  local city = player:GetCities():FindID(cityId)
  need(city ~= nil and city:GetID() == cityId)
  local row = info.Units.UNIT_ARCHAEOLOGIST
  need(row ~= nil and integer(row.Index, 0) and integer(row.Hash))
  local queue = city:GetBuildQueue()
  local result = {
    turn = game.GetCurrentGameTurn(), player_id = pid, city_id = cityId,
    population = city:GetPopulation(),
    production_yield = city:GetYield(env.YieldTypes.PRODUCTION),
    gold = player:GetTreasury():GetGoldBalance(),
    unit_index = row.Index, unit_hash = row.Hash,
    unit_progress = queue:GetUnitProgress(row.Index), unit_cost = queue:GetUnitCost(row.Index),
    queue_size = queue:GetSize(), queue_type_hash = queue:GetCurrentProductionTypeHash(),
    archaeologists = {}
  }
  need(integer(result.turn, 0) and integer(result.population, 0))
  need(finite(result.production_yield) and finite(result.gold))
  need(finite(result.unit_progress) and result.unit_progress >= 0)
  need(finite(result.unit_cost) and result.unit_cost >= 0)
  need(integer(result.queue_size, 0) and integer(result.queue_type_hash))
  local head = queue:GetAt(0)
  if head ~= nil then
    result.head = {}
    for _, pair in ipairs({{"UnitType", "unit_index"}, {"BuildingType", "building_index"},
      {"DistrictType", "district_index"}, {"ProjectType", "project_index"}}) do
      local value = head[pair[1]]
      if value ~= nil then
        need(integer(value, 0))
        result.head[pair[2]] = value
      end
    end
  end
  local seen = {}
  for _, unit in player:GetUnits():Members() do
    local kind = unit:GetUnitType()
    need(integer(kind, 0))
    if kind == row.Index then
      local item = {id = unit:GetID(), owner = unit:GetOwner(), type_index = kind,
        x = unit:GetX(), y = unit:GetY(), moves = unit:GetMovesRemaining(),
        home_city = unit:GetArchaeologyHomeCity()}
      need(integer(item.id, 0) and not seen[item.id])
      need(integer(item.owner, 0) and item.owner == pid)
      need(integer(item.x) and integer(item.y) and integer(item.home_city, -1))
      need(finite(item.moves) and item.moves >= 0)
      seen[item.id] = true
      result.archaeologists[#result.archaeologists + 1] = item
    end
  end
  table.sort(result.archaeologists, function(a, b) return a.id < b.id end)
  return result
end

function M.Read(env, cityId)
  local ok, result = pcall(read, env, cityId)
  if not ok then return nil, "READ_FAILED" end
  return result, nil
end

return M
