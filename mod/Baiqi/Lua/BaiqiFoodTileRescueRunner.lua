-- The executor provides original ports, never the read-only player UI facade.
-- Core persists permission before one native submission. Reloaded ARMED records
-- only observe; they never become a new permission to send.
include("BaiqiFoodTileRescue")
BaiqiFoodTileRescueRunner={}
local pending,attempted={},{}
local running=false
local function Int(v,lo,hi)return type(v)=="number" and v==v and v>=lo and v<=hi and v%1==0 end
local function ID(v)return Int(v,0,2147483647) end
local function Finite(v)return type(v)=="number" and v==v and math.abs(v)<=1000000 end
local function Obj(v)return type(v)=="table" or type(v)=="userdata" end
local function Method(o,k,...)assert(Obj(o) and type(o[k])=="function");return o[k](o,...) end
local function Static(o,k,...)assert(Obj(o) and type(o[k])=="function");return o[k](...) end
local function Player(E,pid,turn)
  if Static(E.Game,"GetLocalPlayer")~=pid or Static(E.Game,"GetCurrentGameTurn")~=turn
    or Static(E.GameConfiguration,"IsAnyMultiplayer")~=false
    or (E.GameConfiguration.IsHotseat and Static(E.GameConfiguration,"IsHotseat")~=false)
    or Static(E.Game,"IsAllowStrategicCommands",pid)~=true
    or Static(E.UI,"IsGameCoreBusy")~=false or Static(E.UI,"IsProcessingMessages")~=false then return nil end
  local p,c=E.Players[pid],E.PlayerConfigurations[pid]
  if Method(p,"IsTurnActive")==true and Method(c,"IsHuman")==true
    and Method(c,"GetLeaderTypeName")==E.leader then return p end
end
local function Identity(c,pid)
  assert(Method(c,"GetOwner")==pid)
  local s={id=Method(c,"GetID"),x=Method(c,"GetX"),y=Method(c,"GetY")}
  assert(ID(s.id) and ID(s.x) and ID(s.y));return s
end
local function SameCity(a,b)return a.id==b.id and a.x==b.x and a.y==b.y end
local function Tokens(E)
  local t={}
  for _,k in ipairs({"MANAGE","SWAP_TILE_OWNER","PARAM_MANAGE_CITIZEN","PARAM_SWAP_TILE_OWNER","PARAM_X","PARAM_Y"}) do
    local v=E.CityCommandTypes[k];assert(type(v)=="number" or type(v)=="string");t[k]=v
  end
  assert(t.PARAM_X~=t.PARAM_Y and t.PARAM_X~=t.PARAM_SWAP_TILE_OWNER and t.PARAM_Y~=t.PARAM_SWAP_TILE_OWNER)
  return t
end
local function Params(E,key)
  local v=Static(E.UI,"GetInterfaceModeParameter",key)
  assert(v==nil or type(v)=="boolean" or type(v)=="string" or Finite(v) or Int(v,-2147483648,2147483647))
  local p={};if v~=nil then p[key]=v end;return p
end
local function Plots(E,r,key)
  local a=r and r[E.CityCommandResults[key]];assert(type(a)=="table");return a
end
local function Manage(E,c,t)
  local r=Static(E.CityManager,"GetCommandTargets",c,t.MANAGE,Params(E,t.PARAM_MANAGE_CITIZEN))
  local plots,counts,locked=Plots(E,r,"PLOTS"),Plots(E,r,"CITIZENS"),Plots(E,r,"LOCKED_CITIZENS")
  local found,n={},0
  for key,id in pairs(plots) do
    n=n+1;assert(n<=128 and ID(id) and found[id]==nil)
    local a,b=counts[key],locked[key];assert(Int(a,-1,256) and Int(b,-1,256))
    found[id]={count=a,locked=b}
  end
  return found
end
local function Ownership(E,own,pid)
  local expected=Method(own,"GetCount");assert(Int(expected,1,128))
  local cityPlots=Static(E.Map,"GetCityPlots");local cities,purchased={},{};local n=0
  for _,c in own:Members() do
    n=n+1;assert(n<=128);local s=Identity(c,pid);assert(not cities[s.id]);s.city=c;cities[s.id]=s
    local plots=Method(cityPlots,"GetPurchasedPlots",c);assert(type(plots)=="table");local count=0
    for _,id in pairs(plots) do
      count=count+1;assert(count<=128 and ID(id) and purchased[id]==nil);purchased[id]=s.id
    end
  end
  assert(n==expected and Method(own,"GetCount")==expected)
  return cities,purchased
end
local function Snapshot(E,own,c,pid,t)
  local identity=Identity(c,pid);local growth,citizens=Method(c,"GetGrowth"),Method(c,"GetCitizens")
  local s={player=pid,owner=pid,cityID=identity.id,population=Method(c,"GetPopulation"),
    surplus=Method(growth,"GetFoodSurplus"),starvation=Method(growth,"GetTurnsUntilStarvation"),
    favored=Method(citizens,"IsFavoredYield",E.YieldTypes.FOOD),disfavored=Method(citizens,"IsDisfavoredYield",E.YieldTypes.FOOD)}
  assert(Finite(s.surplus))
  if s.surplus>=0 or s.favored~=true or s.disfavored~=false or not Int(s.starvation,1,10000) then return nil end
  s.mapWidth,s.mapHeight=Static(E.Map,"GetGridSize");assert(Int(s.mapWidth,1,512) and Int(s.mapHeight,1,512))
  local cities,purchased=Ownership(E,own,pid);assert(cities[s.cityID] and SameCity(identity,cities[s.cityID]))
  local works=Manage(E,c,t);s.zeroFoodSpecialists=0
  for id,r in pairs(works) do
    if r.count>0 and r.locked==0 then
      local plot=Static(E.Map,"GetPlotByIndex",id);assert(plot and Method(plot,"GetOwner")==pid)
      if Method(plot,"GetDistrictType")>=0 and Method(plot,"GetYield",E.YieldTypes.FOOD)==0 then
        s.zeroFoodSpecialists=s.zeroFoodSpecialists+r.count
      end
    end
  end
  if s.zeroFoodSpecialists<1 then return nil end
  local r=Static(E.CityManager,"GetCommandTargets",c,t.SWAP_TILE_OWNER,Params(E,t.PARAM_SWAP_TILE_OWNER))
  local targets=Plots(E,r,"PLOTS");s.targets={};local seen,n={},0;local vis=E.PlayersVisibility[pid]
  for _,id in pairs(targets) do
    n=n+1;assert(n<=128 and ID(id) and not seen[id]);seen[id]=true
    local plot=Static(E.Map,"GetPlotByIndex",id);assert(plot)
    local x,y=Method(plot,"GetX"),Method(plot,"GetY")
    if Method(plot,"GetOwner")==pid and Method(vis,"IsVisible",x,y)==true and Method(vis,"IsRevealed",x,y)==true then
      local source=assert(cities[purchased[id]])
      if source.id~=s.cityID then
        source.manage=source.manage or Manage(E,source.city,t)
        local w=source.manage[id];local q=Params(E,t.PARAM_SWAP_TILE_OWNER);q[t.PARAM_X]=x;q[t.PARAM_Y]=y
        local allowed=Static(E.CityManager,"CanStartCommand",c,t.SWAP_TILE_OWNER,q);assert(type(allowed)=="boolean")
        s.targets[#s.targets+1]={plotID=id,x=x,y=y,food=Method(plot,"GetYield",E.YieldTypes.FOOD),
          sourceCityID=source.id,sourcePopulation=Method(source.city,"GetPopulation"),sourceSurplus=Method(Method(source.city,"GetGrowth"),"GetFoodSurplus"),
          sourceManageHasPlot=w~=nil,sourceManageComplete=true,sourceWorked=w and w.count,sourceLocked=w and w.locked,
          district=Method(plot,"GetDistrictType"),improvement=Method(plot,"GetImprovementType"),nativeAllowed=allowed,
          sourceDistance=Static(E.Map,"GetPlotDistance",source.x,source.y,x,y),targetDistance=Static(E.Map,"GetPlotDistance",identity.x,identity.y,x,y),
          owner=pid,visible=true,revealed=true,sourceX=source.x,sourceY=source.y}
      end
    end
  end
  s.complete=true;return s,identity
end
local function Plan(s)return s and BaiqiFoodTileRescue.Plan(s) end
local function Equal(a,b)
  if not a or not b then return false end
  for _,k in ipairs({"cityID","sourceCityID","plotID","x","y","expectedFood","expectedSurplus"}) do if a[k]~=b[k] then return false end end
  return true
end
local function Bridge(E)
  local b=type(E.ExposedMembers)=="table" and E.ExposedMembers.BaiqiFoodTileRescueBridge
  if type(b)=="table" and b.version==1 and b.marker=="baiqi-food-tile-rescue-v1"
    and type(b.Prepare)=="function" and type(b.Inspect)=="function" then return b end
end
local function Call(b,method,...)
  local ok,a,c,d=pcall(b[method],...);if ok then return a,c,d end
  return nil,nil,"bridge_unavailable"
end
local function Source(s,plan)
  for _,row in ipairs(s.targets)do
    if row.plotID==plan.plotID and row.sourceCityID==plan.sourceCityID
      and Int(row.sourceX,0,s.mapWidth-1) and Int(row.sourceY,0,s.mapHeight-1) then return row.sourceX,row.sourceY end
  end
end
local deniedBeforePersist={owner_or_bridge=true,invalid_journal=true,prior_unresolved=true,prior_plot_unresolved=true,
  journal_limit=true,invalid_identity=true,invalid_record=true,old_identity_mismatch=true,snapshot_changed=true,same_plot=true}
local function City(E,pid,turn,player,own,c,t)
  local identity=Identity(c,pid);local held=pending[identity.id];local b=Bridge(E);if not b then return false end
  local prepare,inspect=b.Prepare,b.Inspect
  local stage,token=Call(b,"Inspect",pid,identity.id,held and held.token)
  if held then
    if held.player~=pid or not SameCity(held,identity) then return false end
    if held.token==nil or (stage~="OBSERVED" and stage~="TRANSFERRED") or token~=held.token then return false end
    if stage=="OBSERVED" then
      print("BAIQI|food_tile_rescue_observed|turn="..turn.."|city="..identity.id.."|plot="..held.plotID.."|token="..token.."|receipt=CORE_OBSERVED")
    else
      print("BAIQI|food_tile_rescue_partial_transfer|turn="..turn.."|city="..identity.id.."|plot="..held.plotID.."|token="..token.."|receipt=CORE_TRANSFERRED")
    end
    pending[identity.id]=nil
  end
  if stage~="OPEN" and stage~="OBSERVED" and stage~="TRANSFERRED" then return false end
  if stage=="OPEN" and token~=nil then return false end
  if (stage=="OBSERVED" or stage=="TRANSFERRED") and (type(token)~="string" or #token==0 or #token>96) then return false end
  local last=attempted[identity.id]
  if last and last.turn==turn and last.token==token then return false end
  local yield=E.YieldTypes.FOOD
  local s=Snapshot(E,own,c,pid,t);local plan=Plan(s);if not plan then return false end
  local sourceX,sourceY=Source(s,plan);if sourceX==nil then return false end
  local manager=E.CityManager;local qualifier,writer=manager.CanStartCommand,manager.RequestCommand
  assert(type(qualifier)=="function" and type(writer)=="function")
  local params=Params(E,t.PARAM_SWAP_TILE_OWNER);params[t.PARAM_X]=plan.x;params[t.PARAM_Y]=plan.y
  if qualifier(c,t.SWAP_TILE_OWNER,params)~=true then return false end
  -- Hold even an uncertain Prepare reply locally. It never authorizes a city
  -- command; on reload the actual durable record is inspected afresh.
  local hold={player=pid,id=identity.id,x=identity.x,y=identity.y,plotID=plan.plotID}
  pending[identity.id]=hold;attempted[identity.id]={turn=turn,token=token}
  local granted,newToken,why=Call(b,"Prepare",pid,identity.id,identity.x,identity.y,
    plan.sourceCityID,sourceX,sourceY,plan.plotID,plan.x,plan.y,turn,plan.expectedFood)
  if granted~=true or type(newToken)~="string" or #newToken==0 or #newToken>96 or why~="armed" then
    if granted==false and deniedBeforePersist[why] then pending[identity.id]=nil end
    return false
  end
  hold.token=newToken
  local armed,storedToken=Call(b,"Inspect",pid,identity.id,newToken)
  if armed~="ARMED" or storedToken~=newToken then return false end
  local fresh=Method(own,"FindID",identity.id);assert(fresh and SameCity(identity,Identity(fresh,pid)))
  local again=Snapshot(E,own,fresh,pid,t);local nextPlan=Plan(again)
  local freshSourceX,freshSourceY;if nextPlan then freshSourceX,freshSourceY=Source(again,nextPlan)end
  if not Equal(plan,nextPlan) or s.surplus~=again.surplus or s.population~=again.population or s.starvation~=again.starvation
    or sourceX~=freshSourceX or sourceY~=freshSourceY or E.YieldTypes.FOOD~=yield
    or Player(E,pid,turn)~=player or E.CityManager~=manager or manager.CanStartCommand~=qualifier or manager.RequestCommand~=writer
    or Bridge(E)~=b or b.Prepare~=prepare or b.Inspect~=inspect then return false end
  local freshTokens=Tokens(E);for k,v in pairs(t) do if freshTokens[k]~=v then return false end end
  local finalParams=Params(E,t.PARAM_SWAP_TILE_OWNER);finalParams[t.PARAM_X]=plan.x;finalParams[t.PARAM_Y]=plan.y
  for k,v in pairs(params) do if finalParams[k]~=v then return false end end
  for k,v in pairs(finalParams) do if params[k]~=v then return false end end
  -- The fresh successful Prepare above is the sole send grant. Old ARM at load,
  -- false/void/throwing submission and post-arm abort never grant another send.
  print("BAIQI|food_tile_rescue_request|turn="..turn.."|city="..identity.id.."|source=BACKGROUND|fromCity="..plan.sourceCityID.."|plot="..plan.plotID.."|token="..newToken.."|predicted="..plan.expectedSurplus)
  pcall(writer,fresh,t.SWAP_TILE_OWNER,params)
  return true
end
function BaiqiFoodTileRescueRunner.Run(E,pid)
  if running then return end;running=true
  pcall(function()
    if type(E)~="table" or getmetatable(E)~=nil or not ID(pid) then return end
    local turn=Static(E.Game,"GetCurrentGameTurn");if not ID(turn) then return end
    local player=Player(E,pid,turn);if not player or not ID(E.YieldTypes.FOOD) then return end
    local t=Tokens(E);local own=Method(player,"GetCities");local count=Method(own,"GetCount")
    if not Int(count,1,128) then return end
    local list,seen={},{}
    for _,c in own:Members() do
      local s=Identity(c,pid);if #list>=128 or seen[s.id] then return end;seen[s.id]=true;list[#list+1]=c
    end
    if #list~=count or Method(own,"GetCount")~=count then return end
    for _,c in ipairs(list) do
      local ok,sent=pcall(City,E,pid,turn,player,own,c,t)
      if ok and sent then return end
    end
  end)
  running=false
end
return BaiqiFoodTileRescueRunner
