include("BaiqiConfig")
include("BaiqiFoodTileJournal")
local MARKER="baiqi-food-tile-rescue-v1"
local previous=BaiqiFoodTileIntentGameplay
if previous~=nil then
  local ok,owned=pcall(function()return type(previous)=="table" and previous.marker==MARKER and previous.version==1 end)
  if not ok or not owned then return previous end
end
BaiqiFoodTileIntentGameplay={marker=MARKER,version=1}
local J=BaiqiFoodTileJournal
local bridge
local function Object(v)return type(v)=="table" or type(v)=="userdata" end
local function Method(o,k,...)assert(Object(o) and type(o[k])=="function");return o[k](o,...) end
local function Static(o,k,...)assert(Object(o) and type(o[k])=="function");return o[k](...) end
local function Number(v)return type(v)=="number" and v==v and math.abs(v)<=1000000 end
local function Owner(pid,active)
  if not J.Integer(pid) or type(ExposedMembers)~="table" or ExposedMembers.BaiqiFoodTileRescueBridge~=bridge
    or Static(Game,"GetLocalPlayer")~=pid or Static(GameConfiguration,"IsAnyMultiplayer")~=false
    or (GameConfiguration.IsHotseat and Static(GameConfiguration,"IsHotseat")~=false) then return nil end
  local p,c=Players[pid],PlayerConfigurations[pid]
  local human
  if type(c.IsHuman)=="function" then
    local ok_h, val_h = pcall(function() return c:IsHuman() end)
    if not ok_h or val_h ~= true then return nil end
    human = true
  elseif type(p.IsHuman)=="function" then
    local ok_h, val_h = pcall(function() return p:IsHuman() end)
    if not ok_h or val_h ~= true then return nil end
    human = true
  else
    return nil
  end
  if human~=true or Method(c,"GetLeaderTypeName")~=BaiqiConfig.leader
    or (active and Method(p,"IsTurnActive")~=true)
    or type(p.GetProperty)~="function" or type(p.SetProperty)~="function" then return nil end
  local key=BaiqiConfig.foodTileRescueIntentKey
  if type(key)~="string" or #key<1 or #key>128 then return nil end
  return p,key
end
local function Load(p,pid,key)
  local raw=p:GetProperty(key)
  if raw==nil then return J.New(pid)end
  return J.Clone(raw,pid)
end
local function Persist(p,pid,key,before,after)
  local copy=J.Clone(after,pid)
  if not copy or not J.Equal(before,Load(p,pid,key),pid) then return false end
  p:SetProperty(key,copy)
  return J.Equal(after,p:GetProperty(key),pid)
end
local function City(p,pid,id,x,y)
  local c=Method(Method(p,"GetCities"),"FindID",id)
  if c and Method(c,"GetID")==id and Method(c,"GetOwner")==pid
    and Method(c,"GetX")==x and Method(c,"GetY")==y then return c end
end
local function Plot(op,pid)
  local w,h=Static(Map,"GetGridSize")
  if w~=op.mapWidth or h~=op.mapHeight then return nil end
  local plot=Static(Map,"GetPlotByIndex",op.plotID)
  if plot and Method(plot,"GetIndex")==op.plotID and Method(plot,"GetX")==op.plotX
    and Method(plot,"GetY")==op.plotY and Method(plot,"GetOwner")==pid then return plot end
end
local function PurchaseCity(plot,pid,id,x,y)
  local city=Static(Cities,"GetPlotPurchaseCity",plot)
  return city and Method(city,"GetID")==id and Method(city,"GetOwner")==pid
    and Method(city,"GetX")==x and Method(city,"GetY")==y
end
local function Observe(p,pid,key,state,op)
  if op.stage~="ARMED" then return state end
  local turn=Static(Game,"GetCurrentGameTurn")
  if not J.Integer(turn) or turn<op.turn then return state end
  local city=City(p,pid,op.cityID,op.cityX,op.cityY);local plot=Plot(op,pid)
  if not city or not plot or not PurchaseCity(plot,pid,op.cityID,op.cityX,op.cityY) then return state end
  local surplus=Method(Method(city,"GetGrowth"),"GetFoodSurplus")
  if not Number(surplus) or surplus<0 then return state end
  local source=City(p,pid,op.sourceCityID,op.sourceX,op.sourceY)
  if not source then return state end
  local sourceSurplus=Method(Method(source,"GetGrowth"),"GetFoodSurplus")
  if not Number(sourceSurplus) or sourceSurplus<0 then return state end
  local nextState=J.Clone(state,pid);local record=nextState.records[J.Key(op.cityID)]
  record.stage="OBSERVED";record.observedTurn=turn;record.observedSurplus=surplus
  if not Persist(p,pid,key,state,nextState) then return nil end
  print("BAIQI|food_tile_intent_observed|turn="..turn.."|city="..op.cityID.."|plot="..op.plotID.."|token="..op.token.."|surplus="..surplus)
  return nextState
end
local function Inspect(pid,cityID,token)
  if not J.Integer(cityID) or (token~=nil and (type(token)~="string" or #token>96)) then return "UNKNOWN",token,"invalid_identity" end
  local p,key=Owner(pid,false);if not p then return "UNAVAILABLE",token,"owner_or_bridge" end
  local state=Load(p,pid,key);if not state then return "UNKNOWN",token,"invalid_journal" end
  local op=state.records[J.Key(cityID)]
  if not op then return token==nil and "OPEN" or "UNKNOWN",token,"no_record" end
  if token~=nil and token~=op.token then return "UNKNOWN",token,"token_mismatch" end
  state=Observe(p,pid,key,state,op);if not state then return "UNKNOWN",op.token,"receipt_write_unconfirmed" end
  op=state.records[J.Key(cityID)]
  return op.stage,op.token,"inspected"
end
local function Prepare(pid,cityID,cityX,cityY,sourceID,sourceX,sourceY,plotID,plotX,plotY,turn,expectedFood)
  local p,key=Owner(pid,true);if not p then return false,nil,"owner_or_bridge" end
  local state=Load(p,pid,key);if not state then return false,nil,"invalid_journal" end
  local prior=state.records[J.Key(cityID)]
  if prior and prior.stage=="ARMED" then return false,nil,"prior_unresolved" end
  local count=0
  for _,record in pairs(state.records)do
    count=count+1
    if record.stage=="ARMED" and record.plotID==plotID then return false,nil,"prior_plot_unresolved" end
  end
  if (not prior and count>=128) or state.serial>=2147483647 then return false,nil,"journal_limit" end
  local w,h=Static(Map,"GetGridSize")
  local nextState=J.Clone(state,pid);nextState.serial=nextState.serial+1
  local op={token=J.Token(pid,nextState.serial),sequence=nextState.serial,cityID=cityID,cityX=cityX,cityY=cityY,
    sourceCityID=sourceID,sourceX=sourceX,sourceY=sourceY,plotID=plotID,plotX=plotX,plotY=plotY,
    mapWidth=w,mapHeight=h,turn=turn,stage="ARMED"}
  local keyID=J.Key(cityID);if not keyID then return false,nil,"invalid_identity" end
  nextState.records[keyID]=op
  if not J.Validate(nextState,pid) then return false,nil,"invalid_record" end
  if prior and (prior.cityX~=cityX or prior.cityY~=cityY) then return false,nil,"old_identity_mismatch" end
  local function Eligible()
    local fresh,freshKey=Owner(pid,true)
    if fresh~=p or freshKey~=key or Static(Game,"GetCurrentGameTurn")~=turn then return false end
    local city=City(p,pid,cityID,cityX,cityY);local source=City(p,pid,sourceID,sourceX,sourceY);local plot=Plot(op,pid)
    if not city or not source or not plot or not PurchaseCity(plot,pid,sourceID,sourceX,sourceY) then return false end
    local surplus=Method(Method(city,"GetGrowth"),"GetFoodSurplus")
    local sd=Static(Map,"GetPlotDistance",sourceX,sourceY,plotX,plotY)
    local td=Static(Map,"GetPlotDistance",cityX,cityY,plotX,plotY)
    if not Number(surplus) or surplus>=0 or not J.Integer(sd) or sd<1 or sd>1024
      or not J.Integer(td) or td>3 then return false end
    if sd>3 then return true end
    -- UI includes player yields that Core may omit. Bound the donor by the
    -- fresh UI cost and reject a higher Core cost rather than assuming equality.
    if not Number(expectedFood) or expectedFood<=0 or Method(plot,"GetDistrictType")~=-1 then return false end
    local food=Method(plot,"GetYield",YieldTypes.FOOD)
    local sourceSurplus=Method(Method(source,"GetGrowth"),"GetFoodSurplus")
    return Number(food) and food>=0 and food<=expectedFood
      and Number(sourceSurplus) and sourceSurplus>=expectedFood
  end
  if not Eligible() or not J.Equal(state,Load(p,pid,key),pid) or not Eligible() then return false,nil,"snapshot_changed" end
  if not Persist(p,pid,key,state,nextState) then return false,nil,"intent_write_unconfirmed" end
  print("BAIQI|food_tile_intent_armed|turn="..turn.."|city="..cityID.."|plot="..plotID.."|token="..op.token)
  return true,op.token,"armed"
end
bridge={version=1,marker=MARKER}
function bridge.Inspect(...)
  local ok,a,b,c=pcall(Inspect,...);if ok then return a,b,c end
  return "UNAVAILABLE",nil,"inspect_unavailable"
end
function bridge.Prepare(...)
  local ok,a,b,c=pcall(Prepare,...);if ok then return a,b,c end
  return false,nil,"prepare_unavailable"
end
pcall(function()
  if type(ExposedMembers)~="table" then return end
  local current=ExposedMembers.BaiqiFoodTileRescueBridge
  if current==nil or (type(current)=="table" and current.version==1 and current.marker==MARKER) then ExposedMembers.BaiqiFoodTileRescueBridge=bridge end
end)
return BaiqiFoodTileIntentGameplay
