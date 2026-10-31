-- EXECUTE_SCRIPT -> GameEvents route follows shipped BlackDeathScenario_StateUtils.
local STATE_KEY = "BAIQI_STATE_V1"

local function ReadState(player)
  local state = player:GetProperty(STATE_KEY)
  if state == nil then return {version=1, enabled=true, cities={}, units={}, protected={}} end
  if type(state) ~= "table" or state.version ~= 1 or type(state.cities) ~= "table"
    or type(state.units) ~= "table" or type(state.protected) ~= "table" then return nil end
  return state
end

local function OnSettings(playerID, params)
  if type(params) ~= "table" or GameConfiguration.IsAnyMultiplayer() or GameConfiguration.IsHotseat() then return end
  local player, config = Players[playerID], PlayerConfigurations[playerID]
  if player == nil or config == nil or not config:IsHuman() or config:GetLeaderTypeName() ~= "LEADER_BAIQI" then return end
  if params.turn ~= Game.GetCurrentGameTurn() or not player:IsTurnActive() then return end
  if type(params.value) ~= "boolean" then return end
  local state = ReadState(player)
  if state == nil then return end
  if params.kind == "global" then
    state.enabled = params.value
  elseif params.kind == "city" then
    local city = player:GetCities():FindID(params.id)
    if city == nil or city:GetOwner() ~= playerID then return end
    state.cities[tostring(city:GetID())] = {paused=params.value, x=city:GetX(), y=city:GetY()}
  elseif params.kind == "unit" then
    local unit = player:GetUnits():FindID(params.id)
    if unit == nil or unit:GetOwner() ~= playerID then return end
    local definition = GameInfo.Units[unit:GetUnitType()]
    if definition == nil or (definition.UnitType ~= "UNIT_SETTLER" and definition.UnitType ~= "UNIT_BUILDER") then return end
    state.units[tostring(unit:GetID())] = params.value
  elseif params.kind == "protect" then
    local plot = Map.GetPlotByIndex(params.id)
    if plot == nil or plot:GetOwner() ~= playerID then return end
    state.protected[tostring(params.id)] = params.value
  else return end
  player:SetProperty(STATE_KEY, state)
  print("BAIQI|settings|player="..tostring(playerID).."|kind="..params.kind.."|id="..tostring(params.id).."|value="..tostring(params.value))
end

GameEvents.BaiqiSettings.Add(OnSettings)
print("BAIQI|gameplay_loaded|version=1")
