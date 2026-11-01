-- Core persists intents and its own native events; it never emits unit commands.
if BaiqiCreativeIntentGameplay then return end
include("BaiqiCreativeJournal")
local J,N=BaiqiCreativeJournal,BaiqiGPJournal
local KEY,MARKER=BaiqiConfig.creativeIntentKey,"baiqi-creative-intent-v1"
local MAX=2147483647
local function Owner(pid,active)
 if not N.Integer(pid,MAX) or pid~=Game.GetLocalPlayer() or GameConfiguration.IsAnyMultiplayer()
  or (GameConfiguration.IsHotseat and GameConfiguration.IsHotseat()) then return nil end
 local player,config=Players[pid],PlayerConfigurations[pid]
 if not player or not config or config:GetLeaderTypeName()~=BaiqiConfig.leader then return nil end
 local human
 if type(config.IsHuman)=="function" then human=config:IsHuman()
 elseif type(player.IsHuman)=="function" then human=player:IsHuman() end
 if human~=true or (active and player:IsTurnActive()~=true)
  or type(player.GetProperty)~="function" or type(player.SetProperty)~="function" then return nil end
 return player
end
local function Live(player,pid,id)
 if not N.Integer(id,MAX) then return nil end
 local u=player:GetUnits():FindID(id)
 if not u or u:GetID()~=id or u:GetOwner()~=pid then return nil end
 local index
 if type(u.GetType)=="function" then index=u:GetType()
 elseif type(u.GetUnitType)=="function" then index=u:GetUnitType() end
 local def=index~=nil and GameInfo.Units[index]
 local expected=def and BaiqiPolicy.CreativeGreatPersonClass(def.UnitType)
 local gp=expected and type(u.GetGreatPerson)=="function" and u:GetGreatPerson()
 local info=gp and GameInfo.GreatPersonIndividuals[gp:GetIndividual()]
 local class=gp and GameInfo.GreatPersonClasses[gp:GetClass()]
 if not info or not class or info.GreatPersonClassType~=expected or class.GreatPersonClassType~=expected
  or not N.Integer(info.Index,MAX) or not N.Integer(class.Index,MAX) then return nil end
 return {id=id,unitType=def.UnitType,class=class.Index,individual=info.Index,x=u:GetX(),y=u:GetY(),
  moves=u:GetMovesRemaining(),formation=type(u.GetFormationUnitCount)=="function" and u:GetFormationUnitCount() or nil}
end
local function Persist(player,pid,state)
 if not J.Validate(state,pid) then return false end
 player:SetProperty(KEY,state)
 return J.Equal(state,player:GetProperty(KEY),pid)
end
local function Same(op,live)
 return live and op.unitID==live.id and op.unitType==live.unitType
  and op.class==live.class and op.individual==live.individual
end
local function Entry(state,pid,live,stage,prior)
 local count=0;for _ in pairs(state.operations) do count=count+1 end
 local key=N.UnitKey(live.id)
 if not key or state.serial>=MAX or (not state.operations[key] and count>=256)
  or not N.Integer(Game.GetCurrentGameTurn(),MAX) then return nil end
 local works={};if prior then for index in pairs(prior.works) do works[index]=true end end
 local n=0;for _ in pairs(works) do n=n+1 end
 if n>=64 then return nil end
 state.serial=state.serial+1
 local op={token=J.Token(pid,state.serial),sequence=state.serial,unitID=live.id,unitType=live.unitType,
  class=live.class,individual=live.individual,turn=Game.GetCurrentGameTurn(),stage=stage,
  works=works,lastWork=prior and prior.lastWork or nil}
 state.operations[key]=op;return op
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
  if def and BaiqiPolicy.CreativeGreatPersonClass(def.UnitType) then
   local live=Live(player,pid,unit:GetID())
   if not live or not Entry(state,pid,live,"LEGACY_UNKNOWN") then return nil end
  end
 end
 if Persist(player,pid,state) then return state end
end
local function Busy(state,id)
 for _,op in pairs(state.operations) do if op.unitID~=id and op.stage=="ARMED" then return true end end
 return false
end
local function Inspect(pid,id)
 local player=Owner(pid,false)
 if not player or not N.UnitKey(id) then return "UNAVAILABLE",nil,"owner_or_id" end
 local state=Load(player,pid)
 if not state then return "UNAVAILABLE",nil,"journal_unavailable" end
 local op=state.operations[N.UnitKey(id)]
 if op and op.stage~="OBSERVED" then return op.stage,op.token,"awaiting_native_core_event" end
 if Busy(state,id) then return "BUSY",nil,"other_creative_intent" end
 if op then return op.stage,op.token,"native_core_event" end
 return "OPEN",nil,"no_prior_intent"
end
local function Prepare(pid,id,unitType,class,individual,x,y)
 local player=Owner(pid,true)
 if not player then return false,nil,"owner" end
 local state=Load(player,pid)
 if not state or Busy(state,id) then return false,nil,"journal_or_busy" end
 local live=Live(player,pid,id)
 if not live or live.unitType~=unitType or live.class~=class or live.individual~=individual
  or live.x~=x or live.y~=y or not N.Integer(x,MAX) or not N.Integer(y,MAX)
  or not BaiqiPolicy.Number(live.moves) or live.moves<=0 or live.formation~=1 then return false,nil,"unit_changed" end
 local plot=Map.GetPlot(x,y);local visibility=PlayersVisibility[pid]
 if not plot or not visibility or visibility:IsRevealed(x,y)~=true or visibility:IsVisible(x,y)~=true
  or plot:GetOwner()~=pid then return false,nil,"plot" end
 local prior=state.operations[N.UnitKey(id)]
 if prior and (prior.stage~="OBSERVED" or not Same(prior,live)) then return false,prior.token,"prior_intent" end
 local op=Entry(state,pid,live,"ARMED",prior)
 if not op or not Persist(player,pid,state) then return false,nil,"persist_unconfirmed" end
 return true,op.token,"persisted"
end
local function OnCreated(pid,id,x,y,buildingID,workIndex)
 local player=Owner(pid,false)
 if not player or not N.UnitKey(id) or not N.Integer(x,MAX) or not N.Integer(y,MAX)
  or not N.Integer(buildingID,MAX) or not N.Integer(workIndex,MAX) then return end
 local state=Load(player,pid);local op=state and state.operations[N.UnitKey(id)]
 if not op or op.stage~="ARMED" then return end
 local workKey=N.UnitKey(workIndex)
 for _,record in pairs(state.operations) do if record.works[workKey] then return end end
 local plot=Map.GetPlot(x,y);local visibility=PlayersVisibility[pid]
 if not plot or not visibility or visibility:IsRevealed(x,y)~=true or visibility:IsVisible(x,y)~=true
  or plot:GetOwner()~=pid then return end
 local city=Cities.GetCityInPlot(x,y);local row=GameInfo.Buildings[buildingID]
 if not city or city:GetOwner()~=pid or not row or row.Index~=buildingID
  or not city:GetBuildings():HasBuilding(row.Index) then return end
 op.works[workKey]=true;op.lastWork=workIndex;op.stage="OBSERVED"
 if Persist(player,pid,state) then
  print("BAIQI|creative_intent_observed|unit="..id.."|token="..op.token.."|work="..workIndex)
 end
end
local function Protected(fn,failure)
 return function(...)
  local ok,a,b,c=pcall(fn,...)
  if ok then return a,b,c end
  print("BAIQI|creative_intent_unavailable|"..tostring(a))
  return failure,nil,"handler_error"
 end
end
local function Bootstrap()
 local pid=Game.GetLocalPlayer();local player=Owner(pid,false)
 if player then Load(player,pid) end
end
BaiqiCreativeIntentGameplay={}
if type(ExposedMembers)=="table" and (ExposedMembers.BaiqiCreativeIntentBridge==nil
 or (type(ExposedMembers.BaiqiCreativeIntentBridge)=="table"
  and ExposedMembers.BaiqiCreativeIntentBridge.marker==MARKER and ExposedMembers.BaiqiCreativeIntentBridge.version==1))
 and Events and Events.GreatWorkCreated then
 ExposedMembers.BaiqiCreativeIntentBridge={version=1,marker=MARKER,
  Inspect=Protected(Inspect,"UNAVAILABLE"),Prepare=Protected(Prepare,false)}
 Events.GreatWorkCreated.Add(Protected(OnCreated,false))
 if GameEvents and GameEvents.OnGameTurnStarted then GameEvents.OnGameTurnStarted.Add(Protected(Bootstrap,false)) end
 if GameEvents and GameEvents.BaiqiRequisitionRecover then GameEvents.BaiqiRequisitionRecover.Add(Protected(Bootstrap,false)) end
 Protected(Bootstrap,false)()
 print("BAIQI|creative_intent_loaded|version=1")
else
 print("BAIQI|creative_intent_unavailable|bridge_conflict_or_event_missing=true")
end
