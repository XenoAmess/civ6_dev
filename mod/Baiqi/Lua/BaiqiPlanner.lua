-- Pure decisions. Engine reads and actions live in BaiqiController.
BaiqiPlanner = {}

local function number(n) return BaiqiPolicy.Number(n) end

function BaiqiPlanner.Choose(city, candidates)
  if type(city) ~= "table" or city.paused ~= false or city.queueEmpty ~= true then return nil end
  local best, bestScore
  for _, candidate in ipairs(candidates or {}) do
    if candidate.legal == true and number(candidate.score) and number(candidate.index) then
      local score = candidate.score + (candidate.repair == true and 1000 or 0)
      if best == nil or score > bestScore or (score == bestScore and candidate.index < best.index) then
        best, bestScore = candidate, score
      end
    end
  end
  return best
end

function BaiqiPlanner.AllowRecruit(role, s, c)
  if type(s) ~= "table" or type(c) ~= "table" then return false end
  for _, key in ipairs({"gold", "netGold", "cities", "maintenance", "committedMaintenance"}) do
    if not number(s[key]) then return false end
  end
  if s.resourceAffordable ~= true or s.gold < c.goldReserve
    or s.netGold - s.committedMaintenance - s.maintenance < c.netGoldMin then return false end
  if role == "settler" then
    return number(s.cityPopulation) and s.cityPopulation >= c.settlerMinPop
      and number(s.settlers) and number(s.queuedSettlers) and number(s.reservedSettlers)
      and s.settlers + s.queuedSettlers + s.reservedSettlers < c.maxSettlers and s.hasSafeSite == true
  elseif role == "builder" then
    return number(s.builders) and number(s.queuedBuilders)
      and s.builders + s.queuedBuilders < math.max(1, math.ceil(s.cities * c.buildersPerCity))
  elseif role == "military" then
    return number(s.army) and number(s.queuedArmy)
      and s.army + s.queuedArmy < math.max(2, s.cities * c.armyPerCity)
  end
  return false
end

function BaiqiPlanner.Site(candidates, reservations, unitID)
  local best
  for _, p in ipairs(candidates or {}) do
    local reservation = reservations and reservations[p.index]
    if p.legal == true and p.revealed == true and p.safe == true and p.protected == false
      and (reservation == nil or reservation == unitID) and number(p.score) and number(p.index)
      and (best == nil or p.score > best.score or (p.score == best.score and p.index < best.index)) then best = p end
  end
  return best
end

-- Journal transitions are deliberately independent of payment and transfer APIs.
function BaiqiPlanner.Transition(stage, event, proof)
  if stage == "COMMITTED" or stage == "REJECTED" then return stage, "duplicate" end
  proof = proof or {}
  if stage == "QUOTED" and event == "SUBMIT" and proof.confirmed == true and proof.quoteValid == true then
    return "SUBMITTED", "submit"
  end
  if (stage == "SUBMITTED" or stage == "UNKNOWN") and proof.correlated == true then
    if event == "COMMIT" and proof.engineSuccess == true and proof.settled == true then return "COMMITTED", "settled" end
    if event == "REJECT" and proof.definitelyNotExecuted == true and proof.compensated == true then return "REJECTED", "failed" end
  end
  if stage == "SUBMITTED" and event == "UNKNOWN" then return "UNKNOWN", "freeze" end
  return stage, "blocked"
end
