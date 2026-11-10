-- Uses the same legal, normal-cost requests as the shipped research/government UI.
-- This module belongs only to the unguarded, invisible executor context.
include("BaiqiConfig")
include("BaiqiGovernorLoyalty")
include("BaiqiFoodFocusRunner")
include("BaiqiFoodTileRescueRunner")
BaiqiAdmin={}
local attempted,turn={},-1
local techPriority={TECH_MINING=90,TECH_ANIMAL_HUSBANDRY=85,TECH_ARCHERY=80,TECH_BRONZE_WORKING=75,TECH_WHEEL=70}
local civicPriority={CIVIC_CODE_OF_LAWS=100,CIVIC_CRAFTSMANSHIP=90,CIVIC_FOREIGN_TRADE=85,CIVIC_EARLY_EMPIRE=80,CIVIC_STATE_WORKFORCE=75,CIVIC_POLITICAL_PHILOSOPHY=70}
local policyPriority={POLICY_URBAN_PLANNING=100,POLICY_DISCIPLINE=95,POLICY_AGOGE=90,POLICY_COLONIZATION=85,POLICY_ILKUM=80}
local governorPriority={GOVERNOR_THE_RESOURCE_MANAGER=100,GOVERNOR_THE_BUILDER=90,
  GOVERNOR_THE_EDUCATOR=80,GOVERNOR_THE_DEFENDER=70}
local pantheonPriority={BELIEF_GOD_OF_THE_FORGE=100,BELIEF_CITY_PATRON_GODDESS=90}
local governmentSlots
local pendingGreatPerson
local pendingReligion
local pendingGovernorRescue
local religionBeliefPriority={BELIEF_WORK_ETHIC=100,BELIEF_FEED_THE_WORLD=95,
  BELIEF_TITHE=90,BELIEF_DEFENDER_OF_FAITH=85}
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
local function Pantheon(pid,player)
  if not player.GetReligion or not GameInfo.Beliefs then return end
  local religion=player:GetReligion()
  if not religion or religion:GetPantheon()>=0 or not religion:CanCreatePantheon() then return end
  local world=Game.GetReligion()
  local row=Choose(GameInfo.Beliefs,function(r)
    return r.BeliefClassType=="BELIEF_CLASS_PANTHEON"
      and not world:IsInSomePantheon(r.Index) and not world:IsInSomeReligion(r.Index)
  end,function() return 0 end,pantheonPriority,"BeliefType")
  if row then
    -- The engine charges normal faith. A request is not proof of founding.
    Once("pantheon",function() UI.RequestPlayerOperation(pid,PlayerOperations.FOUND_PANTHEON,{
      [PlayerOperations.PARAM_BELIEF_TYPE]=row.Hash,
      [PlayerOperations.PARAM_INSERT_MODE]=PlayerOperations.VALUE_EXCLUSIVE}) end)
  end
end
local function ReligionState(pid,player)
  local religion=player.GetReligion and player:GetReligion()
  if not religion or not religion.GetReligionTypeCreated or not religion.GetNumBeliefsEarned or not religion.GetPantheon
    or not Game.GetReligion then return nil end
  local world=Game.GetReligion()
  if not world or not world.GetReligions then return nil end
  local state={id=religion:GetReligionTypeCreated(),earned=religion:GetNumBeliefsEarned(),pantheon=religion:GetPantheon(),beliefs={},classes={},count=0}
  if type(state.id)~="number" or state.id<-1 or state.id%1~=0 or type(state.earned)~="number" or state.earned<0 or state.earned%1~=0
    or type(state.pantheon)~="number" or state.pantheon<-1 or state.pantheon%1~=0 then return nil end
  if state.id>=0 then
    local found=false
    local list=world:GetReligions()
    if type(list)~="table" then return nil end
    for _,entry in ipairs(list) do
      if entry.Founder==pid and entry.Religion==state.id then
        if type(entry.Beliefs)~="table" then return nil end
        for _,index in pairs(entry.Beliefs) do
          local row=GameInfo.Beliefs[index]
          if not row or state.beliefs[index] then return nil end
          state.beliefs[index]=true;state.classes[row.BeliefClassType]=true;state.count=state.count+1
        end
        found=true;break
      end
    end
    if not found then return nil end
  end
  local indices={};for index in pairs(state.beliefs) do indices[#indices+1]=index end;table.sort(indices)
  state.stamp=state.id..":"..state.earned..":"..table.concat(indices,",")
  return state,world
end

local function ReligionPlayer(pid)
  local player,config=Players[pid],PlayerConfigurations[pid]
  if Game.GetLocalPlayer()==pid and player and config and config:IsHuman()==true
    and config:GetLeaderTypeName()==BaiqiConfig.leader and player:IsTurnActive()==true
    and Game.IsAllowStrategicCommands(pid)==true and GameConfiguration.IsAnyMultiplayer()==false
    and (not GameConfiguration.IsHotseat or GameConfiguration.IsHotseat()==false)
    and Game.GetCurrentGameTurn()==turn then return player end
end

local function Religion(pid,player)
  if not GameInfo.Religions or not GameInfo.Beliefs then return end
  local state,world=ReligionState(pid,player)
  if not state then return end
  if pendingReligion then
    if pendingReligion.player~=pid then return end
    local observed=(pendingReligion.kind=="found" and state.id==pendingReligion.index)
      or (pendingReligion.kind=="belief" and state.beliefs[pendingReligion.index])
    if not observed then
      if not pendingReligion.waitLogged then
        print("BAIQI|religion_request_pending|turn="..turn.."|kind="..pendingReligion.kind.."|index="..pendingReligion.index)
        pendingReligion.waitLogged=true
      end
      return
    end
    print("BAIQI|admin_observed|turn="..turn.."|kind=religion_"..pendingReligion.kind.."|index="..pendingReligion.index.."|beliefs="..state.count)
    pendingReligion=nil
  end
  if state.pantheon<0 or state.earned<=state.count then return end
  local kind,row,operation,parameters
  if state.id<0 then
    if not world.HasBeenFounded then return end
    local choices={}
    for candidate in GameInfo.Religions() do
      if candidate.Pantheon==false and world:HasBeenFounded(candidate.Index)==false then choices[#choices+1]=candidate end
    end
    table.sort(choices,function(a,b)
      if a.RequiresCustomName~=b.RequiresCustomName then return not a.RequiresCustomName end
      return a.Index<b.Index
    end)
    row=choices[1];if not row then return end
    kind,operation="found",PlayerOperations.FOUND_RELIGION
    parameters={[PlayerOperations.PARAM_RELIGION_TYPE]=row.Hash,[PlayerOperations.PARAM_INSERT_MODE]=PlayerOperations.VALUE_EXCLUSIVE}
    if row.RequiresCustomName then parameters[PlayerOperations.PARAM_RELIGION_CUSTOM_NAME]="白绮之道" end
  else
    if not world.IsTooManyForReligion then return end
    row=Choose(GameInfo.Beliefs,function(candidate)
      return candidate.BeliefClassType~="BELIEF_CLASS_PANTHEON" and not state.classes[candidate.BeliefClassType]
        and (state.classes.BELIEF_CLASS_FOLLOWER or candidate.BeliefClassType=="BELIEF_CLASS_FOLLOWER")
        and world:IsInSomePantheon(candidate.Index)==false and world:IsInSomeReligion(candidate.Index)==false
        and world:IsTooManyForReligion(candidate.Index,state.id)==false
    end,function() return 0 end,religionBeliefPriority,"BeliefType")
    if not row then return end
    kind,operation="belief",PlayerOperations.ADD_BELIEF
    parameters={[PlayerOperations.PARAM_BELIEF_TYPE]=row.Hash,[PlayerOperations.PARAM_INSERT_MODE]=PlayerOperations.VALUE_EXCLUSIVE}
  end
  if operation==nil then return end
  -- Selection and actual earned capacity are re-read at the write boundary.
  local actualPlayer=ReligionPlayer(pid)
  if not actualPlayer then return end
  local fresh,freshWorld=ReligionState(pid,actualPlayer)
  if not fresh or fresh.stamp~=state.stamp then return end
  if kind=="found" then
    if freshWorld:HasBeenFounded(row.Index)~=false then return end
  elseif freshWorld:IsInSomePantheon(row.Index)~=false or freshWorld:IsInSomeReligion(row.Index)~=false
    or freshWorld:IsTooManyForReligion(row.Index,fresh.id)~=false then return end
  if not ReligionPlayer(pid) then return end
  Once("religion:"..kind..":"..row.Index..":"..fresh.stamp,function()
    pendingReligion={player=pid,kind=kind,index=row.Index}
    UI.RequestPlayerOperation(pid,operation,parameters)
  end)
end

local function Assignable(row)
  if GameInfo.GovernorsCannotAssign then
    for restriction in GameInfo.GovernorsCannotAssign() do
      if restriction.GovernorType==row.GovernorType and restriction.CannotAssign then return false end
    end
  end
  return true
end
local function LoyaltyCity(city,pid,governors)
  assert(city:GetOwner()==pid)
  local identity=assert(city:GetCulturalIdentity())
  local assigned=governors:GetAssignedGovernor(city)
  local pressure,count,keys,entries,total,found=0,0,0,0,0,false
  local rows=identity:GetIdentitySourcesBreakdown()
  assert(type(rows)=="table")
  for key in pairs(rows) do
    assert(type(key)=="number" and key%1==0 and key>=1 and key<=64)
    keys=keys+1
  end
  for _,source in ipairs(rows) do
    count=count+1;assert(count<=64 and type(source)=="table")
    for kind,value in pairs(source) do
      entries=entries+1;assert(entries<=128)
      assert(type(kind)=="string" and type(value)=="number" and value==value and math.abs(value)<=1000)
      total=total+value
      if kind=="Governors" then pressure=pressure+value;found=true end
    end
  end
  local rate=identity:GetLoyaltyPerTurn()
  assert(count==keys and math.abs(total-rate)<=1/256)
  assert((not assigned and pressure==0) or (assigned and found and pressure>0))
  return {id=city:GetID(),population=city:GetPopulation(),loyalty=identity:GetLoyalty(),
    rate=rate,assigned=assigned and assigned:GetType(),removalPressure=pressure}
end
local function GovernorLoyaltySnapshot(pid,player,governors)
  local ok,snapshot=pcall(function()
    local result={cities={},governors={}}
    local own=player:GetCities();local expected=own:GetCount()
    assert(type(expected)=="number" and expected>=0 and expected<=128 and expected%1==0)
    for _,city in own:Members() do
      assert(#result.cities<128)
      result.cities[#result.cities+1]=LoyaltyCity(city,pid,governors)
    end
    assert(#result.cities==expected and own:GetCount()==expected)
    local needed=false
    for _,c in ipairs(result.cities) do
      if c.assigned==nil and type(c.rate)=="number" and c.rate<0
        and type(c.loyalty)=="number" then needed=true end
    end
    if not needed then return nil end
    local _,list=governors:GetGovernorList();assert(type(list)=="table" and #list<=32)
    for _,governor in ipairs(list) do
      assert(#result.governors<32)
      local row=assert(GameInfo.Governors[governor:GetType()])
      local assigned=governor:GetAssignedCity()
      -- Never recall a governor from a foreign city or city-state.
      assert(not assigned or assigned:GetOwner()==pid)
      local item={type=row.Index,city=assigned and assigned:GetID(),
        neutralized=governor:GetNeutralizedTurns(),pressure=governor:GetIdentityPressure(),assignable={}}
      for _,city in ipairs(result.cities) do
        local native=assert(own:FindID(city.id));assert(native:GetOwner()==pid)
        local can=governors:CanAssignGovernor(row.Hash,native,true)
        assert(type(can)=="boolean")
        item.assignable[city.id]=Assignable(row) and can
      end
      result.governors[#result.governors+1]=item
    end
    return result
  end)
  if ok then return snapshot end
end
local function GovernorRescue(pid,player,governors)
  if pendingGovernorRescue then
    local p=pendingGovernorRescue
    local ok,observed=pcall(function()
      if p.player~=pid then return false end
      local city=player:GetCities():FindID(p.target)
      if not city or city:GetOwner()~=pid then return false end
      local g=governors:GetAssignedGovernor(city)
      local source=g and g:GetAssignedCity()
      return g~=nil and g:GetType()==p.governor and source~=nil
        and source:GetOwner()==pid and source:GetID()==p.target
    end)
    if not ok or observed~=true then return true end
    print("BAIQI|governor_rescue_observed|turn="..turn.."|governor="..p.governor.."|target="..p.target)
    pendingGovernorRescue=nil
  end
  if type(BaiqiGovernorLoyalty)~="table" or type(BaiqiGovernorLoyalty.Plan)~="function" then return false end
  local plan=BaiqiGovernorLoyalty.Plan(GovernorLoyaltySnapshot(pid,player,governors))
  if not plan then return false end
  local fresh=BaiqiGovernorLoyalty.Plan(GovernorLoyaltySnapshot(pid,player,governors))
  if not fresh or fresh.governor~=plan.governor or fresh.source~=plan.source or fresh.target~=plan.target then return true end
  local ok,ready=pcall(function()
    local city=assert(player:GetCities():FindID(plan.target))
    local row=assert(GameInfo.Governors[plan.governor])
    if not Assignable(row) or governors:CanAssignGovernor(row.Hash,city,true)~=true then return false end
    -- Read critical native values after the permission call as well.
    local target=LoyaltyCity(city,pid,governors)
    local _,list=governors:GetGovernorList();local selected
    for _,g in ipairs(list) do if g:GetType()==plan.governor then selected=g end end
    if not selected then return false end
    local assigned=selected:GetAssignedCity()
    local checkCities={target}
    if plan.source~=nil then
      if not assigned or assigned:GetOwner()~=pid or assigned:GetID()~=plan.source then return false end
      local donor=LoyaltyCity(assigned,pid,governors)
      checkCities[#checkCities+1]=donor
    elseif assigned~=nil then return false end
    local checked=BaiqiGovernorLoyalty.Plan({cities=checkCities,governors={{type=selected:GetType(),
      city=assigned and assigned:GetID(),neutralized=selected:GetNeutralizedTurns(),
      pressure=selected:GetIdentityPressure(),assignable={[plan.target]=true}}}})
    if not checked or checked.governor~=plan.governor or checked.source~=plan.source or checked.target~=plan.target then return false end
    local config=PlayerConfigurations[pid]
    return Game.GetLocalPlayer()==pid and Game.GetCurrentGameTurn()==turn and player:IsTurnActive()
      and config:GetLeaderTypeName()==BaiqiConfig.leader and config:IsHuman()
      and Game.IsAllowStrategicCommands(pid) and not GameConfiguration.IsAnyMultiplayer()
      and not (GameConfiguration.IsHotseat and GameConfiguration.IsHotseat())
  end)
  if not ok or ready~=true then return true end
  Once("governor-assign:"..plan.governor,function()
    pendingGovernorRescue={player=pid,governor=plan.governor,target=plan.target}
    print("BAIQI|governor_rescue_request|turn="..turn.."|governor="..plan.governor.."|target="..plan.target)
    -- A false, void or throwing request is still uncertain; no in-session replay.
    pcall(UI.RequestPlayerOperation,pid,PlayerOperations.ASSIGN_GOVERNOR,{
      [PlayerOperations.PARAM_GOVERNOR_TYPE]=plan.governor,
      [PlayerOperations.PARAM_PLAYER_ONE]=pid,[PlayerOperations.PARAM_CITY_DEST]=plan.target})
  end)
  return true
end
local function Governors(pid,player)
  if not player.GetGovernors or not GameInfo.Governors then return end
  local governors=player:GetGovernors()
  if not governors then return end
  if GovernorRescue(pid,player,governors) then return end
  local cities={}
  for _,city in player:GetCities():Members() do
    if city:GetOwner()==pid and not governors:GetAssignedGovernor(city) then cities[#cities+1]=city end
  end
  table.sort(cities,function(a,b)
    if a:GetPopulation()~=b:GetPopulation() then return a:GetPopulation()>b:GetPopulation() end
    return a:GetID()<b:GetID()
  end)
  local _,list=governors:GetGovernorList()
  table.sort(list,function(a,b) return a:GetType()<b:GetType() end)
  -- Wait for each request's actual state before making another title decision.
  for _,governor in ipairs(list) do
    local row=GameInfo.Governors[governor:GetType()]
    if row and Assignable(row) and not governor:GetAssignedCity() and governor:GetNeutralizedTurns()==0 then
      for _,city in ipairs(cities) do
        if governors:CanAssignGovernor(row.Hash,city,true) then
          Once("governor-assign:"..row.Index,function()
            UI.RequestPlayerOperation(pid,PlayerOperations.ASSIGN_GOVERNOR,{
              [PlayerOperations.PARAM_GOVERNOR_TYPE]=row.Index,
              [PlayerOperations.PARAM_PLAYER_ONE]=pid,[PlayerOperations.PARAM_CITY_DEST]=city:GetID()})
          end)
          return
        end
      end
    end
  end
  local spent=governors:GetGovernorPointsSpent()
  if governors:GetGovernorPoints()<=spent then return end
  local titleKey="governor-title:"..spent
  if #cities>0 and governors:CanAppoint() then
    local row=Choose(GameInfo.Governors,function(r)
      -- CanAssignGovernor is false before appointment in the native engine.
      return Assignable(r) and not governors:HasGovernor(r.Hash) and governors:CanEverAppointGovernor(r.Hash)
    end,function() return 0 end,governorPriority,"GovernorType")
    if row then
      Once(titleKey,function() UI.RequestPlayerOperation(pid,PlayerOperations.APPOINT_GOVERNOR,
        {[PlayerOperations.PARAM_GOVERNOR_TYPE]=row.Index}) end)
      return
    end
  end
  for _,governor in ipairs(list) do
    local row=GameInfo.Governors[governor:GetType()]
    if row and Assignable(row) and governors:CanPromoteGovernor(row.Hash) then
      for entry in GameInfo.GovernorPromotionSets() do
        local promotion=GameInfo.GovernorPromotions[entry.GovernorPromotion]
        if entry.GovernorType==row.GovernorType and promotion and not promotion.BaseAbility
          and not governor:HasPromotion(promotion.Hash) and governors:CanEarnPromotion(row.Hash,promotion.Hash) then
          Once(titleKey,function() UI.RequestPlayerOperation(pid,PlayerOperations.PROMOTE_GOVERNOR,{
            [PlayerOperations.PARAM_GOVERNOR_TYPE]=row.Index,
            [PlayerOperations.PARAM_GOVERNOR_PROMOTION_TYPE]=promotion.Index}) end)
          return
        end
      end
    end
  end
end
local function Dedication(pid)
  if not Game.GetEras or not EndTurnBlockingTypes or not NotificationManager
    or not EndTurnBlockingTypes.ENDTURN_BLOCKING_COMMEMORATION_AVAILABLE then return end
  if NotificationManager.GetFirstEndTurnBlocking(pid)~=EndTurnBlockingTypes.ENDTURN_BLOCKING_COMMEMORATION_AVAILABLE then return end
  local eras=Game.GetEras()
  if not eras or eras:GetPlayerNumAllowedCommemorations(pid)<=0 then return end
  local active,choices={},{}
  local actual=eras:GetPlayerActiveCommemorations(pid)
  for _,index in ipairs(actual) do active[index]=true end
  for _,index in ipairs(eras:GetPlayerCommemorateChoices(pid)) do
    local row=GameInfo.CommemorationTypes[index]
    if row and not active[index] then choices[#choices+1]=row end
  end
  table.sort(choices,function(a,b)
    local x=a.CommemorationType=="COMMEMORATION_INFRASTRUCTURE" and 1 or 0
    local y=b.CommemorationType=="COMMEMORATION_INFRASTRUCTURE" and 1 or 0
    if x~=y then return x>y end
    return a.Index<b.Index
  end)
  if choices[1] then
    -- One request per observed active-count state; the engine decides when all
    -- normal or heroic choices are complete. Never infer total vs remaining.
    Once("dedication:"..#actual,function() UI.RequestPlayerOperation(pid,PlayerOperations.COMMEMORATE,
      {[PlayerOperations.PARAM_COMMEMORATION_TYPE]=choices[1].Index}) end)
  end
end
local function GreatPeople(pid)
  if not Game.GetGreatPeople then return end
  local people=Game.GetGreatPeople()
  if not people then return end
  if pendingGreatPerson~=nil then
    if people:CanRecruitPerson(pid,pendingGreatPerson) then return end
    pendingGreatPerson=nil
  end
  for _,entry in ipairs(people:GetTimeline()) do
    local index=entry.Individual
    if index~=nil and people:CanRecruitPerson(pid,index) then
      Once("great-person:"..index,function()
        pendingGreatPerson=index
        UI.RequestPlayerOperation(pid,PlayerOperations.RECRUIT_GREAT_PERSON,
          {[PlayerOperations.PARAM_GREAT_PERSON_INDIVIDUAL_TYPE]=index})
      end)
      return
    end
  end
end
local function Government(pid,culture)
  if not culture.CanChangeGovernmentAtAll or not GameInfo.Governments or not GameInfo.Government_SlotCounts then return false end
  local currentIndex=culture:GetCurrentGovernment()
  local current=GameInfo.Governments[currentIndex]
  if not governmentSlots then
    governmentSlots={}
    for row in GameInfo.Governments() do governmentSlots[row.GovernmentType]={count=0,score=0} end
    for row in GameInfo.Government_SlotCounts() do
      local item=governmentSlots[row.GovernmentType]
      if item then
        item.count=item.count+row.NumSlots
        local weight=row.GovernmentSlotType=="SLOT_MILITARY" and 3
          or (row.GovernmentSlotType=="SLOT_WILDCARD" and 2 or 1)
        item.score=item.score+row.NumSlots*weight
      end
    end
  end
  local currentSlots=current and governmentSlots[current.GovernmentType]
  local best,bestSlots
  if culture:CanChangeGovernmentAtAll() and not culture:GovernmentChangeMade()
    and (currentIndex==-1 or culture:CivicCompletedThisTurn()) then
    for row in GameInfo.Governments() do
      local slots=governmentSlots[row.GovernmentType]
      if slots and slots.count>(currentSlots and currentSlots.count or 0)
        and culture:IsGovernmentUnlocked(row.Hash) and culture:GetAnarchyTurns(row.Index)==0 then
        if not best or slots.count>bestSlots.count
          or (slots.count==bestSlots.count and (slots.score>bestSlots.score
            or (slots.score==bestSlots.score and row.Index<best.Index))) then best,bestSlots=row,slots end
      end
    end
  end
  if best then
    Once("government",function() culture:RequestChangeGovernment(best.Hash) end)
    return true -- Wait for the actual new government before filling its policy slots.
  end
  if NotificationManager and EndTurnBlockingTypes
    and EndTurnBlockingTypes.ENDTURN_BLOCKING_CONSIDER_GOVERNMENT_CHANGE
    and NotificationManager.GetFirstEndTurnBlocking(pid)==EndTurnBlockingTypes.ENDTURN_BLOCKING_CONSIDER_GOVERNMENT_CHANGE then
    -- An evaluated decision to retain the current government, not a paid unlock.
    Once("government-retain",function() culture:SetGovernmentChangeConsidered(true) end)
  end
  return false
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
  if type(BaiqiFoodFocusRunner)=="table" and type(BaiqiFoodFocusRunner.Run)=="function" then
    BaiqiFoodFocusRunner.Run({Game=Game,GameConfiguration=GameConfiguration,UI=UI,
      Players=Players,PlayerConfigurations=PlayerConfigurations,CityManager=CityManager,
      CityCommandTypes=CityCommandTypes,YieldTypes=YieldTypes,leader=BaiqiConfig.leader},pid)
  end
  if type(BaiqiFoodTileRescueRunner)=="table" and type(BaiqiFoodTileRescueRunner.Run)=="function" then
    BaiqiFoodTileRescueRunner.Run({Game=Game,GameConfiguration=GameConfiguration,UI=UI,
      Players=Players,PlayerConfigurations=PlayerConfigurations,CityManager=CityManager,
      CityCommandTypes=CityCommandTypes,CityCommandResults=CityCommandResults,YieldTypes=YieldTypes,
      Map=Map,PlayersVisibility=PlayersVisibility,leader=BaiqiConfig.leader},pid)
  end
  Pantheon(pid,player)
  Religion(pid,player)
  Governors(pid,player)
  Dedication(pid)
  GreatPeople(pid)
  if Government(pid,culture) then return end
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
