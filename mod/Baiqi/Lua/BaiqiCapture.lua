-- GameCore execution only. No action occurs while this file is loaded.
BaiqiCapture = {}
local C = BaiqiConfig
local active = {}

local function Log(id, stage, reason)
  print("BAIQI|requisition|id="..tostring(id).."|stage="..tostring(stage).."|reason="..tostring(reason))
end

local function Journal(player)
  local j = player:GetProperty(C.requisitionKey)
  if j == nil then return {version=1,operations={}} end
  if type(j) ~= "table" or j.version ~= 1 or type(j.operations) ~= "table" then return nil end
  return j
end

local function Persist(player, journal, record)
  journal.operations[record.id] = record
  journal.lastID = record.id
  player:SetProperty(C.requisitionKey, journal)
  local readback = player:GetProperty(C.requisitionKey)
  local seen = readback and readback.operations and readback.operations[record.id]
  if seen == nil or seen.phase ~= record.phase or seen.stage ~= record.stage then error("journal_write_not_observed") end
end

local function Unknown(player, journal, record, reason)
  record.stage = BaiqiPlanner.Transition("SUBMITTED", "UNKNOWN", {})
  record.reason = reason
  Persist(player,journal,record)
  Log(record.id,record.stage,reason)
  return false, reason
end

function BaiqiCapture.Recover(playerID)
  local player = BaiqiRequisition.Player(playerID)
  if player == nil then return end
  local journal = Journal(player)
  if journal == nil then return end
  for _,record in pairs(journal.operations) do
    if type(record) == "table" and record.stage ~= "COMMITTED" and record.stage ~= "REJECTED"
      and record.stage ~= "UNKNOWN" and not active[record.id] then
      Unknown(player,journal,record,"interrupted_"..tostring(record.phase))
    end
  end
end

local function Execute(player, journal, record, quote)
  local city = CityManager.GetCityAt(quote.x,quote.y)
  local unit = player:GetUnits():FindID(quote.unitID)
  if city == nil or city:GetOwner() ~= quote.targetOwner or city:GetID() ~= quote.cityID or unit == nil then
    return false,"owner_changed"
  end
  record.stage = BaiqiPlanner.Transition("QUOTED","SUBMIT",{confirmed=true,quoteValid=true})
  record.phase = "TRANSFERRING"
  Persist(player,journal,record)
  local ok = pcall(CityManager.TransferCity,city,quote.playerID)
  local acquired = CityManager.GetCityAt(quote.x,quote.y)
  if not ok or acquired == nil or acquired:GetOwner() ~= quote.playerID then
    return Unknown(player,journal,record,"transfer_unresolved")
  end
  record.phase, record.transferObserved, record.newCityID = "TRANSFERRED", true, acquired:GetID()
  Persist(player,journal,record)
  local treasury = player:GetTreasury()
  local before = treasury:GetGoldBalance()
  if not BaiqiPolicy.Number(before) or before < quote.cost then return Unknown(player,journal,record,"funds_changed_after_transfer") end
  record.phase, record.balanceBefore = "CHARGING", before
  Persist(player,journal,record)
  ok = pcall(function() treasury:ChangeGoldBalance(-quote.cost) end)
  local after = treasury:GetGoldBalance()
  if not ok or not BaiqiPolicy.Number(after) or math.abs(after-(before-quote.cost)) > 0.001 then
    return Unknown(player,journal,record,"charge_unresolved")
  end
  record.phase, record.chargeObserved, record.balanceAfter = "CHARGED", true, after
  Persist(player,journal,record)
  record.phase = "FINISHING"
  Persist(player,journal,record)
  ok = pcall(function()
    unit:SetProperty("BAIQI_REQUISITION_TURN",quote.turn)
    UnitManager.FinishMoves(unit)
  end)
  if not ok or unit:GetMovesRemaining() ~= 0 then return Unknown(player,journal,record,"movement_unresolved") end
  record.stage = BaiqiPlanner.Transition(record.stage,"COMMIT",{correlated=true,engineSuccess=true,settled=true})
  record.phase, record.reason = "DONE", "committed"
  Persist(player,journal,record)
  Log(record.id,record.stage,"committed")
  return true,"committed"
end

function BaiqiCapture.Request(playerID, params)
  local player = BaiqiRequisition.Player(playerID)
  if player == nil or type(params) ~= "table" or params.confirmed ~= true then return false,"not_confirmed" end
  if params.playerID ~= playerID or params.turn ~= Game.GetCurrentGameTurn() then return false,"stale_turn" end
  if type(params.requestID) ~= "string" or #params.requestID > 128 then return false,"invalid_request" end
  if (params.kind~=nil and params.kind~="city") or params.requestID:sub(1,5)~="city:" then return false,"invalid_target" end
  local journal = Journal(player)
  if journal == nil then return false,"journal_version" end
  BaiqiCapture.Recover(playerID)
  journal = Journal(player)
  local previous = journal.operations[params.requestID]
  if previous ~= nil then
    if type(previous) ~= "table" then return false,"journal_corrupt" end
    Log(params.requestID,previous.stage,"duplicate"); return previous.stage == "COMMITTED","duplicate"
  end
  local quote, reason = BaiqiRequisition.Quote(playerID,params.unitID,params.targetOwner,params.cityID,params.kind)
  if quote == nil then Log(params.requestID,"REJECTED",reason); return false,reason end
  if params.requestID ~= BaiqiRequisition.RequestID(quote) or params.x ~= quote.x or params.y ~= quote.y
    or params.cost ~= quote.cost or params.population ~= quote.population then return false,"quote_changed" end
  if BaiqiRequisition.Conflict(journal,quote.unitID,quote.x,quote.y) then return false,"pending_operation" end
  if type(CityManager.TransferCity) ~= "function" or type(UnitManager.FinishMoves) ~= "function" then return false,"engine_unavailable" end
  local record = {id=params.requestID,stage="QUOTED",phase="VALIDATED",turn=quote.turn,
    kind=quote.kind,playerID=playerID,unitID=quote.unitID,targetOwner=quote.targetOwner,cityID=quote.cityID,
    x=quote.x,y=quote.y,cost=quote.cost,population=quote.population}
  active[record.id] = true
  local ok,success,result = pcall(Execute,player,journal,record,quote)
  active[record.id] = nil
  if not ok then
    if record.stage == "COMMITTED" then Log(record.id,"COMMITTED","post_commit_error"); return true,"committed" end
    return Unknown(player,journal,record,"execution_interrupted")
  end
  return success,result
end
