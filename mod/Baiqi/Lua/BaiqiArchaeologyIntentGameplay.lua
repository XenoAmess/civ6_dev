-- Core metadata only. UI owns native excavation/choice and current UI inventory.
local MARKER="baiqi-archaeology-core-v1"
local previous=BaiqiArchaeologyIntentGameplay
if previous~=nil then
  local ok,owned=pcall(function() return type(previous)=="table" and previous.version==1 and previous.marker==MARKER end)
  if not ok or not owned then return previous end
end
include("BaiqiConfig")
include("BaiqiArchaeologyJournal")
include("BaiqiArchaeologistUnit")
local C,J,U=BaiqiConfig,BaiqiArchaeologyJournal,BaiqiArchaeologistUnit
local KEY=C.archaeologyIntentKey
local MAX=2147483647
local BRIDGE_MARKER="baiqi-archaeology-intent-v1"
local proposalFields={homeCityID=true,cityX=true,cityY=true,buildingIndex=true,x=true,y=true,
  resourceIndex=true,resourceType=true,baselineWorkIDs=true}
local choiceFields={unitID=true,unitType=true,homeCityID=true,x=true,y=true,artifactIndex=true,
  artifactType=true,actingPlayerID=true,choicePlayerID=true,targetPlayerID=true}
local function Object(value) return type(value)=="table" or type(value)=="userdata" end
local function Method(value,name)
  assert(Object(value) and type(value[name])=="function")
  return value[name]
end
local function PlainFields(value,fields)
  if type(value)~="table" or getmetatable(value)~=nil then return false end
  for field in pairs(value) do if not fields[field] then return false end end
  return true
end
local function Owner(pid,active)
  if not J.Integer(pid,MAX) or pid~=Game.GetLocalPlayer() or GameConfiguration.IsAnyMultiplayer()
    or (GameConfiguration.IsHotseat and GameConfiguration.IsHotseat())
    or type(KEY)~="string" or #KEY==0 then return nil end
  local player,config=Players[pid],PlayerConfigurations[pid]
  if not Object(player) or not Object(config) or Method(config,"GetLeaderTypeName")(config)~=C.leader then return nil end
  local human
  if type(config.IsHuman)=="function" then human=config:IsHuman()
  elseif type(player.IsHuman)=="function" then human=player:IsHuman() end
  if human~=true or (active and Method(player,"IsTurnActive")(player)~=true)
    or type(player.GetProperty)~="function" or type(player.SetProperty)~="function" then return nil end
  return player
end
local function Turn()
  local value=Game.GetCurrentGameTurn()
  if J.Integer(value,MAX) then return value end
end
local function Load(player,pid)
  local raw=player:GetProperty(KEY)
  if raw==nil then return J.New(pid),true end
  return J.Clone(raw,pid),false
end
local function Persist(player,pid,before,wasNil,after)
  if not J.Validate(after,pid) then return false end
  local current=player:GetProperty(KEY)
  if wasNil then
    if current~=nil then return false end
  elseif not J.Equal(before,current,pid) then return false end
  player:SetProperty(KEY,after)
  return J.Equal(after,player:GetProperty(KEY),pid)
end
local function Museum(pid,op)
  local player=Players[pid]
  local cities=Method(player,"GetCities")(player)
  local city=Method(cities,"FindID")(cities,op.homeCityID)
  if Method(city,"GetID")(city)~=op.homeCityID or Method(city,"GetOwner")(city)~=pid
    or Method(city,"GetX")(city)~=op.cityX or Method(city,"GetY")(city)~=op.cityY then return nil end
  local row=GameInfo.Buildings.BUILDING_MUSEUM_ARTIFACT
  if not Object(row) or row.BuildingType~="BUILDING_MUSEUM_ARTIFACT" or row.Index~=op.buildingIndex then return nil end
  local buildings=Method(city,"GetBuildings")(city)
  if Method(buildings,"HasBuilding")(buildings,row.Index)~=true then return nil end
  return city
end
local function Facts(pid,id,op,excavating)
  local player=Owner(pid,true)
  if not player then return nil end
  local live=U.Read(player,pid,id)
  if not live or live.unitID~=id or live.unitType~="UNIT_ARCHAEOLOGIST"
    or live.x~=op.x or live.y~=op.y or live.formation~=1 or (excavating and live.moves<=0)
    or not Museum(pid,op) then return nil end
  local vis=PlayersVisibility[pid]
  if Method(vis,"IsRevealed")(vis,op.x,op.y)~=true or Method(vis,"IsVisible")(vis,op.x,op.y)~=true then return nil end
  local plot=Map.GetPlot(op.x,op.y)
  if Method(plot,"GetX")(plot)~=op.x or Method(plot,"GetY")(plot)~=op.y
    or Method(plot,"GetOwner")(plot)~=pid then return nil end
  local index=Method(plot,"GetResourceType")(plot)
  if not excavating and index==-1 then return player end
  if index~=op.resourceIndex then return nil end
  local row=GameInfo.Resources[index]
  if not Object(row) or row.ResourceType~=op.resourceType then return nil end
  return player
end
local function Busy(state)
  for _,op in pairs(state.operations) do if op.stage~="OBSERVED" then return true end end
  return false
end
local function Count(value)
  local count=0;for _ in pairs(value) do count=count+1 end;return count
end
local function PrepareExcavation(pid,id,proposal)
  local player=Owner(pid,true)
  local key=J.UnitKey(id)
  if not player or not key or not PlainFields(proposal,proposalFields) then return false,nil,"owner_or_proposal" end
  local state,wasNil=Load(player,pid)
  if not state or Busy(state) then return false,nil,"journal_or_unresolved" end
  local prior=state.operations[key]
  if state.serial>=MAX or (not prior and Count(state.operations)>=256)
    or (prior and Count(prior.works)>=64) then return false,nil,"journal_limit" end
  local at=Turn()
  if not at then return false,nil,"turn" end
  local nextState=J.Clone(state,pid);nextState.serial=nextState.serial+1
  local op={unitID=id,unitType="UNIT_ARCHAEOLOGIST",sequence=nextState.serial,
    token=J.Token(pid,nextState.serial),stage="EXCAVATE_ARMED",turn=at,works={}}
  for field in pairs(proposalFields) do op[field]=proposal[field] end
  if prior then for work in pairs(prior.works) do op.works[work]=true end end
  nextState.operations[key]=op
  nextState=J.Clone(nextState,pid)
  if not nextState then return false,nil,"proposal_schema" end
  op=nextState.operations[key]
  if not Facts(pid,id,op,true) or Turn()~=at then return false,nil,"facts_changed" end
  local fresh=Facts(pid,id,op,true)
  if not fresh or Turn()~=at then return false,nil,"facts_changed" end
  if not Persist(fresh,pid,state,wasNil,nextState) then return false,nil,"persist_unconfirmed" end
  return true,op.token,"persisted"
end
local function PrepareChoice(pid,id,token,descriptor)
  local player=Owner(pid,true);local key=J.UnitKey(id)
  if not player or not key or type(token)~="string" or not PlainFields(descriptor,choiceFields) then return false,nil,"owner_or_descriptor" end
  local state,wasNil=Load(player,pid)
  local op=state and state.operations[key]
  if not op or op.stage~="EXCAVATE_ARMED" or op.token~=token then return false,nil,"prior_intent" end
  if descriptor.unitID~=id or descriptor.unitType~=op.unitType or descriptor.homeCityID~=op.homeCityID
    or descriptor.x~=op.x or descriptor.y~=op.y then return false,nil,"descriptor_identity" end
  local at=Turn()
  if not at or at<op.turn then return false,nil,"turn" end
  local after=J.Clone(state,pid);local nextOp=after.operations[key]
  nextOp.stage="CHOICE_ARMED";nextOp.choiceTurn=at
  for _,field in ipairs({"artifactIndex","artifactType","actingPlayerID","choicePlayerID","targetPlayerID"}) do nextOp[field]=descriptor[field] end
  if not J.Validate(after,pid) then return false,nil,"descriptor_schema" end
  if not Facts(pid,id,nextOp,false) or Turn()~=at then return false,nil,"facts_changed" end
  local fresh=Facts(pid,id,nextOp,false)
  if not fresh or Turn()~=at then return false,nil,"facts_changed" end
  if not Persist(fresh,pid,state,wasNil,after) then return false,nil,"persist_unconfirmed" end
  return true,token,"persisted"
end
local function Inspect(pid,id)
  local player=Owner(pid,false);local key=J.UnitKey(id)
  if not player or not key then return "UNAVAILABLE",nil,"owner_or_id" end
  local state=Load(player,pid)
  if not state then return "UNAVAILABLE",nil,"journal_unavailable" end
  local op=state.operations[key]
  if op then return op.stage,op.token,"saved_intent" end
  if Busy(state) then return "BUSY",nil,"other_unresolved" end
  return "OPEN",nil,"no_prior_intent"
end
local function ObserveCreated(pid,id,x,y,building,work)
  local player=Owner(pid,false);local key=J.UnitKey(id)
  if not player or not key or not J.Integer(x,MAX) or not J.Integer(y,MAX)
    or not J.Integer(building,MAX) or not J.Integer(work,MAX) then return false end
  local state,wasNil=Load(player,pid);local op=state and state.operations[key]
  if not op or op.stage~="CHOICE_ARMED" or op.cityX~=x or op.cityY~=y or op.buildingIndex~=building
    or Count(op.works)>=64 or not Museum(pid,op) then return false end
  for _,known in ipairs(op.baselineWorkIDs) do if known==work then return false end end
  local workKey=J.UnitKey(work)
  for _,record in pairs(state.operations) do if record.works[workKey] then return false end end
  local after=J.Clone(state,pid);local nextOp=after.operations[key]
  nextOp.works[workKey]=true;nextOp.newWorkID=work;nextOp.stage="OBSERVED"
  local fresh=Owner(pid,false)
  if not fresh or not Museum(pid,nextOp) then return false end
  return Persist(fresh,pid,state,wasNil,after)
end
local function Protected(fn,failure)
  return function(...)
    local ok,a,b,c=pcall(fn,...)
    if ok then return a,b,c end
    return failure,nil,"handler_error"
  end
end
local bridge={version=1,marker=BRIDGE_MARKER,PrepareExcavation=Protected(PrepareExcavation,false),
  PrepareChoice=Protected(PrepareChoice,false),Inspect=Protected(Inspect,"UNAVAILABLE")}
local function ProtectedObservation(...)
  local ok,observed=pcall(ObserveCreated,...)
  return ok and observed==true
end
local module={version=1,marker=MARKER,bridge=bridge,ObserveCreated=ProtectedObservation}
BaiqiArchaeologyIntentGameplay=module
pcall(function()
  if type(ExposedMembers)~="table" then return end
  local prior=ExposedMembers.BaiqiArchaeologyBridge
  if prior==nil or (type(prior)=="table" and prior.version==1 and prior.marker==BRIDGE_MARKER) then
    ExposedMembers.BaiqiArchaeologyBridge=bridge
  end
end)
return module
