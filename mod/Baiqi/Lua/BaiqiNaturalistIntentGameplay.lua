-- Core metadata permission precedes the executor's one park operation.
if BaiqiNaturalistIntentGameplay then return end
include("BaiqiConfig")
include("BaiqiNaturalistJournal")
include("BaiqiNaturalistUnit")
local J,U,C=BaiqiNaturalistJournal,BaiqiNaturalistUnit,BaiqiConfig
local KEY=C.naturalistIntentKey
local MARKER="baiqi-naturalist-intent-v1"

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
    or type(player.GetProperty)~="function" or type(player.SetProperty)~="function"
    or type(KEY)~="string" then return nil end
  return player
end

local function Persist(player,pid,state)
  if not J.Validate(state,pid) then return false end
  player:SetProperty(KEY,state)
  return J.Equal(state,player:GetProperty(KEY),pid)
end

local function Load(player,pid)
  local raw=player:GetProperty(KEY)
  if raw~=nil then return J.Clone(raw,pid) end
  -- Older versions never issued naturalist actions. This new feature starts
  -- empty; malformed/unknown existing data is never reset or migrated to OPEN.
  local state=J.New(pid)
  if Persist(player,pid,state) then return state end
end

local function OwnedVisiblePlot(pid,x,y)
  if not J.Integer(x,2147483647) or not J.Integer(y,2147483647) then return nil end
  local visibility=PlayersVisibility[pid]
  if not visibility or visibility:IsRevealed(x,y)~=true or visibility:IsVisible(x,y)~=true then return nil end
  local plot=Map.GetPlot(x,y)
  if not plot or plot:GetX()~=x or plot:GetY()~=y or plot:GetOwner()~=pid
    or type(plot.IsNationalPark)~="function" then return nil end
  return plot
end

local function Reconcile(player,pid,state,op)
  if op.stage=="ARMED" then
    local plot=OwnedVisiblePlot(pid,op.x,op.y)
    -- A consumed/missing unit or timeout does not prove the park exists.
    if plot and plot:IsNationalPark()==true then
      op.stage="OBSERVED"
      if not Persist(player,pid,state) then return false,"persist_unconfirmed" end
    end
  end
  return true,op.stage
end

local function Inspect(pid,id)
  local player=Owner(pid,false)
  if not player or not J.UnitKey(id) then return "UNAVAILABLE",nil,"owner_or_id" end
  local state=Load(player,pid)
  if not state then return "UNAVAILABLE",nil,"journal_unavailable" end
  local op=state.operations[J.UnitKey(id)]
  if not op then return "OPEN",nil,"no_prior_intent" end
  local ok,why=Reconcile(player,pid,state,op)
  if not ok then return "UNAVAILABLE",op.token,why end
  return op.stage,op.token,why
end

local function Prepare(pid,id,charges,x,y)
  local player=Owner(pid,true)
  if not player or not J.Integer(charges,1000000) or charges<1 then return false,nil,"owner_or_charges" end
  local state=Load(player,pid)
  if not state then return false,nil,"journal_unavailable" end
  local live=U.Read(player,pid,id)
  if not live or live.charges~=charges or live.x~=x or live.y~=y
    or live.moves<=0 or live.formation~=1 then return false,nil,"unit_changed" end
  local plot=OwnedVisiblePlot(pid,x,y)
  if not plot or plot:IsNationalPark()~=false then return false,nil,"target_changed" end
  local key=J.UnitKey(id)
  local prior=state.operations[key]
  if prior then
    local ok=Reconcile(player,pid,state,prior)
    if not ok or prior.stage~="OBSERVED" or live.charges>=prior.charges then
      return false,prior.token,"prior_intent"
    end
  end
  local count=0
  for otherKey,op in pairs(state.operations) do
    count=count+1
    if otherKey~=key and op.stage=="ARMED" and op.x==x and op.y==y then
      return false,nil,"target_reserved"
    end
  end
  local current=Game.GetCurrentGameTurn()
  if state.serial>=2147483647 or (not prior and count>=256)
    or not J.Integer(current,2147483647) then return false,nil,"journal_limit" end
  state.serial=state.serial+1
  local op={token=J.Token(pid,state.serial),sequence=state.serial,unitID=id,
    unitType="UNIT_NATURALIST",charges=charges,x=x,y=y,turn=current,stage="ARMED"}
  state.operations[key]=op
  if not Persist(player,pid,state) then return false,nil,"persist_unconfirmed" end
  return true,op.token,"persisted"
end

local function Protected(fn,failure)
  return function(...)
    local ok,a,b,c=pcall(fn,...)
    if ok then return a,b,c end
    print("BAIQI|naturalist_intent_unavailable|"..tostring(a))
    return failure,nil,"handler_error"
  end
end
local bridge={version=1,marker=MARKER,Inspect=Protected(Inspect,"UNAVAILABLE"),Prepare=Protected(Prepare,false)}
BaiqiNaturalistIntentGameplay={}
local function Bootstrap()
  local pid=Game.GetLocalPlayer()
  local player=Owner(pid,false)
  if player then Load(player,pid) end
end
if type(ExposedMembers)=="table" and (ExposedMembers.BaiqiNaturalistIntentBridge==nil
  or (type(ExposedMembers.BaiqiNaturalistIntentBridge)=="table"
    and ExposedMembers.BaiqiNaturalistIntentBridge.marker==MARKER
    and ExposedMembers.BaiqiNaturalistIntentBridge.version==1)) then
  ExposedMembers.BaiqiNaturalistIntentBridge=bridge
  if GameEvents and GameEvents.OnGameTurnStarted then GameEvents.OnGameTurnStarted.Add(Protected(Bootstrap,false)) end
  if GameEvents and GameEvents.BaiqiRequisitionRecover then GameEvents.BaiqiRequisitionRecover.Add(Protected(Bootstrap,false)) end
  Protected(Bootstrap,false)()
  print("BAIQI|naturalist_intent_loaded|version=1")
else
  print("BAIQI|naturalist_intent_unavailable|bridge_conflict=true")
end
