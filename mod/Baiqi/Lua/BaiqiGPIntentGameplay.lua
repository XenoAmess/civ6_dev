-- Gameplay owns durable intent metadata; UI remains the sole command emitter.
if BaiqiGPIntentGameplay then return end
include("BaiqiGPJournal")
local J,C=BaiqiGPJournal,BaiqiConfig
local KEY=C.greatPersonIntentKey
local MARKER="baiqi-gp-intent-v1"
local function Owner(pid,active)
  if not J.Integer(pid,2147483647) or pid~=Game.GetLocalPlayer()
    or GameConfiguration.IsAnyMultiplayer()
    or (GameConfiguration.IsHotseat and GameConfiguration.IsHotseat()) then return nil end
  local player,config=Players[pid],PlayerConfigurations[pid]
  if not player or not config or config:GetLeaderTypeName()~=C.leader then return nil end
  local human
  if type(config.IsHuman)=="function" then human=config:IsHuman()
  elseif type(player.IsHuman)=="function" then human=player:IsHuman() end
  if human~=true or (active and player:IsTurnActive()~=true)
    or type(player.GetProperty)~="function" or type(player.SetProperty)~="function" then return nil end
  return player
end
local function ReadLive(player,pid,id)
  -- FindID can return a recycled slot. Reject unsupported engine-sized IDs
  -- before entering native code, while retaining larger IDs in saved metadata.
  if not J.Integer(id,2147483647) then return nil end
  local unit=player:GetUnits():FindID(id)
  if not unit or unit:GetID()~=id or unit:GetOwner()~=pid then return nil end
  local index
  if type(unit.GetType)=="function" then index=unit:GetType()
  elseif type(unit.GetUnitType)=="function" then index=unit:GetUnitType() end
  local def=index~=nil and GameInfo.Units[index]
  local expected=def and BaiqiPolicy.DistrictGreatPersonClass(def.UnitType)
  local gp=expected and type(unit.GetGreatPerson)=="function" and unit:GetGreatPerson()
  if not gp then return nil end
  local info=GameInfo.GreatPersonIndividuals[gp:GetIndividual()]
  local class=GameInfo.GreatPersonClasses[gp:GetClass()]
  local charges=gp:GetActionCharges()
  if not info or not class or info.GreatPersonClassType~=expected or class.GreatPersonClassType~=expected
    or not J.Integer(info.Index,2147483647) or not J.Integer(class.Index,2147483647)
    or not J.Integer(charges,1000000) or info.ActionRequiresSuzerainTerritory==true
    or info.ActionRequiresSuzerainTerritory==1 or info.ActionRequiresSuzerainTerritory=="True"
    or info.ActionRequiresSuzerainTerritory=="true" then return nil end
  return {id=id,unitType=def.UnitType,class=class.Index,individual=info.Index,charges=charges,
    x=unit:GetX(),y=unit:GetY(),moves=unit:GetMovesRemaining(),
    formation=type(unit.GetFormationUnitCount)=="function" and unit:GetFormationUnitCount() or nil}
end
local function Persist(player,pid,state)
  if not J.Validate(state,pid) then return false end
  player:SetProperty(KEY,state)
  return J.Equal(state,player:GetProperty(KEY),pid)
end
local function Entry(pid,state,live,stage)
  if state.serial>=2147483647 or not J.Integer(Game.GetCurrentGameTurn(),2147483647) then return nil end
  local count=0;for _ in pairs(state.operations) do count=count+1 end
  local key=J.UnitKey(live.id)
  if not key or (not state.operations[key] and count>=256) then return nil end
  state.serial=state.serial+1
  local op={token=J.Token(pid,state.serial),sequence=state.serial,unitID=live.id,unitType=live.unitType,
    class=live.class,individual=live.individual,charges=live.charges,
    turn=Game.GetCurrentGameTurn(),stage=stage,eventSeen=false}
  state.operations[key]=op
  return op
end
local function Load(player,pid)
  local raw=player:GetProperty(KEY)
  if raw~=nil then return J.Clone(raw,pid) end
  -- Old saves contain no historical command receipts. Existing charged people
  -- are held rather than being guessed to be safe to activate again.
  local state=J.New(pid)
  for _,unit in player:GetUnits():Members() do
    local index
    if type(unit.GetType)=="function" then index=unit:GetType()
    elseif type(unit.GetUnitType)=="function" then index=unit:GetUnitType() end
    local def=index~=nil and GameInfo.Units[index]
    if def and BaiqiPolicy.DistrictGreatPersonClass(def.UnitType) then
      local live=ReadLive(player,pid,unit:GetID())
      if not live then return nil end
      if live.charges>0 and not Entry(pid,state,live,"LEGACY_UNKNOWN") then return nil end
    end
  end
  if Persist(player,pid,state) then return state end
end
local function Same(op,live)
  return live and live.id==op.unitID and live.unitType==op.unitType
    and live.class==op.class and live.individual==op.individual
end
local function Reconcile(player,pid,state,op,live,event)
  local changed=false
  if op.stage~="ARMED" then
    if op.stage=="OBSERVED" and Same(op,live) and live.charges<op.charges then return true,"charges="..live.charges end
    if op.stage=="OBSERVED" and not live and op.eventSeen then return true,"native_activation_event" end
    return true,op.stage
  end
  if event and not op.eventSeen then op.eventSeen=true;changed=true end
  local proof
  if Same(op,live) and live.charges<op.charges then proof="charges="..live.charges
  elseif not live and op.eventSeen then proof="native_activation_event" end
  if proof then op.stage="OBSERVED";changed=true end
  if changed and not Persist(player,pid,state) then return false,"persist_unconfirmed" end
  return true,proof or "awaiting_native_activation_or_charge_change"
end
local function Inspect(pid,id)
  local player=Owner(pid,false)
  if not player or not J.UnitKey(id) then return "UNAVAILABLE",nil,"owner_or_id" end
  local state=Load(player,pid)
  if not state then return "UNAVAILABLE",nil,"journal_unavailable" end
  local op=state.operations[J.UnitKey(id)]
  if not op then return "OPEN",nil,"no_prior_intent" end
  local ok,reason=Reconcile(player,pid,state,op,ReadLive(player,pid,id),false)
  if not ok then return "UNAVAILABLE",op.token,reason end
  return op.stage,op.token,reason
end
local function Prepare(pid,id,unitType,class,individual,charges,x,y)
  local player=Owner(pid,true)
  if not player then return false,nil,"owner" end
  local state=Load(player,pid)
  if not state then return false,nil,"journal_unavailable" end
  local live=ReadLive(player,pid,id)
  if not live or live.unitType~=unitType or live.class~=class or live.individual~=individual
    or live.charges~=charges or charges<=0 or live.x~=x or live.y~=y
    or not J.Integer(x,2147483647) or not J.Integer(y,2147483647)
    or not BaiqiPolicy.Number(live.moves) or live.moves<=0 or live.formation~=1 then return false,nil,"unit_changed" end
  local plot=Map.GetPlot(x,y)
  local visibility=PlayersVisibility[pid]
  local info=GameInfo.GreatPersonIndividuals[live.individual]
  if not BaiqiPolicy.GreatPersonActivationPlot(live.unitType,info,pid,plot,visibility,Map) then return false,nil,"plot" end
  local prior=state.operations[J.UnitKey(id)]
  if prior then
    local ok=Reconcile(player,pid,state,prior,live,false)
    if not ok or prior.stage~="OBSERVED" or not Same(prior,live) or live.charges>=prior.charges then
      return false,prior.token,"prior_intent"
    end
  end
  local op=Entry(pid,state,live,"ARMED")
  if not op or not Persist(player,pid,state) then return false,nil,"persist_unconfirmed" end
  -- This scalar is a fresh Core acknowledgement, not a stale UI property read.
  return true,op.token,"persisted"
end
local function Observe(pid,id,classID,individualID)
  local player=Owner(pid,false)
  if not player or not J.UnitKey(id) then return "UNAVAILABLE",nil,"owner_or_id" end
  local state=Load(player,pid)
  if not state then return "UNAVAILABLE",nil,"journal_unavailable" end
  local op=state.operations[J.UnitKey(id)]
  local class=GameInfo.GreatPersonClasses[classID]
  local info=GameInfo.GreatPersonIndividuals[individualID]
  if not op or not class or not info or class.Index~=op.class or info.Index~=op.individual
    or class.GreatPersonClassType~=BaiqiPolicy.DistrictGreatPersonClass(op.unitType)
    or info.GreatPersonClassType~=class.GreatPersonClassType then return "UNAVAILABLE",nil,"event_identity" end
  local ok,reason=Reconcile(player,pid,state,op,ReadLive(player,pid,id),true)
  if not ok then return "UNAVAILABLE",op.token,reason end
  return op.stage,op.token,reason
end
-- Exceptions cannot become grants. Never export native objects across contexts.
local function Protected(fn,failure)
  return function(...)
    local ok,a,b,c=pcall(fn,...)
    if ok then return a,b,c end
    print("BAIQI|great_person_intent_unavailable|"..tostring(a))
    return failure,nil,"handler_error"
  end
end
local bridge={version=1,marker=MARKER,Inspect=Protected(Inspect,"UNAVAILABLE"),
  Prepare=Protected(Prepare,false),Observe=Protected(Observe,"UNAVAILABLE")}
BaiqiGPIntentGameplay={}
local function Bootstrap()
  local pid=Game.GetLocalPlayer()
  local player=Owner(pid,false)
  if player then Load(player,pid) end
end
if type(ExposedMembers)=="table" and (ExposedMembers.BaiqiGreatPersonIntentBridge==nil
  or (type(ExposedMembers.BaiqiGreatPersonIntentBridge)=="table"
    and ExposedMembers.BaiqiGreatPersonIntentBridge.marker==MARKER
    and ExposedMembers.BaiqiGreatPersonIntentBridge.version==1)) then
  ExposedMembers.BaiqiGreatPersonIntentBridge=bridge
  if GameEvents and GameEvents.OnGameTurnStarted then GameEvents.OnGameTurnStarted.Add(Protected(Bootstrap,false)) end
  if GameEvents and GameEvents.BaiqiRequisitionRecover then GameEvents.BaiqiRequisitionRecover.Add(Protected(Bootstrap,false)) end
  Protected(Bootstrap,false)()
  print("BAIQI|great_person_intent_loaded|version=1")
else
  print("BAIQI|great_person_intent_unavailable|bridge_conflict=true")
end
