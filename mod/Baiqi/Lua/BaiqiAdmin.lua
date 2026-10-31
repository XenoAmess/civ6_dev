-- Uses the same legal, normal-cost requests as the shipped research/government UI.
-- This module belongs only to the unguarded, invisible executor context.
include("BaiqiConfig")
BaiqiAdmin={}
local attempted,turn={},-1
local techPriority={TECH_MINING=90,TECH_ANIMAL_HUSBANDRY=85,TECH_ARCHERY=80,TECH_BRONZE_WORKING=75,TECH_WHEEL=70}
local civicPriority={CIVIC_CODE_OF_LAWS=100,CIVIC_CRAFTSMANSHIP=90,CIVIC_FOREIGN_TRADE=85,CIVIC_EARLY_EMPIRE=80,CIVIC_STATE_WORKFORCE=75,CIVIC_POLITICAL_PHILOSOPHY=70}
local policyPriority={POLICY_URBAN_PLANNING=100,POLICY_DISCIPLINE=95,POLICY_AGOGE=90,POLICY_COLONIZATION=85,POLICY_ILKUM=80}
local function Once(key,action)
  if attempted[key] then return false end
  attempted[key]=true
  action()
  print("BAIQI|admin_request|turn="..turn.."|key="..key)
  return true
end
local function Choose(rows,can,cost,priorities,typeKey)
  local choices={}
  for row in rows() do
    if can(row) then choices[#choices+1]=row end
  end
  table.sort(choices,function(a,b)
    local x,y=priorities[a[typeKey]] or 0,priorities[b[typeKey]] or 0
    if x~=y then return x>y end
    x,y=cost(a),cost(b)
    if x~=y then return x<y end
    return a.Index<b.Index
  end)
  return choices[1]
end
function BaiqiAdmin.Run()
  local pid=Game.GetLocalPlayer()
  if pid==nil or pid<0 or GameConfiguration.IsAnyMultiplayer()
    or (GameConfiguration.IsHotseat and GameConfiguration.IsHotseat()) then return end
  local player,config=Players[pid],PlayerConfigurations[pid]
  if not player or not config or config:GetLeaderTypeName()~=BaiqiConfig.leader
    or not config:IsHuman() or not player:IsTurnActive() or not Game.IsAllowStrategicCommands(pid) then return end
  local current=Game.GetCurrentGameTurn()
  if current~=turn then turn=current;attempted={} end
  local techs,culture=player:GetTechs(),player:GetCulture()
  if techs:GetResearchingTech()==-1 then
    local row=Choose(GameInfo.Technologies,function(r) return not techs:HasTech(r.Index) and techs:CanResearch(r.Index) end,
      function(r) return techs:GetResearchCost(r.Index) end,techPriority,"TechnologyType")
    if row then
      local path=techs:GetResearchPath(row.Hash)
      if type(path)=="table" and next(path)~=nil then
        Once("tech:"..row.Index,function() UI.RequestPlayerOperation(pid,PlayerOperations.RESEARCH,
          {[PlayerOperations.PARAM_TECH_TYPE]=path,[PlayerOperations.PARAM_INSERT_MODE]=PlayerOperations.VALUE_EXCLUSIVE}) end)
      end
    end
  end
  if culture:GetProgressingCivic()==-1 then
    local row=Choose(GameInfo.Civics,function(r) return not culture:HasCivic(r.Index) and culture:CanProgress(r.Index) end,
      function(r) return culture:GetCultureCost(r.Index) end,civicPriority,"CivicType")
    if row then
      local path=culture:GetCivicPath(row.Hash)
      if type(path)=="table" and next(path)~=nil then
        Once("civic:"..row.Index,function() UI.RequestPlayerOperation(pid,PlayerOperations.PROGRESS_CIVIC,
          {[PlayerOperations.PARAM_CIVIC_TYPE]=path,[PlayerOperations.PARAM_INSERT_MODE]=PlayerOperations.VALUE_EXCLUSIVE}) end)
      end
    end
  end
  -- Fill open slots only in the game's free policy window. Never pay to unlock it.
  if culture:PolicyChangeMade() or not (culture:CivicCompletedThisTurn() or culture:GetNumPolicySlotsOpen()>0) then return end
  local used,add,clear={}, {}, {}
  for i=0,culture:GetNumPolicySlots()-1 do
    clear[#clear+1]=i
    local index=culture:GetSlotPolicy(i)
    if index~=nil and index>=0 then
      local row=GameInfo.Policies[index]
      if row==nil then return end
      used[index]=true;add[i]=row.Hash
    end
  end
  local filled=false
  for i=0,culture:GetNumPolicySlots()-1 do
    if culture:GetSlotPolicy(i)==-1 then
      local slot=GameInfo.GovernmentSlots[culture:GetSlotType(i)]
      if slot then
        local best=Choose(GameInfo.Policies,function(r)
          return not used[r.Index] and culture:IsPolicyUnlocked(r.Hash) and not culture:IsPolicyObsolete(r.Hash)
            and (slot.GovernmentSlotType=="SLOT_WILDCARD" or r.GovernmentSlotType==slot.GovernmentSlotType)
        end,function() return 0 end,policyPriority,"PolicyType")
        if best then used[best.Index]=true;add[i]=best.Hash;filled=true end
      end
    end
  end
  -- The native confirmation submits every slot in clearList, including empty
  -- slots, and the complete final hash map. An empty clearList is a no-op in
  -- the actual engine even when add contains legal policies.
  if filled then Once("policies",function() culture:RequestPolicyChanges(clear,add) end) end
end
