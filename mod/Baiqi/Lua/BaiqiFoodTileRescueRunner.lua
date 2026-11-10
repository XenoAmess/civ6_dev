-- The executor provides original ports, never the read-only player UI facade.
-- One desired reassignment at a time. Unknown submissions remain held in-session.
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
local function City(E,pid,turn,player,own,c,t)
  local identity=Identity(c,pid);local held=pending[identity.id]
  if held then
    if held.player~=pid or not SameCity(held,identity) then return false end
    local _,purchased=Ownership(E,own,pid)
    local surplus=Method(Method(c,"GetGrowth"),"GetFoodSurplus")
    if purchased[held.plotID]~=identity.id or not Finite(surplus) or surplus<0 then return false end
    print("BAIQI|food_tile_rescue_observed|turn="..turn.."|city="..identity.id.."|plot="..held.plotID.."|surplus="..surplus)
    pending[identity.id]=nil
  end
  if attempted[identity.id]==turn then return false end
  local s=Snapshot(E,own,c,pid,t);local plan=Plan(s);if not plan then return false end
  local manager=E.CityManager;local qualifier,writer=manager.CanStartCommand,manager.RequestCommand
  assert(type(qualifier)=="function" and type(writer)=="function")
  local params=Params(E,t.PARAM_SWAP_TILE_OWNER);params[t.PARAM_X]=plan.x;params[t.PARAM_Y]=plan.y
  if qualifier(c,t.SWAP_TILE_OWNER,params)~=true then return false end
  local fresh=Method(own,"FindID",identity.id);assert(fresh and SameCity(identity,Identity(fresh,pid)))
  local again=Snapshot(E,own,fresh,pid,t);local nextPlan=Plan(again)
  if not Equal(plan,nextPlan) or s.surplus~=again.surplus or s.population~=again.population or s.starvation~=again.starvation
    or Player(E,pid,turn)~=player or E.CityManager~=manager or manager.CanStartCommand~=qualifier or manager.RequestCommand~=writer then return false end
  local freshTokens=Tokens(E);for k,v in pairs(t) do if freshTokens[k]~=v then return false end end
  local finalParams=Params(E,t.PARAM_SWAP_TILE_OWNER);finalParams[t.PARAM_X]=plan.x;finalParams[t.PARAM_Y]=plan.y
  for k,v in pairs(params) do if finalParams[k]~=v then return false end end
  for k,v in pairs(finalParams) do if params[k]~=v then return false end end
  -- Desired plot ownership is the receipt. No timeout, alternate target or retry
  -- follows false/void/throwing submission while that desired state is unknown.
  pending[identity.id]={player=pid,id=identity.id,x=identity.x,y=identity.y,plotID=plan.plotID}
  attempted[identity.id]=turn
  print("BAIQI|food_tile_rescue_request|turn="..turn.."|city="..identity.id.."|source="..plan.sourceCityID.."|plot="..plan.plotID.."|predicted="..plan.expectedSurplus)
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
