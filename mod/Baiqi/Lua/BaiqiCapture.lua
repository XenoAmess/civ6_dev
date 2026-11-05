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

local function Integer(value)
  return BaiqiPolicy.Number(value) and value>=0 and value%1==0
end

local function ActorInWorld(unit)
  -- A consumed entity can retain its full ID, owner and movement in GameCore.
  -- Missing or failed native reads are not positive proof of availability.
  local ok,valid=pcall(function()
    if type(unit.IsDead)~="function" or type(unit.IsDelayedDeath)~="function"
      or unit:IsDead()~=false or unit:IsDelayedDeath()~=false then return false end
    local x,y=unit:GetX(),unit:GetY()
    if not Integer(x) or not Integer(y) or type(Map.GetGridSize)~="function"
      or type(Map.GetPlot)~="function" then return false end
    local width,height=Map.GetGridSize()
    if not Integer(width) or not Integer(height) or width<1 or height<1
      or x>=width or y>=height then return false end
    local plot=Map.GetPlot(x,y)
    return plot~=nil and plot:GetX()==x and plot:GetY()==y
  end)
  return ok and valid==true
end

local function Settle(player,journal,record,quote,recovering)
  if record.phase~="TRANSFERRED" and record.phase~="CHARGED" and record.phase~="FINISHING" then
    return Unknown(player,journal,record,"settlement_phase_unknown")
  end
  -- TRANSFERRED is a persisted positive receipt before any charge intent.
  -- CHARGING is deliberately excluded: a balance alone cannot prove a debit.
  if record.phase=="TRANSFERRED" then
    local treasury=player:GetTreasury()
    local before=treasury:GetGoldBalance()
    if not BaiqiPolicy.Number(before) or before<quote.cost then return Unknown(player,journal,record,"funds_changed_after_transfer") end
    record.phase,record.balanceBefore="CHARGING",before
    Persist(player,journal,record)
    local ok=pcall(function() treasury:ChangeGoldBalance(-quote.cost) end)
    local after=treasury:GetGoldBalance()
    if not ok or not BaiqiPolicy.Number(after) or math.abs(after-(before-quote.cost))>0.001 then
      return Unknown(player,journal,record,"charge_unresolved")
    end
    record.phase,record.chargeObserved,record.balanceAfter="CHARGED",true,after
    Persist(player,journal,record)
  end
  local unit=player:GetUnits():FindID(quote.unitID)
  if not BaiqiPolicy.MatchesID(unit,quote.unitID) or unit:GetOwner()~=quote.playerID then
    return Unknown(player,journal,record,"unit_changed_after_transfer")
  end
  if Game.GetCurrentGameTurn()~=quote.turn or BaiqiRequisition.Player(quote.playerID)==nil
    or not BaiqiRequisition.IsCaptureUnit(unit) or unit.GetFormationUnitCount==nil or unit:GetFormationUnitCount()~=1
    or not BaiqiPolicy.Number(unit:GetMovesRemaining()) or unit:GetMovesRemaining()<0
    or not ActorInWorld(unit) then
    return Unknown(player,journal,record,"settlement_context_changed")
  end
  record.phase="FINISHING"
  Persist(player,journal,record)
  local ok=pcall(function()
    unit:SetProperty("BAIQI_REQUISITION_TURN",quote.turn)
    -- Ending an already exhausted unit costs nothing further. Never take a
    -- later turn's movement during recovery; its turn is checked below.
    if unit:GetMovesRemaining()>0 then UnitManager.FinishMoves(unit) end
  end)
  if not ok or unit:GetMovesRemaining()~=0 then return Unknown(player,journal,record,"movement_unresolved") end
  record.stage=BaiqiPlanner.Transition(record.stage,"COMMIT",{correlated=true,engineSuccess=true,settled=true})
  record.phase,record.reason="DONE",recovering and "recovered" or "committed"
  Persist(player,journal,record)
  Log(record.id,record.stage,record.reason)
  return true,record.reason
end

local function Recoverable(playerID,player,journal,key,record)
  if (record.stage~="SUBMITTED" and record.stage~="UNKNOWN") or record.kind~="city"
    or record.playerID~=playerID or record.id~=key or type(key)~="string" or #key>128
    or not Integer(record.turn) or record.turn~=Game.GetCurrentGameTurn()
    or not Integer(record.unitID) or not Integer(record.targetOwner) or record.targetOwner==playerID
    or not Integer(record.cityID) or not Integer(record.newCityID) or not Integer(record.x) or not Integer(record.y)
    or not Integer(record.population) or record.population<1 or not Integer(record.cost)
    or record.cost~=C.cityCostBase+C.cityCostPerPopulation*record.population
    or record.transferObserved~=true or key~=BaiqiRequisition.RequestID(record) then return false end
  if record.phase~="TRANSFERRED" and record.phase~="CHARGED" and record.phase~="FINISHING" then return false end
  if record.phase=="TRANSFERRED" then
    if record.chargeObserved then return false end
  elseif record.chargeObserved~=true or not BaiqiPolicy.Number(record.balanceBefore)
    or not BaiqiPolicy.Number(record.balanceAfter) or record.balanceBefore<record.cost
    or math.abs(record.balanceAfter-(record.balanceBefore-record.cost))>0.001 then return false end
  for otherKey,other in pairs(journal.operations) do
    if otherKey~=key then
      if type(other)~="table" then return false end
      local retired=other.kind=="granary" or (type(other.id)=="string" and other.id:sub(1,8)=="granary:")
      if not retired and other.stage~="COMMITTED" and other.stage~="REJECTED"
        and (other.unitID==record.unitID or (other.x==record.x and other.y==record.y)) then return false end
    end
  end
  if not Map.GetPlot(record.x,record.y) then return false end
  local city=CityManager.GetCityAt(record.x,record.y)
  local unit=player:GetUnits():FindID(record.unitID)
  return BaiqiPolicy.MatchesID(city,record.newCityID) and city:GetOwner()==playerID
    and city:GetX()==record.x and city:GetY()==record.y
    and BaiqiPolicy.MatchesID(unit,record.unitID) and unit:GetOwner()==playerID
    and BaiqiRequisition.IsCaptureUnit(unit) and unit.GetFormationUnitCount~=nil and unit:GetFormationUnitCount()==1
    and BaiqiPolicy.Number(unit:GetMovesRemaining()) and unit:GetMovesRemaining()>=0
    and ActorInWorld(unit)
    and type(UnitManager.FinishMoves)=="function"
end

function BaiqiCapture.Recover(playerID)
  local player=BaiqiRequisition.Player(playerID)
  if player==nil then return end
  local journal=Journal(player)
  if journal==nil then return end
  for key,record in pairs(journal.operations) do
    if type(record)=="table" and (record.stage=="SUBMITTED" or record.stage=="UNKNOWN" or record.stage=="QUOTED")
      and type(record.id)=="string" and key==record.id and not active[key] then
      local readable,eligible=pcall(Recoverable,playerID,player,journal,key,record)
      if readable and eligible then
        active[key]=true
        local ok,success=pcall(Settle,player,journal,record,record,true)
        active[key]=nil
        if not ok and record.stage~="COMMITTED" then Unknown(player,journal,record,"recovery_interrupted") end
        if record.stage=="COMMITTED" then
          player:SetProperty("BAIQI_REQUISITION_RESULT",{id=key,stage="COMMITTED",reason="recovered"})
        end
      elseif record.stage~="UNKNOWN" then
        Unknown(player,journal,record,"interrupted_"..tostring(record.phase))
      end
    end
  end
end

local function Execute(player, journal, record, quote)
  local city = CityManager.GetCityAt(quote.x,quote.y)
  local unit = player:GetUnits():FindID(quote.unitID)
  if city == nil or city:GetOwner() ~= quote.targetOwner or city:GetID() ~= quote.cityID
    or not BaiqiPolicy.MatchesID(unit,quote.unitID) or unit:GetOwner()~=quote.playerID then
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
  return Settle(player,journal,record,quote,false)
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
