if BaiqiProphetIntentGameplay then return end
include("BaiqiProphetJournal")
local J,C=BaiqiProphetJournal,BaiqiConfig
local KEY=C.prophetIntentKey
local MARKER="baiqi-prophet-intent-v1"
local function Owner(pid,active)
  if not J.Integer(pid,2147483647) or pid~=Game.GetLocalPlayer()
    or GameConfiguration.IsAnyMultiplayer()
    or (GameConfiguration.IsHotseat and GameConfiguration.IsHotseat()) then return nil end
  local player,config=Players[pid],PlayerConfigurations[pid]
  if not player or not config or config:GetLeaderTypeName()~=C.leader then return nil end
  local human
  if type(config.IsHuman)=="function" then human=config:IsHuman()
  elseif type(player.IsHuman)=="function" then human=player:IsHuman() end
  if human~=true or (active and (player:IsTurnActive()~=true
    or type(Game.IsAllowStrategicCommands)~="function" or Game.IsAllowStrategicCommands(pid)~=true))
    or type(player.GetProperty)~="function" or type(player.SetProperty)~="function" then return nil end
  return player
end
local function Signed(value)
  return type(value)=="number" and value==value and math.abs(value)<math.huge and value%1==0 and value>=-1 and value<=2147483647
end
-- ABSENT is an actual failed full-ID lookup. Aliases and unreadable objects
-- remain UNKNOWN; they cannot prove this prophet was consumed.
local function ReadIdentity(player,pid,id)
  if not J.Integer(id,2147483647) then return "UNKNOWN" end
  local unit=player:GetUnits():FindID(id)
  if unit==nil then return "ABSENT" end
  for _,name in ipairs({"GetID","GetOwner","GetX","GetY","GetGreatPerson"}) do
    if type(unit[name])~="function" then return "UNKNOWN" end
  end
  if unit:GetID()~=id or unit:GetOwner()~=pid then return "UNKNOWN" end
  local index
  if type(unit.GetType)=="function" then index=unit:GetType()
  elseif type(unit.GetUnitType)=="function" then index=unit:GetUnitType() end
  local def=index~=nil and GameInfo.Units[index]
  if not def or def.UnitType~="UNIT_GREAT_PROPHET" then return "UNKNOWN" end
  local gp=unit:GetGreatPerson()
  if not gp or type(gp.GetIndividual)~="function" or type(gp.GetClass)~="function" then return "UNKNOWN" end
  local info=GameInfo.GreatPersonIndividuals[gp:GetIndividual()]
  local class=GameInfo.GreatPersonClasses[gp:GetClass()]
  if not info or not class or info.GreatPersonClassType~="GREAT_PERSON_CLASS_PROPHET"
    or class.GreatPersonClassType~="GREAT_PERSON_CLASS_PROPHET"
    or not J.Integer(info.Index,2147483647) or not J.Integer(class.Index,2147483647) then return "UNKNOWN" end
  local x,y=unit:GetX(),unit:GetY()
  if not J.Integer(x,2147483647) or not J.Integer(y,2147483647) then return "UNKNOWN" end
  local moves=type(unit.GetMovesRemaining)=="function" and unit:GetMovesRemaining() or nil
  local formation=type(unit.GetFormationUnitCount)=="function" and unit:GetFormationUnitCount() or nil
  return "LIVE",{id=id,unitType=def.UnitType,class=class.Index,individual=info.Index,x=x,y=y,moves=moves,formation=formation}
end
local function ReadLive(player,pid,id)
  local status,live=ReadIdentity(player,pid,id)
  if status~="LIVE" or not BaiqiPolicy.Number(live.moves) or live.moves<=0 or live.formation~=1 then return nil end
  local plot=Map.GetPlot(live.x,live.y)
  local visibility=PlayersVisibility[pid]
  if not plot or plot:GetOwner()~=pid or type(plot.IsWater)~="function" or plot:IsWater()
    or not visibility or visibility:IsRevealed(live.x,live.y)~=true or visibility:IsVisible(live.x,live.y)~=true then return nil end
  local religion=type(player.GetReligion)=="function" and player:GetReligion()
  if not religion or type(religion.GetReligionTypeCreated)~="function" then return nil end
  local created=religion:GetReligionTypeCreated()
  if not Signed(created) or created~=-1 then return nil end
  -- Earned capacity/founding qualification are UI-only native getters. The UI
  -- repeats them at dispatch; Core does not fabricate an independent read.
  return live
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
    class=live.class,individual=live.individual,x=live.x,y=live.y,turn=Game.GetCurrentGameTurn(),earned=0,stage=stage,eventSeen=false}
  state.operations[key]=op
  return op
end
local function Load(player,pid)
  local raw=player:GetProperty(KEY)
  if raw~=nil then return J.Clone(raw,pid) end
  local state=J.New(pid)
  for _,unit in player:GetUnits():Members() do
    local index
    if type(unit.GetType)=="function" then index=unit:GetType()
    elseif type(unit.GetUnitType)=="function" then index=unit:GetUnitType() end
    local def=index~=nil and GameInfo.Units[index]
    if not def then return nil end
    if def.UnitType=="UNIT_GREAT_PROPHET" then
      local status,identity=ReadIdentity(player,pid,unit:GetID())
      if status~="LIVE" or not Entry(pid,state,identity,"LEGACY_UNKNOWN") then return nil end
    end
  end
  if Persist(player,pid,state) then return state end
end
local function Same(op,live)
  return live and live.id==op.unitID and live.unitType==op.unitType
    and live.class==op.class and live.individual==op.individual
end
local function Reconcile(player,pid,state,op,event)
  if op.stage~="ARMED" then return true,op.stage end
  local changed=false
  if event and not op.eventSeen then op.eventSeen=true;changed=true end
  local proof
  if op.eventSeen then
    local status,identity=ReadIdentity(player,pid,op.unitID)
    if status=="ABSENT" then proof="native_activation_and_consumed_unit"
    elseif status=="LIVE" and Same(op,identity) then
      local religion=type(player.GetReligion)=="function" and player:GetReligion()
      local created=religion and type(religion.GetReligionTypeCreated)=="function" and religion:GetReligionTypeCreated()
      if Signed(created) and created>=0 then proof="native_activation_and_created_religion" end
    end
  end
  if proof then op.stage="OBSERVED";changed=true end
  if changed and not Persist(player,pid,state) then return false,"persist_unconfirmed" end
  return true,proof or "awaiting_correlated_native_effect"
end
local function Inspect(pid,id)
  local player=Owner(pid,false)
  if not player or not J.UnitKey(id) then return "UNAVAILABLE",nil,"owner_or_id" end
  local state=Load(player,pid)
  if not state then return "UNAVAILABLE",nil,"journal_unavailable" end
  local op=state.operations[J.UnitKey(id)]
  if not op then return "OPEN",nil,"no_prior_intent" end
  local ok,reason=Reconcile(player,pid,state,op,false)
  if not ok then return "UNAVAILABLE",op.token,reason end
  return op.stage,op.token,reason
end
local function Prepare(pid,id,classIndex,individualIndex,x,y,earnedBaseline)
  local player=Owner(pid,true)
  if not player or not J.Integer(id,2147483647) then return false,nil,"owner_or_id" end
  local state=Load(player,pid)
  if not state then return false,nil,"journal_unavailable" end
  local prior=state.operations[J.UnitKey(id)]
  if prior then return false,prior.token,"prior_intent" end
  for _,op in pairs(state.operations) do
    if op.stage=="ARMED" or op.stage=="LEGACY_UNKNOWN" then return false,op.token,"other_unknown_prophet" end
  end
  local live=ReadLive(player,pid,id)
  if not live or live.class~=classIndex or live.individual~=individualIndex
    or live.x~=x or live.y~=y or earnedBaseline~=0 or not Owner(pid,true) then return false,nil,"unit_changed" end
  local op=Entry(pid,state,live,"ARMED")
  if not op or not Persist(player,pid,state) then return false,nil,"persist_unconfirmed" end
  return true,op.token,"persisted"
end
local function Observe(pid,id,classIndex,individualIndex)
  local player=Owner(pid,false)
  if not player or not J.UnitKey(id) then return "UNAVAILABLE",nil,"owner_or_id" end
  local state=Load(player,pid)
  if not state then return "UNAVAILABLE",nil,"journal_unavailable" end
  local op=state.operations[J.UnitKey(id)]
  local class=GameInfo.GreatPersonClasses[classIndex]
  local info=GameInfo.GreatPersonIndividuals[individualIndex]
  if not op or not class or not info or class.Index~=op.class or info.Index~=op.individual
    or class.GreatPersonClassType~="GREAT_PERSON_CLASS_PROPHET"
    or info.GreatPersonClassType~="GREAT_PERSON_CLASS_PROPHET" then return "UNAVAILABLE",nil,"event_identity" end
  local ok,reason=Reconcile(player,pid,state,op,true)
  if not ok then return "UNAVAILABLE",op.token,reason end
  return op.stage,op.token,reason
end
local function Protected(fn,failure)
  return function(...)
    local ok,a,b,c=pcall(fn,...)
    if ok then return a,b,c end
    print("BAIQI|prophet_intent_unavailable|"..tostring(a))
    return failure,nil,"handler_error"
  end
end
local bridge={version=1,marker=MARKER,Inspect=Protected(Inspect,"UNAVAILABLE"),
  Prepare=Protected(Prepare,false),Observe=Protected(Observe,"UNAVAILABLE")}
BaiqiProphetIntentGameplay={}
local function Bootstrap()
  local pid=Game.GetLocalPlayer()
  local player=Owner(pid,false)
  if player then Load(player,pid) end
end
if type(ExposedMembers)=="table" and (ExposedMembers.BaiqiProphetIntentBridge==nil
  or (type(ExposedMembers.BaiqiProphetIntentBridge)=="table"
    and ExposedMembers.BaiqiProphetIntentBridge.marker==MARKER
    and ExposedMembers.BaiqiProphetIntentBridge.version==1)) then
  ExposedMembers.BaiqiProphetIntentBridge=bridge
  if GameEvents and GameEvents.OnGameTurnStarted then GameEvents.OnGameTurnStarted.Add(Protected(Bootstrap,false)) end
  if GameEvents and GameEvents.BaiqiRequisitionRecover then GameEvents.BaiqiRequisitionRecover.Add(Protected(Bootstrap,false)) end
  Protected(Bootstrap,false)()
  print("BAIQI|prophet_intent_loaded|version=1")
else
  print("BAIQI|prophet_intent_unavailable|bridge_conflict=true")
end