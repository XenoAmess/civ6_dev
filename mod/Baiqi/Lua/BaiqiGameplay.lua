-- EXECUTE_SCRIPT -> GameEvents route follows shipped BlackDeathScenario_StateUtils.
include("BaiqiConfig")
include("BaiqiPolicy")
include("BaiqiPlanner")
include("BaiqiRights")
include("BaiqiRequisition")
include("BaiqiCapture")
local STATE_KEY = "BAIQI_STATE_V1"

local function ReadState(player)
  local state = player:GetProperty(STATE_KEY)
  if state == nil then return {version=1, enabled=true, cities={}, units={}, protected={}} end
  if type(state) ~= "table" or state.version ~= 1 or type(state.cities) ~= "table"
    or type(state.units) ~= "table" or type(state.protected) ~= "table" then return nil end
  return state
end

local function OnSettings(playerID, params)
  if type(params) ~= "table" then return end
  local player = BaiqiRequisition.Player(playerID)
  if player == nil then return end
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
local function OnRequisition(playerID,params)
  local player=BaiqiRequisition.Player(playerID)
  if player==nil or type(params)~="table" or type(params.requestID)~="string" or #params.requestID>128 then return end
  local ok,success,reason=pcall(BaiqiCapture.Request,playerID,params)
  local journal=player:GetProperty(BaiqiConfig.requisitionKey)
  local record=journal and journal.operations and journal.operations[params.requestID]
  local stage=type(record)=="table" and record.stage or (ok and "REJECTED" or "UNKNOWN")
  player:SetProperty("BAIQI_REQUISITION_RESULT",{id=params.requestID,stage=stage,reason=ok and reason or "handler_error"})
  if not ok then print("BAIQI|requisition_handler_error|"..tostring(success)) end
end
GameEvents.BaiqiRequisition.Add(OnRequisition)
GameEvents.BaiqiRequisitionRecover.Add(function(playerID)
  BaiqiCapture.Recover(playerID)
  BaiqiRights.Refresh()
end)
GameEvents.OnGameTurnStarted.Add(BaiqiRights.Refresh)
GameEvents.BuildingPillageStateChanged.Add(BaiqiRights.Refresh)
GameEvents.BuildingConstructed.Add(BaiqiRights.Refresh)
Events.CityTransfered.Add(BaiqiRights.Refresh)
Events.CityRemovedFromMap.Add(BaiqiRights.Refresh)
Events.PlayerTurnActivated.Add(BaiqiRights.Refresh)
print("BAIQI|gameplay_loaded|version=1")
