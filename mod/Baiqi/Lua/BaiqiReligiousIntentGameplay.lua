-- Core persists permission before the UI's sole native spread request.
if BaiqiReligiousIntentGameplay then return end
include("BaiqiReligiousJournal")
local J,C=BaiqiReligiousJournal,BaiqiConfig
local KEY=C.religiousIntentKey
local MARKER="baiqi-religious-intent-v1"
local function Owner(pid,active)
  if type(KEY)~="string" or #KEY==0 or #KEY>128
    or not J.Integer(pid,2147483647) or pid~=Game.GetLocalPlayer()
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
-- Candidate138's Core religion-component snapshot, with owner-added checks for
-- missing required native members. Zero charges/moves remain valid readbacks.
local function ReadMissionary(player,pid,id)
  if not J.Integer(id,2147483647) then return nil end
  local unit=player:GetUnits():FindID(id)
  if not unit then return nil end
  for _,name in ipairs({"GetID","GetOwner","GetX","GetY","GetMovesRemaining"}) do
    if type(unit[name])~="function" then return nil end
  end
  if unit:GetID()~=id or unit:GetOwner()~=pid then return nil end
  local index
  if type(unit.GetType)~="function" then return nil end
  index=unit:GetType()
  local def=index~=nil and GameInfo.Units[index]
  if not def or def.UnitType~="UNIT_MISSIONARY" then return nil end
  if type(unit.GetReligion)~="function" then return nil end
  local religion=unit:GetReligion()
  if not religion or type(religion.GetReligionType)~="function" or type(religion.GetSpreadCharges)~="function" then return nil end
  local religionID=religion:GetReligionType()
  local charges=religion:GetSpreadCharges()
  if not J.Integer(religionID,2147483647) or not J.Integer(charges,1000000) then return nil end
  local x,y=unit:GetX(),unit:GetY()
  if not J.Integer(x,2147483647) or not J.Integer(y,2147483647) then return nil end
  local moves=unit:GetMovesRemaining()
  if not BaiqiPolicy.Number(moves) or moves<0 then return nil end
  local formation
  if type(unit.GetFormationUnitCount)=="function" then formation=unit:GetFormationUnitCount() end
  if not J.Integer(formation,64) or formation<1 then return nil end
  return {id=id,unitType="UNIT_MISSIONARY",religion=religionID,charges=charges,x=x,y=y,moves=moves,formation=formation}
end
local function Persist(player,pid,state)
  if not J.Validate(state,pid) then return false end
  player:SetProperty(KEY,state)
  return J.Equal(state,player:GetProperty(KEY),pid)
end
local function Entry(pid,state,live,stage,city)
  if state.serial>=2147483647 or not J.Integer(Game.GetCurrentGameTurn(),2147483647) then return nil end
  local count=0;for _ in pairs(state.operations) do count=count+1 end
  local key=J.UnitKey(live.id)
  if not key or (not state.operations[key] and count>=256) then return nil end
  state.serial=state.serial+1
  local op={token=J.Token(pid,state.serial),sequence=state.serial,unitID=live.id,unitType=live.unitType,
    religion=live.religion,charges=live.charges,x=live.x,y=live.y,turn=Game.GetCurrentGameTurn(),stage=stage}
  if city then op.cityID=city:GetID();op.cityX=city:GetX();op.cityY=city:GetY() end
  state.operations[key]=op
  return op
end
local function Load(player,pid)
  local raw=player:GetProperty(KEY)
  if raw~=nil then return J.Clone(raw,pid) end
  local state=J.New(pid)
  for _,unit in player:GetUnits():Members() do
    local index=type(unit.GetType)=="function" and unit:GetType()
    local def=index~=nil and GameInfo.Units[index]
    if def and def.UnitType=="UNIT_MISSIONARY" then
      local live=ReadMissionary(player,pid,unit:GetID())
      if not live then return nil end
      if live.charges>0 and not Entry(pid,state,live,"LEGACY_UNKNOWN") then return nil end
    end
  end
  if Persist(player,pid,state) then return state end
end
local function Same(op,live)
  return live and live.id==op.unitID and live.unitType==op.unitType and live.religion==op.religion
end
local function Reconcile(player,pid,state,op,live)
  -- A missing unit, timeout or generic segment event does not prove spread.
  -- The actual native experiment emitted no segment event. Never fabricate it.
  if op.stage=="ARMED" and Same(op,live) and live.charges<op.charges then
    op.stage="OBSERVED"
    if not Persist(player,pid,state) then return false,"persist_unconfirmed" end
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
  local ok,reason=Reconcile(player,pid,state,op,ReadMissionary(player,pid,id))
  if not ok then return "UNAVAILABLE",op.token,reason end
  return op.stage,op.token,reason
end
local function Prepare(pid,id,religion,charges,x,y,cityID)
  local player=Owner(pid,true)
  if not player then return false,nil,"owner" end
  local state=Load(player,pid)
  if not state then return false,nil,"journal_unavailable" end
  local live=ReadMissionary(player,pid,id)
  if not live or live.religion~=religion or live.charges~=charges or charges<=0
    or live.x~=x or live.y~=y or live.moves<=0 or live.formation~=1
    or not J.Integer(cityID,2147483647) then return false,nil,"unit_changed" end
  local city=player:GetCities():FindID(cityID)
  if not BaiqiPolicy.MatchesID(city,cityID) or city:GetOwner()~=pid or city:GetX()~=x or city:GetY()~=y then
    return false,nil,"city_or_position_changed"
  end
  local visibility=PlayersVisibility[pid]
  local pr,cr=player:GetReligion(),city:GetReligion()
  if not visibility or not pr or not cr or not BaiqiPolicy.MissionaryTarget(pid,pr:GetReligionTypeCreated(),
    live.religion,city:GetOwner(),cr:GetMajorityReligion(),visibility:IsRevealed(x,y),visibility:IsVisible(x,y)) then
    return false,nil,"domestic_target_changed"
  end
  local prior=state.operations[J.UnitKey(id)]
  if prior then
    local ok=Reconcile(player,pid,state,prior,live)
    if not ok or prior.stage~="OBSERVED" or not Same(prior,live) or live.charges>=prior.charges then
      return false,prior.token,"prior_intent"
    end
  end
  local op=Entry(pid,state,live,"ARMED",city)
  if not op or not Persist(player,pid,state) then return false,nil,"persist_unconfirmed" end
  return true,op.token,"persisted"
end
local function Protected(fn,failure)
  return function(...)
    local ok,a,b,c=pcall(fn,...)
    if ok then return a,b,c end
    print("BAIQI|religious_intent_unavailable|"..tostring(a))
    return failure,nil,"handler_error"
  end
end
local bridge={version=1,marker=MARKER,Inspect=Protected(Inspect,"UNAVAILABLE"),Prepare=Protected(Prepare,false)}
BaiqiReligiousIntentGameplay={}
-- Freeze legacy actors before a permitted new purchase can appear. Existing
-- ARMED/LEGACY_UNKNOWN entries remain unchanged; this never issues a command.
local Initialize=Protected(function(pid)
  if type(ExposedMembers)~="table" or ExposedMembers.BaiqiReligiousIntentBridge~=bridge then return false end
  local player=Owner(pid,false)
  return player~=nil and Load(player,pid)~=nil
end,false)
function BaiqiReligiousIntentGameplay.Initialize(pid)
  local result=Initialize(pid)
  return result==true
end
local function Bootstrap()
  local pid=Game.GetLocalPlayer()
  local player=Owner(pid,false)
  if player then Load(player,pid) end
end
if type(ExposedMembers)=="table" and (ExposedMembers.BaiqiReligiousIntentBridge==nil
  or (type(ExposedMembers.BaiqiReligiousIntentBridge)=="table"
    and ExposedMembers.BaiqiReligiousIntentBridge.marker==MARKER
    and ExposedMembers.BaiqiReligiousIntentBridge.version==1)) then
  ExposedMembers.BaiqiReligiousIntentBridge=bridge
  if GameEvents and GameEvents.OnGameTurnStarted then GameEvents.OnGameTurnStarted.Add(Protected(Bootstrap,false)) end
  if GameEvents and GameEvents.BaiqiRequisitionRecover then GameEvents.BaiqiRequisitionRecover.Add(Protected(Bootstrap,false)) end
  Protected(Bootstrap,false)()
  print("BAIQI|religious_intent_loaded|version=1")
else
  print("BAIQI|religious_intent_unavailable|bridge_conflict=true")
end
