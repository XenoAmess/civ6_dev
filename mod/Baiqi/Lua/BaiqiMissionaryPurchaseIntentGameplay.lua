include("BaiqiConfig")
include("BaiqiMissionaryPurchaseSnapshot")
include("BaiqiMissionaryPurchaseJournal")
include("BaiqiNaturalistPurchaseJournal")
include("BaiqiFaithPurchaseGuard")

-- The UI supplies the current engine quote. Core independently checks the
-- balance, city and stock; Core has no UI city:GetGold() price component.
local EVENT_MARKER="baiqi-missionary-purchase-events-v1"
local previousModule=BaiqiMissionaryPurchaseIntentGameplay
if previousModule~=nil then
  local ok,owned=pcall(function() return type(previousModule)=="table" and previousModule.marker==EVENT_MARKER end)
  if not ok or not owned then return previousModule end
end
BaiqiMissionaryPurchaseIntentGameplay={marker=EVENT_MARKER}
local MARKER="baiqi-missionary-purchase-v1"
local MAX=2147483647
local function Object(value)
  return type(value)=="table" or type(value)=="userdata"
end
local function Number(value)
  return type(value)=="number" and value==value and value>-math.huge and value<math.huge
end
local function Hash(value)
  return Number(value) and value>=-2147483648 and value<=4294967295 and value%1==0
end
local function Owner(pid,active)
  local j=BaiqiMissionaryPurchaseJournal
  if type(j)~="table" or not j.Integer(pid,MAX) or not Object(BaiqiConfig)
    or not Object(Game) or not Object(GameConfiguration)
    or Game.GetLocalPlayer()~=pid or GameConfiguration.IsAnyMultiplayer()
    or (GameConfiguration.IsHotseat and GameConfiguration.IsHotseat()) then return nil end
  local player=Players and Players[pid]
  local config=PlayerConfigurations and PlayerConfigurations[pid]
  if not Object(player) or not Object(config) or type(config.GetLeaderTypeName)~="function"
    or config:GetLeaderTypeName()~=BaiqiConfig.leader then return nil end
  local human
  if type(config.IsHuman)=="function" then human=config:IsHuman()
  elseif type(player.IsHuman)=="function" then human=player:IsHuman() end
  local key=BaiqiConfig.missionaryPurchaseIntentKey
  if human~=true or (active and (type(player.IsTurnActive)~="function" or player:IsTurnActive()~=true))
    or type(player.GetProperty)~="function" or type(player.SetProperty)~="function"
    or type(key)~="string" or #key==0 or #key>128 then return nil end
  return player,key
end
local function UnitHash()
  if not Object(GameInfo) or not Object(GameInfo.Units) then return nil end
  local row=GameInfo.Units.UNIT_MISSIONARY
  if Object(row) and row.UnitType=="UNIT_MISSIONARY" and row.MustPurchase==true and row.PurchaseYield=="YIELD_FAITH" and Hash(row.Hash) then return row.Hash end
end
local function Turn()
  local turn=Game.GetCurrentGameTurn()
  if BaiqiMissionaryPurchaseJournal.Integer(turn,MAX) then return turn end
end
local function Load(player,pid,key)
  -- A thrown read escapes into the bridge's protected call; it is never nil.
  local raw=player:GetProperty(key)
  if raw==nil then return BaiqiMissionaryPurchaseJournal.New(pid) end
  return BaiqiMissionaryPurchaseJournal.Clone(raw,pid)
end
local function Persist(player,pid,key,state)
  local j=BaiqiMissionaryPurchaseJournal
  local value=j.Clone(state,pid)
  if not value then return false end
  player:SetProperty(key,value)
  return j.Equal(state,player:GetProperty(key),pid)
end
local function BirthSiteMatches(player,pid,op,unit)
  if unit.x==op.x and unit.y==op.y then return true end
  local ok,result=pcall(function()
    local j=BaiqiMissionaryPurchaseJournal
    local holy=GameInfo.Districts.DISTRICT_HOLY_SITE
    if not Object(holy) or holy.DistrictType~="DISTRICT_HOLY_SITE" or not j.Integer(holy.Index,MAX) then return false end
    local city=player:GetCities():FindID(op.cityID)
    if not Object(city) or city:GetID()~=op.cityID or city:GetOwner()~=pid
      or city:GetX()~=op.x or city:GetY()~=op.y then return false end
    -- Core's city district collection has GetDistrict, but no Members method.
    local district=city:GetDistricts():GetDistrict(holy.Index)
    if not Object(district) then return false end
    local id=district:GetID()
    if not j.Integer(id,MAX) or district:GetOwner()~=pid or district:GetType()~=holy.Index
      or district:GetX()~=unit.x or district:GetY()~=unit.y
      or district:IsComplete()~=true or district:IsPillaged()~=false then return false end
    local ownerCity=district:GetCity()
    if not Object(ownerCity) or ownerCity:GetID()~=op.cityID or ownerCity:GetOwner()~=pid
      or ownerCity:GetX()~=op.x or ownerCity:GetY()~=op.y then return false end
    local plot=Map.GetPlot(unit.x,unit.y)
    return Object(plot) and plot:GetOwner()==pid and plot:GetDistrictType()==holy.Index
      and plot:GetDistrictID()==id
  end)
  return ok and result==true
end
local function ReceiptUnit(player,pid,op,snap)
  local j=BaiqiMissionaryPurchaseJournal
  if not snap or snap.cityID~=op.cityID or snap.owner~=pid or snap.x~=op.x or snap.y~=op.y
    or snap.religionIndex~=op.religionIndex or snap.majorityReligion~=op.religionIndex
    or op.faithBefore-snap.faithBalance~=op.cost then return nil end
  local count,unit=0,nil
  for _,v in ipairs(snap.missionaries) do
    if v.religionIndex==op.religionIndex and v.charges>0 then count=count+1;unit=v end
  end
  if count~=1 or not unit or unit.unitType~="UNIT_MISSIONARY" or not j.Integer(unit.unitID,MAX)
    or unit.formation~=1 or not BirthSiteMatches(player,pid,op,unit) then return nil end
  for _,prior in ipairs(op.baselineUnitIDs) do if prior==unit.unitID then return nil end end
  return unit
end
local function FreshReceipt(player,pid,key,state,op,first)
  local current,currentKey=Owner(pid,false)
  if current~=player or currentKey~=key or Turn()~=op.turn or UnitHash()~=op.unitHash then return nil end
  local snap=BaiqiMissionaryPurchaseSnapshot.Read(player,pid,op.cityID)
  local unit=ReceiptUnit(player,pid,op,snap)
  if not unit then return nil end
  for _,k in ipairs({"unitID","unitType","religionIndex","charges","x","y","moves","formation"}) do
    if unit[k]~=first[k] then return nil end
  end
  if not BaiqiMissionaryPurchaseJournal.Equal(state,Load(player,pid,key),pid) then return nil end
  local live=player:GetUnits():FindID(unit.unitID)
  local city=player:GetCities():FindID(op.cityID)
  if not Object(live) or not Object(city) or not BirthSiteMatches(player,pid,op,unit) then return nil end
  local pr=player:GetReligion();local ur=live:GetReligion()
  local definition=GameInfo.Units[live:GetType()]
  current,currentKey=Owner(pid,false)
  if current~=player or currentKey~=key or Turn()~=op.turn or UnitHash()~=op.unitHash
    or not Object(definition) or definition.UnitType~="UNIT_MISSIONARY"
    or live:GetID()~=unit.unitID or live:GetOwner()~=pid or live:IsDelayedDeath()~=false
    or live:GetX()~=unit.x or live:GetY()~=unit.y or live:GetMovesRemaining()~=unit.moves
    or live:GetFormationUnitCount()~=1 or ur:GetReligionType()~=op.religionIndex
    or ur:GetSpreadCharges()~=unit.charges or pr:GetReligionTypeCreated()~=op.religionIndex
    or pr:GetFaithBalance()~=snap.faithBalance or op.faithBefore-snap.faithBalance~=op.cost
    or city:GetID()~=op.cityID or city:GetOwner()~=pid or city:GetX()~=op.x or city:GetY()~=op.y
    or city:GetReligion():GetMajorityReligion()~=op.religionIndex then return nil end
  return snap,unit
end
local function Observe(player,pid,key,state)
  local j=BaiqiMissionaryPurchaseJournal
  for id,op in pairs(state.operations) do
    if op.stage=="ARMED" and Turn()==op.turn and UnitHash()==op.unitHash then
      local snap=BaiqiMissionaryPurchaseSnapshot.Read(player,pid,op.cityID)
      local unit=ReceiptUnit(player,pid,op,snap)
      if unit then
        local fresh,actual=FreshReceipt(player,pid,key,state,op,unit)
        if fresh then
          local nextState=j.Clone(state,pid)
          nextState.operations[id].stage="OBSERVED"
          nextState.operations[id].newUnitID=actual.unitID
          nextState.operations[id].faithAfter=fresh.faithBalance
          if not Persist(player,pid,key,nextState)then return nil end
          return nextState
        end
      end
    end
  end
  return state
end
local function Inspect(pid,token)
  local player,key=Owner(pid,false)
  if not player then return "UNAVAILABLE",nil,"owner_or_configuration" end
  local state=Load(player,pid,key)
  if not state then return "UNKNOWN",nil,"journal_unavailable" end
  if token~=nil then
    if type(token)~="string" then return "UNKNOWN",nil,"invalid_token" end
    local found=false
    for _,op in pairs(state.operations) do if op.token==token then found=true end end
    if not found then return "UNKNOWN",token,"unknown_token" end
  end
  state=Observe(player,pid,key,state)
  if not state then return "UNKNOWN",token,"receipt_write_unconfirmed" end
  for _,op in pairs(state.operations) do
    if token and op.token==token then return op.stage,op.token,"inspected" end
    if not token and op.stage=="ARMED" then return "ARMED",op.token,"unresolved" end
  end
  return "OPEN",nil,"no_unresolved"
end
local function SameIDs(a,b)
  if not a or not b or #a~=#b then return false end
  for i=1,#a do if a[i]~=b[i]then return false end end
  return true
end
local function FaithOpen(player,pid)
  if not Object(BaiqiFaithPurchaseGuard)or type(BaiqiFaithPurchaseGuard.Open)~="function" then return false end
  return BaiqiFaithPurchaseGuard.Open({Config=BaiqiConfig,NaturalistJournal=BaiqiNaturalistPurchaseJournal,
    MissionaryJournal=BaiqiMissionaryPurchaseJournal},player,pid)==true
end
local function Prepare(pid,cityID,x,y,unitHash,religionIndex,cost,faithBefore,reserve)
  local j=BaiqiMissionaryPurchaseJournal
  if not j.Integer(pid,MAX)or not j.Integer(cityID,MAX)or not j.Integer(x,MAX)or not j.Integer(y,MAX)
    or not j.Integer(religionIndex,MAX)or not Hash(unitHash)or not Number(cost)or cost<=0
    or not Number(faithBefore)or faithBefore<0 or not Number(reserve)or reserve<0
    or faithBefore-cost<reserve then return false,nil,"invalid_quote" end
  local player,key=Owner(pid,true)
  local turn=player and Turn()
  if not player or not turn or UnitHash()~=unitHash then return false,nil,"owner_or_type" end
  local state=Load(player,pid,key)
  if not state then return false,nil,"journal_unavailable" end
  state=Observe(player,pid,key,state)
  if not state then return false,nil,"receipt_write_unconfirmed" end
  local count=0
  for _,op in pairs(state.operations)do count=count+1;if op.stage=="ARMED"then return false,nil,"prior_unresolved"end end
  if count>=256 or state.serial>=MAX then return false,nil,"journal_limit"end
  local function Eligible()
    local fresh,currentKey=Owner(pid,true)
    if not fresh or currentKey~=key or Turn()~=turn or UnitHash()~=unitHash then return nil end
    local snap=BaiqiMissionaryPurchaseSnapshot.Read(fresh,pid,cityID)
    if not snap or snap.cityID~=cityID or snap.owner~=pid or snap.x~=x or snap.y~=y
      or snap.faithBalance~=faithBefore or snap.religionIndex~=religionIndex
      or snap.majorityReligion~=religionIndex then return nil end
    local ids={}
    for _,v in ipairs(snap.missionaries)do
      if v.religionIndex==religionIndex and v.charges>0 then return nil end
      ids[#ids+1]=v.unitID
    end
    return ids
  end
  local first=Eligible()
  if not first or not FaithOpen(player,pid)then return false,nil,"snapshot_or_shared_faith_held"end
  if not Object(BaiqiReligiousIntentGameplay)or type(BaiqiReligiousIntentGameplay.Initialize)~="function"
    or BaiqiReligiousIntentGameplay.Initialize(pid)~=true then return false,nil,"spread_initialization_unconfirmed"end
  local second=Eligible()
  if not SameIDs(first,second)then return false,nil,"snapshot_changed"end
  if not FaithOpen(player,pid)or not j.Equal(state,Load(player,pid,key),pid)then return false,nil,"journal_changed"end
  local final=Eligible()
  if not SameIDs(second,final)then return false,nil,"snapshot_changed"end
  if not FaithOpen(player,pid)or not j.Equal(state,Load(player,pid,key),pid)then return false,nil,"journal_changed"end
  local nextState=j.Clone(state,pid);nextState.serial=nextState.serial+1
  local seq=nextState.serial;local token=j.Token(pid,seq)
  nextState.operations[j.Key(seq)]={token=token,sequence=seq,cityID=cityID,unitType="UNIT_MISSIONARY",
    unitHash=unitHash,religionIndex=religionIndex,x=x,y=y,cost=cost,faithBefore=faithBefore,reserve=reserve,
    turn=turn,stage="ARMED",baselineUnitIDs=final}
  if not Persist(player,pid,key,nextState)then return false,nil,"intent_write_unconfirmed"end
  return true,token,"armed"
end
local stopped=false
local bridge={version=1,marker=MARKER}
function bridge.Prepare(...)
  if stopped or type(ExposedMembers)~="table"or ExposedMembers.BaiqiMissionaryPurchaseBridge~=bridge then return false,nil,"bridge_not_owned"end
  local ok,a,b,c=pcall(Prepare,...)
  if ok then return a,b,c end
  return false,nil,"prepare_unavailable"
end
function bridge.Inspect(...)
  if stopped or type(ExposedMembers)~="table"or ExposedMembers.BaiqiMissionaryPurchaseBridge~=bridge then return "UNAVAILABLE",nil,"bridge_not_owned"end
  local ok,a,b,c=pcall(Inspect,...)
  if ok then return a,b,c end
  return "UNAVAILABLE",nil,"inspect_unavailable"
end
pcall(function()
  if type(ExposedMembers)=="table" then
    local prior=ExposedMembers.BaiqiMissionaryPurchaseBridge
    if prior==nil or (type(prior)=="table" and prior.version==1 and prior.marker==MARKER) then
      ExposedMembers.BaiqiMissionaryPurchaseBridge=bridge
    end
  end
end)
local subscriptions={}
local function Shutdown()
  if stopped then return end
  stopped=true
  for _,owned in ipairs(subscriptions) do pcall(owned.remove,owned.callback) end
  subscriptions={}
end
pcall(function()
  if previousModule and type(previousModule.Shutdown)=="function" then previousModule.Shutdown() end
end)
BaiqiMissionaryPurchaseIntentGameplay.Shutdown=Shutdown
local function ObserveEvent(playerID)
  if stopped or type(ExposedMembers)~="table"or ExposedMembers.BaiqiMissionaryPurchaseBridge~=bridge then return end
  pcall(function()
    if playerID==Game.GetLocalPlayer() then bridge.Inspect(playerID) end
  end)
end
for _,name in ipairs({"UnitAddedToMap","PlayerTurnDeactivated"}) do
  pcall(function()
    if type(Events)~="table" or type(ExposedMembers)~="table"
      or ExposedMembers.BaiqiMissionaryPurchaseBridge~=bridge then return end
    local event=Events[name]
    if not Object(event) or type(event.Add)~="function" or type(event.Remove)~="function" then return end
    local add,remove=event.Add,event.Remove
    if pcall(add,ObserveEvent) then
      subscriptions[#subscriptions+1]={event=event,remove=remove,callback=ObserveEvent}
    end
  end)
end
return BaiqiMissionaryPurchaseIntentGameplay
