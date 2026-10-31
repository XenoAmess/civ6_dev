-- Reviewed from local-model policy candidate; player IDs must not be fixed to 0.
BaiqiPolicy = {}

function BaiqiPolicy.Number(value)
  return type(value) == "number" and value == value and math.abs(value) < math.huge
end

function BaiqiPolicy.Context(ctx)
  return type(ctx) == "table" and ctx.isBaiqi == true and ctx.activeTurn == true
    and ctx.enabled == true and BaiqiPolicy.Number(ctx.player) and ctx.player >= 0
    and ctx.player == ctx.localPlayer
end

function BaiqiPolicy.ActionAllowed(unitType, operation)
  if operation=="SKIP_TURN" then return unitType=="UNIT_SETTLER" or unitType=="UNIT_BUILDER" end
  if unitType == "UNIT_SETTLER" then return operation == "MOVE_TO" or operation == "FOUND_CITY" end
  if unitType == "UNIT_BUILDER" then
    return operation == "MOVE_TO" or operation == "BUILD_IMPROVEMENT" or operation == "REPAIR"
  end
  return false
end

function BaiqiPolicy.CanCivilian(ctx, unit)
  if not BaiqiPolicy.Context(ctx) then return false, "context_inactive" end
  if type(unit) ~= "table" or unit.owner ~= ctx.player then return false, "owner_mismatch" end
  if unit.type ~= "UNIT_SETTLER" and unit.type ~= "UNIT_BUILDER" then return false, "not_whitelisted" end
  if unit.formationCount ~= 1 then return false, "formation_or_unknown" end
  if not BaiqiPolicy.Number(unit.moves) or unit.moves <= 0 then return false, "no_moves" end
  return true, "eligible"
end
