-- Only the unguarded executor supplies these native ports. Explicit desired
-- focus states are observed before advancing; uncertain requests are not replayed.
include("BaiqiFoodFocus")
BaiqiFoodFocusRunner={}
local pending={}
local running=false
local function Integer(v)
  return type(v)=="number" and v>=0 and v<=2147483647 and v%1==0
end
local function Object(v)return type(v)=="table" or type(v)=="userdata" end
local function Method(o,k,...)
  assert(Object(o) and type(o[k])=="function");return o[k](o,...)
end
local function Static(o,k,...)
  assert(Object(o) and type(o[k])=="function");return o[k](...)
end
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
local function Read(E,c,pid,yield)
  local owner=Method(c,"GetOwner");if owner~=pid then return nil end
  local id,x,y=Method(c,"GetID"),Method(c,"GetX"),Method(c,"GetY")
  if not Integer(id) or not Integer(x) or not Integer(y) then return nil end
  local growth,citizens=Method(c,"GetGrowth"),Method(c,"GetCitizens")
  return {player=pid,owner=owner,cityID=id,x=x,y=y,
    surplus=Method(growth,"GetFoodSurplus"),favored=Method(citizens,"IsFavoredYield",yield),
    disfavored=Method(citizens,"IsDisfavoredYield",yield)}
end
local function Plan(s)
  if type(BaiqiFoodFocus)~="table" or type(BaiqiFoodFocus.Plan)~="function" then return nil end
  local p=BaiqiFoodFocus.Plan(s)
  if type(p)~="table" or getmetatable(p)~=nil or p.cityID~=s.cityID then return nil end
  if (p.mode=="FAVOR" and p.flags==0 and p.data0==1)
    or (p.mode=="UNIGNORE" and p.flags==1 and p.data0==0) then return p end
end
local function Same(a,b)
  return a and b and a.player==b.player and a.owner==b.owner and a.cityID==b.cityID
    and a.x==b.x and a.y==b.y and a.surplus==b.surplus
    and a.favored==b.favored and a.disfavored==b.disfavored
end
local function City(E,pid,turn,player,own,c,yield)
  local s=Read(E,c,pid,yield);if not s then return end
  local held=pending[s.cityID]
  if held then
    if held.player~=pid or held.x~=s.x or held.y~=s.y then return end
    local observed=s.disfavored==false and (held.mode=="UNIGNORE" or s.favored==true)
    if not observed then return end
    pending[s.cityID]=nil
    print("BAIQI|food_focus_observed|turn="..turn.."|city="..s.cityID.."|mode="..held.mode)
  end
  local plan=Plan(s);if not plan then return end
  local command=E.CityCommandTypes.SET_FOCUS
  local flags,data0,yieldKey=E.CityCommandTypes.PARAM_FLAGS,E.CityCommandTypes.PARAM_DATA0,E.CityCommandTypes.PARAM_YIELD_TYPE
  if command==nil or flags==nil or data0==nil or yieldKey==nil
    or flags==data0 or flags==yieldKey or data0==yieldKey then return end
  local params={[flags]=plan.flags,[yieldKey]=yield,[data0]=plan.data0}
  local manager=E.CityManager;assert(Object(manager))
  local qualifier,writer=manager.CanStartCommand,manager.RequestCommand
  if type(qualifier)~="function" or type(writer)~="function"
    or qualifier(c,command,params)~=true then return end
  local freshCity=Method(own,"FindID",s.cityID)
  if not freshCity or not Same(s,Read(E,freshCity,pid,yield)) then return end
  local fresh=Plan(Read(E,freshCity,pid,yield))
  if not fresh or fresh.mode~=plan.mode or fresh.flags~=plan.flags or fresh.data0~=plan.data0
    or Player(E,pid,turn)~=player or E.CityManager~=manager
    or manager.CanStartCommand~=qualifier or manager.RequestCommand~=writer
    or E.CityCommandTypes.SET_FOCUS~=command or E.YieldTypes.FOOD~=yield
    or E.CityCommandTypes.PARAM_FLAGS~=flags or E.CityCommandTypes.PARAM_DATA0~=data0
    or E.CityCommandTypes.PARAM_YIELD_TYPE~=yieldKey then return end
  -- Written before the call. False, void and exceptions remain held until the
  -- actual native focus state is observed, including on later turns.
  pending[s.cityID]={player=pid,x=s.x,y=s.y,mode=plan.mode}
  print("BAIQI|food_focus_request|turn="..turn.."|city="..s.cityID.."|mode="..plan.mode)
  pcall(writer,freshCity,command,params)
end
function BaiqiFoodFocusRunner.Run(E,pid)
  if running then return end
  running=true
  pcall(function()
    if type(E)~="table" or getmetatable(E)~=nil or not Integer(pid) then return end
    local turn=Static(E.Game,"GetCurrentGameTurn")
    local player=Player(E,pid,turn);if not player then return end
    local yield=E.YieldTypes.FOOD;if not Integer(yield) then return end
    local own=Method(player,"GetCities");local expected=Method(own,"GetCount")
    if not Integer(expected) or expected>128 then return end
    local cities={}
    for _,c in own:Members() do
      if #cities>=128 or Method(c,"GetOwner")~=pid then return end
      cities[#cities+1]=c
    end
    if #cities~=expected or Method(own,"GetCount")~=expected then return end
    for _,c in ipairs(cities) do pcall(City,E,pid,turn,player,own,c,yield) end
  end)
  running=false
end
return BaiqiFoodFocusRunner
