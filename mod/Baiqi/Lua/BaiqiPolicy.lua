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
    or unitType=="UNIT_NATURALIST" or unitType=="UNIT_ARCHAEOLOGIST"
    or unitType=="UNIT_GREAT_PROPHET"
    or BaiqiPolicy.DistrictGreatPersonClass(unitType)~=nil or BaiqiPolicy.CreativeGreatPersonClass(unitType)~=nil
end

function BaiqiPolicy.ActionAllowed(unitType, operation)
  if operation=="SKIP_TURN" then return BaiqiPolicy.CivilianType(unitType) end
  if unitType=="UNIT_ARCHAEOLOGIST" then return operation=="MOVE_TO" or operation=="EXCAVATE" end
  if unitType=="UNIT_NATURALIST" then return operation=="MOVE_TO" or operation=="DESIGNATE_PARK" end
  if unitType=="UNIT_MISSIONARY" then return operation=="MOVE_TO" or operation=="SPREAD_RELIGION" end
  if unitType=="UNIT_GREAT_PROPHET" then return operation=="MOVE_TO" or operation=="FOUND_RELIGION" end
  if BaiqiPolicy.DistrictGreatPersonClass(unitType) then return operation=="MOVE_TO" or operation=="ACTIVATE_GREAT_PERSON" end
  if BaiqiPolicy.CreativeGreatPersonClass(unitType) then return operation=="MOVE_TO" or operation=="ACTIVATE_GREAT_PERSON" end
  if unitType=="UNIT_TRADER" then return operation=="MAKE_TRADE_ROUTE" end
  if unitType == "UNIT_SETTLER" then return operation == "MOVE_TO" or operation == "FOUND_CITY" end
  if unitType == "UNIT_BUILDER" then
    return operation == "MOVE_TO" or operation == "BUILD_IMPROVEMENT" or operation == "REPAIR"
      or operation == "BUILD_IMPROVEMENT_ADJACENT"
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

-- Pure own-city stability decision; no engine calls or cached permission.
BaiqiPolicy.ExpansionStability=(function()
local BaiqiExpansionStability = {}

local function Plain(v)return type(v)=="table"and getmetatable(v)==nil end

local function IsFiniteNumber(n)
  return type(n) == "number" and n == n and n ~= math.huge and n ~= -math.huge
end

local function IsIntegerInRange(n, min, max)
  if not IsFiniteNumber(n) then return false end
  if n ~= math.floor(n) then return false end
  return n >= min and n <= max
end

function BaiqiExpansionStability.Evaluate(snapshot)
  if not Plain(snapshot) then return "UNKNOWN", "invalid_state", nil end

  local rules = snapshot.loyaltyRules
  if rules == false then
    return "CLEAR", "no_loyalty_rules", nil
  end

  if rules ~= true then
    return "UNKNOWN", "invalid_state", nil
  end

  local cities = snapshot.cities
  if not Plain(cities) then return "UNKNOWN", "invalid_state", nil end

  -- Validate structure: dense array, no metatable, no extra keys, max 128
  local count = 0
  for k, v in pairs(cities) do
    if type(k) ~= "number" or k ~= math.floor(k) or k < 1 or k > 128 then
      return "UNKNOWN", "invalid_state", nil
    end
    count = count + 1
  end

  if count > 128 then return "UNKNOWN", "invalid_state", nil end

  -- Check for holes and ensure 1..count are all present
  for i = 1, count do
    if cities[i] == nil then return "UNKNOWN", "invalid_state", nil end
  end

  -- Validate each city DTO
  local seenIDs = {}
  local bestUnstable = nil
  local bestID = nil
  local bestLoyalty = nil
  local bestRate = nil

  for i = 1, count do
    local city = cities[i]
    if not Plain(city) then return "UNKNOWN", "invalid_state", nil end

    -- Check for extra keys in city table (strict DTO)
    local keyCount = 0
    for k, _ in pairs(city) do
      keyCount = keyCount + 1
      if k ~= "id" and k ~= "loyalty" and k ~= "rate" then
        return "UNKNOWN", "invalid_state", nil
      end
    end
    if keyCount ~= 3 then return "UNKNOWN", "invalid_state", nil end

    local id = city.id
    local loyalty = city.loyalty
    local rate = city.rate

    if not IsIntegerInRange(id, 0, 2147483647) then return "UNKNOWN", "invalid_state", nil end
    if not IsFiniteNumber(loyalty) or loyalty < 0 or loyalty > 100 then return "UNKNOWN", "invalid_state", nil end
    if not IsFiniteNumber(rate) or rate < -1000 or rate > 1000 then return "UNKNOWN", "invalid_state", nil end

    if seenIDs[id] then return "UNKNOWN", "invalid_state", nil end
    seenIDs[id] = true

    -- Determine instability: rate < 0 OR loyalty < 50
    if rate < 0 or loyalty < 50 then
      -- Priority: lower loyalty, then lower rate, then lower id
      if bestUnstable == nil then
        bestUnstable = true
        bestID = id
        bestLoyalty = loyalty
        bestRate = rate
      else
        if loyalty < bestLoyalty then
          bestID = id; bestLoyalty = loyalty; bestRate = rate
        elseif loyalty == bestLoyalty then
          if rate < bestRate then
            bestID = id; bestLoyalty = loyalty; bestRate = rate
          elseif rate == bestRate then
            if id < bestID then
              bestID = id; bestLoyalty = loyalty; bestRate = rate
            end
          end
        end
      end
    end
  end

  if bestUnstable then
    return "HOLD", "unstable_owned_city", bestID
  end

  if count == 0 then
    return "CLEAR", "first_city", nil
  end

  return "CLEAR", "stable", nil
end

return BaiqiExpansionStability.Evaluate
end)()
