-- Reviewed from local-model policy candidate; player IDs must not be fixed to 0.
BaiqiPolicy = {}
local districtGreatPersonClasses={UNIT_GREAT_SCIENTIST="GREAT_PERSON_CLASS_SCIENTIST",
  UNIT_GREAT_ENGINEER="GREAT_PERSON_CLASS_ENGINEER",UNIT_GREAT_MERCHANT="GREAT_PERSON_CLASS_MERCHANT"}
local creativeGreatPersonClasses={UNIT_GREAT_WRITER="GREAT_PERSON_CLASS_WRITER",
  UNIT_GREAT_ARTIST="GREAT_PERSON_CLASS_ARTIST",UNIT_GREAT_MUSICIAN="GREAT_PERSON_CLASS_MUSICIAN"}

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

local function FlagTrue(value)
  return value==true or value==1 or value=="True" or value=="true"
end
local function FlagFalse(value)
  return value==false or value==0 or value=="False" or value=="false"
end
function BaiqiPolicy.UnownedBorderGreatPerson(unitType,info)
  return unitType=="UNIT_GREAT_MERCHANT" and type(info)=="table"
    and info.GreatPersonClassType=="GREAT_PERSON_CLASS_MERCHANT"
    and FlagFalse(info.ActionRequiresOwnedTile) and FlagTrue(info.ActionRequiresUnownedTile)
    and FlagTrue(info.ActionRequiresAdjacentOwnedTile) and info.ActionRequiresCompletedDistrictType==nil
    and FlagFalse(info.ActionRequiresCityStateTerritory) and FlagFalse(info.ActionRequiresSuzerainTerritory)
    and FlagFalse(info.ActionRequiresEnemyTerritory) and FlagFalse(info.ActionRequiresNonHostileTerritory)
end

-- Shared read-only validation, using each caller's own Core/UI bindings. No
-- native objects or authority decisions are passed between Lua contexts.
function BaiqiPolicy.GreatPersonActivationPlot(unitType,info,pid,plot,visibility,map)
  if not BaiqiPolicy.Number(pid) or pid<0 or pid%1~=0 or not plot or not visibility then return false end
  local x,y=plot:GetX(),plot:GetY()
  if visibility:IsRevealed(x,y)~=true or visibility:IsVisible(x,y)~=true then return false end
  if not BaiqiPolicy.UnownedBorderGreatPerson(unitType,info) then return plot:GetOwner()==pid end
  if plot:GetOwner()~=-1 or type(plot.IsWater)~="function" or plot:IsWater()~=false
    or type(plot.IsImpassable)~="function" or plot:IsImpassable()~=false
    or not map or type(map.GetAdjacentPlot)~="function" then return false end
  for direction=0,5 do
    local adjacent=map.GetAdjacentPlot(x,y,direction)
    if adjacent and visibility:IsRevealed(adjacent:GetX(),adjacent:GetY())==true
      and adjacent:GetOwner()==pid then return true end
  end
  return false
end

function BaiqiPolicy.CreativeGreatPersonClass(unitType)
  return creativeGreatPersonClasses[unitType]
end

function BaiqiPolicy.CivilianType(unitType)
  return unitType=="UNIT_SETTLER" or unitType=="UNIT_BUILDER" or unitType=="UNIT_TRADER"
    or unitType=="UNIT_MISSIONARY"
    or unitType=="UNIT_GREAT_PROPHET"
    or BaiqiPolicy.DistrictGreatPersonClass(unitType)~=nil or BaiqiPolicy.CreativeGreatPersonClass(unitType)~=nil
end

function BaiqiPolicy.ActionAllowed(unitType, operation)
  if operation=="SKIP_TURN" then return BaiqiPolicy.CivilianType(unitType) end
  if unitType=="UNIT_MISSIONARY" then return operation=="MOVE_TO" or operation=="SPREAD_RELIGION" end
  if unitType=="UNIT_GREAT_PROPHET" then return operation=="MOVE_TO" or operation=="FOUND_RELIGION" end
  if BaiqiPolicy.DistrictGreatPersonClass(unitType) then return operation=="MOVE_TO" or operation=="ACTIVATE_GREAT_PERSON" end
  if BaiqiPolicy.CreativeGreatPersonClass(unitType) then return operation=="MOVE_TO" or operation=="ACTIVATE_GREAT_PERSON" end
  if unitType=="UNIT_TRADER" then return operation=="MAKE_TRADE_ROUTE" end
  if unitType == "UNIT_SETTLER" then return operation == "MOVE_TO" or operation == "FOUND_CITY" end
  if unitType == "UNIT_BUILDER" then
    return operation == "MOVE_TO" or operation == "BUILD_IMPROVEMENT" or operation == "REPAIR"
  end
  return false
end

function BaiqiPolicy.MissionaryTarget(pid, religion, unitReligion, cityOwner, cityMajority, revealed, visible)
  if not BaiqiPolicy.Number(pid) or pid < 0 or pid % 1 ~= 0 or pid > 2147483647 then return false end
  if not BaiqiPolicy.Number(religion) or religion < 0 or religion % 1 ~= 0 or religion > 2147483647 then return false end
  if not BaiqiPolicy.Number(unitReligion) or unitReligion < 0 or unitReligion % 1 ~= 0 or unitReligion > 2147483647 then return false end
  if not BaiqiPolicy.Number(cityOwner) or cityOwner < 0 or cityOwner % 1 ~= 0 or cityOwner > 2147483647 then return false end
  if not BaiqiPolicy.Number(cityMajority) or cityMajority < -1 or cityMajority % 1 ~= 0 or cityMajority > 2147483647 then return false end
  if revealed ~= true or visible ~= true then return false end
  if unitReligion ~= religion then return false end
  if cityOwner ~= pid then return false end
  if cityMajority == religion then return false end
  return true
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
