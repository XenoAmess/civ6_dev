-- Reviewed from local-model policy candidate; player IDs must not be fixed to 0.
BaiqiPolicy = {}
local districtGreatPersonClasses={UNIT_GREAT_SCIENTIST="GREAT_PERSON_CLASS_SCIENTIST",
  UNIT_GREAT_ENGINEER="GREAT_PERSON_CLASS_ENGINEER",UNIT_GREAT_MERCHANT="GREAT_PERSON_CLASS_MERCHANT"}

function BaiqiPolicy.Number(value)
  return type(value) == "number" and value == value and math.abs(value) < math.huge
end

-- Native collection FindID can return a new object occupying an old slot.
function BaiqiPolicy.MatchesID(object, id)
  local kind=type(object)
  return (kind=="table" or kind=="userdata") and BaiqiPolicy.Number(id) and id>=0 and id%1==0
    and object.GetID~=nil and object:GetID()==id
end

function BaiqiPolicy.Context(ctx)
  return type(ctx) == "table" and ctx.isBaiqi == true and ctx.activeTurn == true
    and ctx.enabled == true and BaiqiPolicy.Number(ctx.player) and ctx.player >= 0
    and ctx.player == ctx.localPlayer
end

function BaiqiPolicy.DistrictGreatPersonClass(unitType)
  return districtGreatPersonClasses[unitType]
end

function BaiqiPolicy.CivilianType(unitType)
  return unitType=="UNIT_SETTLER" or unitType=="UNIT_BUILDER" or unitType=="UNIT_TRADER"
    or BaiqiPolicy.DistrictGreatPersonClass(unitType)~=nil
end

function BaiqiPolicy.ActionAllowed(unitType, operation)
  if operation=="SKIP_TURN" then return BaiqiPolicy.CivilianType(unitType) end
  if BaiqiPolicy.DistrictGreatPersonClass(unitType) then return operation=="MOVE_TO" or operation=="ACTIVATE_GREAT_PERSON" end
  if unitType=="UNIT_TRADER" then return operation=="MAKE_TRADE_ROUTE" end
  if unitType == "UNIT_SETTLER" then return operation == "MOVE_TO" or operation == "FOUND_CITY" end
  if unitType == "UNIT_BUILDER" then
    return operation == "MOVE_TO" or operation == "BUILD_IMPROVEMENT" or operation == "REPAIR"
  end
  return false
end

function BaiqiPolicy.CanCivilian(ctx, unit)
  if not BaiqiPolicy.Context(ctx) then return false, "context_inactive" end
  if type(unit) ~= "table" or unit.owner ~= ctx.player then return false, "owner_mismatch" end
  if not BaiqiPolicy.CivilianType(unit.type) then return false, "not_whitelisted" end
  if unit.type=="UNIT_TRADER" and unit.tradeIdle~=true then return false,"trade_not_idle" end
  if unit.formationCount ~= 1 then return false, "formation_or_unknown" end
  if not BaiqiPolicy.Number(unit.moves) or unit.moves <= 0 then return false, "no_moves" end
  return true, "eligible"
end
