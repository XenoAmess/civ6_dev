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
  elseif role == "trader" then
    return s.cities>=2 and number(s.traders) and number(s.queuedTraders) and number(s.tradeCapacity)
      and s.traders+s.queuedTraders<s.tradeCapacity
  elseif role == "archaeologist" then
    return s.archaeologistDemand==true
  elseif role == "military" then
    return number(s.army) and number(s.queuedArmy)
      and s.army + s.queuedArmy < math.max(2, s.cities * c.armyPerCity)
  end
  return false
end

function BaiqiPlanner.MilitaryRole(row)
  if row.PromotionClass=="PROMOTION_CLASS_RECON" then return "recon" end
  if row.Domain=="DOMAIN_SEA" then return "naval" end
  if row.Domain=="DOMAIN_AIR" then return "air" end
  if row.FormationClass=="FORMATION_CLASS_SUPPORT" then return "support" end
  if row.PromotionClass=="PROMOTION_CLASS_SIEGE" then return "siege" end
  if (row.RangedCombat or 0)>0 then return "ranged" end
  if (row.Combat or 0)>0 then return "frontline" end
end

-- Rank production only. Live, queued and unacknowledged commitments share one
-- role tally; no orders are issued to the resulting units.
function BaiqiPlanner.MilitaryScore(row, s, c)
  local role=BaiqiPlanner.MilitaryRole(row)
  local counts=s.militaryRoles
  if not role or type(counts)~="table" or not number(s.cities) then return nil end
  for _,key in ipairs({"recon","frontline","ranged","siege","support","naval","air"}) do
    if not number(counts[key]) or counts[key]<0 then return nil end
  end
  local score
  if role=="recon" then
    if not number(c.reconCitiesPerUnit) or c.reconCitiesPerUnit<=0
      or counts.recon>=math.max(1,math.ceil(s.cities/c.reconCitiesPerUnit)) then return nil end
    score=50
  elseif role=="frontline" then score=counts.frontline<=counts.ranged and 66 or 64
  elseif role=="ranged" then score=counts.ranged<counts.frontline and 66 or 64
  elseif role=="siege" then score=62
  elseif role=="support" then score=61
  elseif role=="air" then score=61
  else score=60 end
  local strength=math.max(row.Combat or 0,row.RangedCombat or 0,row.Bombard or 0)
  return score+math.min(0.9,math.max(0,strength)/1000)
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
