include("BaiqiConfig")
include("BaiqiNaturalistUnit")
include("BaiqiNaturalistPurchaseSnapshot")
include("BaiqiNaturalistPurchaseJournal")

-- The UI supplies the current engine quote. Core independently checks the
-- balance, city and stock; Core has no UI city:GetGold() price component.
BaiqiNaturalistPurchaseIntentGameplay={}
local MARKER="baiqi-naturalist-purchase-v1"
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
  local j=BaiqiNaturalistPurchaseJournal
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
  local key=BaiqiConfig.naturalistPurchaseIntentKey
  if human~=true or (active and (type(player.IsTurnActive)~="function" or player:IsTurnActive()~=true))
    or type(player.GetProperty)~="function" or type(player.SetProperty)~="function"
    or type(key)~="string" or #key==0 or #key>128 then return nil end
  return player,key
end
local function UnitHash()
  if not Object(GameInfo) or not Object(GameInfo.Units) then return nil end
  local row=GameInfo.Units.UNIT_NATURALIST
  if Object(row) and row.UnitType=="UNIT_NATURALIST" and Hash(row.Hash) then return row.Hash end
end
local function Turn()
  local turn=Game.GetCurrentGameTurn()
  if BaiqiNaturalistPurchaseJournal.Integer(turn,MAX) then return turn end
end
local function Load(player,pid,key)
  -- A thrown read escapes into the bridge's protected call; it is never nil.
  local raw=player:GetProperty(key)
  if raw==nil then return BaiqiNaturalistPurchaseJournal.New(pid) end
  return BaiqiNaturalistPurchaseJournal.Clone(raw,pid)
end
local function Persist(player,pid,key,state)
  local j=BaiqiNaturalistPurchaseJournal
  local value=j.Clone(state,pid)
  if not value then return false end
  player:SetProperty(key,value)
  return j.Equal(state,player:GetProperty(key),pid)
end
local function Observe(player,pid,key,state)
  local j=BaiqiNaturalistPurchaseJournal
  for id,op in pairs(state.operations) do
    if op.stage=="ARMED" and Turn()==op.turn and UnitHash()==op.unitHash then
      local snapshot=BaiqiNaturalistPurchaseSnapshot.Read(player,pid,op.cityID)
      if snapshot and snapshot.x==op.x and snapshot.y==op.y and #snapshot.naturalists==1
        and op.faithBefore-snapshot.faithBalance==op.cost then
        local unit=snapshot.naturalists[1]
        local old=false
        for _,prior in ipairs(op.baselineUnitIDs) do if prior==unit.unitID then old=true end end
        if not old and unit.unitType=="UNIT_NATURALIST" and j.Integer(unit.unitID,MAX)
          and unit.charges>=1 and unit.x==op.x and unit.y==op.y and unit.formation==1 then
          local nextState=j.Clone(state,pid)
          nextState.operations[id].stage="OBSERVED"
          nextState.operations[id].newUnitID=unit.unitID
          nextState.operations[id].faithAfter=snapshot.faithBalance
          if not Persist(player,pid,key,nextState) then return nil end
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
local function Prepare(pid,cityID,x,y,unitHash,cost,faithBefore,reserve)
  local j=BaiqiNaturalistPurchaseJournal
  if not j.Integer(pid,MAX) or not j.Integer(cityID,MAX) or not j.Integer(x,MAX) or not j.Integer(y,MAX)
    or not Hash(unitHash) or not Number(cost) or cost<=0 or not Number(faithBefore) or faithBefore<0
    or not Number(reserve) or reserve<0 or faithBefore-cost<reserve then return false,nil,"invalid_quote" end
  local player,key=Owner(pid,true)
  local turn=player and Turn()
  if not player or not turn or UnitHash()~=unitHash then return false,nil,"owner_or_type" end
  local state=Load(player,pid,key)
  if not state then return false,nil,"journal_unavailable" end
  state=Observe(player,pid,key,state)
  if not state then return false,nil,"receipt_write_unconfirmed" end
  local count=0
  for _,op in pairs(state.operations) do
    count=count+1
    if op.stage=="ARMED" then return false,nil,"prior_unresolved" end
  end
  if count>=256 or state.serial>=MAX then return false,nil,"journal_limit" end
  local function Eligible()
    local fresh,currentKey=Owner(pid,true)
    if not fresh or currentKey~=key or Turn()~=turn or UnitHash()~=unitHash then return false end
    local snapshot=BaiqiNaturalistPurchaseSnapshot.Read(fresh,pid,cityID)
    return snapshot and snapshot.x==x and snapshot.y==y and snapshot.faithBalance==faithBefore
      and #snapshot.naturalists==0
  end
  if not Eligible() or not Eligible() then return false,nil,"snapshot_changed" end
  if not j.Equal(state,Load(player,pid,key),pid) then return false,nil,"journal_changed" end
  local nextState=j.Clone(state,pid)
  nextState.serial=nextState.serial+1
  local seq=nextState.serial
  local token=j.Token(pid,seq)
  nextState.operations[j.Key(seq)]={token=token,sequence=seq,cityID=cityID,unitType="UNIT_NATURALIST",
    unitHash=unitHash,x=x,y=y,cost=cost,faithBefore=faithBefore,reserve=reserve,turn=turn,
    stage="ARMED",baselineUnitIDs={}}
  if not Persist(player,pid,key,nextState) then return false,nil,"intent_write_unconfirmed" end
  return true,token,"armed"
end
local bridge={version=1,marker=MARKER}
function bridge.Prepare(...)
  local ok,a,b,c=pcall(Prepare,...)
  if ok then return a,b,c end
  return false,nil,"prepare_unavailable"
end
function bridge.Inspect(...)
  local ok,a,b,c=pcall(Inspect,...)
  if ok then return a,b,c end
  return "UNAVAILABLE",nil,"inspect_unavailable"
end
if type(ExposedMembers)=="table" then
  local prior=ExposedMembers.BaiqiNaturalistPurchaseBridge
  if prior==nil or (type(prior)=="table" and prior.version==1 and prior.marker==MARKER) then
    ExposedMembers.BaiqiNaturalistPurchaseBridge=bridge
  end
end
return BaiqiNaturalistPurchaseIntentGameplay
