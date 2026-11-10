include=function()end
local w={turn=208,surplus=-1,starvation=2,pop=8,favored=true,disfavored=false,allowed=true,
  busy=false,processing=false,human=true,active=true,multi=false,owner=0,sourceDistance=4,
  sourceHasPlot=false,sourceLocked=0,visible=true,revealed=true,requests={},reads=0,apply=false}
W=w
local c={GetID=function()return 458758 end,GetOwner=function()return w.owner end,
  GetX=function()return 59 end,GetY=function()return 32 end,GetPopulation=function()return w.pop end}
local d={GetID=function()return w.sourceID or 65536 end,GetOwner=function()return 0 end,
  GetX=function()return 55 end,GetY=function()return 34 end,GetPopulation=function()return 16 end,
  GetGrowth=function()return {GetFoodSurplus=function()return 16 end}end}
c.GetGrowth=function()return {GetFoodSurplus=function()return w.surplus end,GetTurnsUntilStarvation=function()return w.starvation end}end
c.GetCitizens=function()return {IsFavoredYield=function()return w.favored end,IsDisfavoredYield=function()return w.disfavored end}end
local own={GetCount=function()return w.count or 2 end,FindID=function(_,id)
  if w.staleFind then return d end
  if id==458758 then return c elseif id==65536 then return d end end}
own.Members=function()local n=0;return function()n=n+1;if n==1 then return 7,c elseif n==2 then return 12,d end end end
local player={IsTurnActive=function()return w.active end,GetCities=function()return own end}
local function plot(id,x,y,food,district)
  return {GetX=function()return x end,GetY=function()return y end,GetOwner=function()return 0 end,
    GetYield=function()return food end,GetDistrictType=function()return district end,GetImprovementType=function()return -1 end}
end
local plots={[2277]=plot(2277,57,30,1,-1),[2353]=plot(2353,59,31,0,9)}
E={leader='LEADER_BAIQI',Players={[0]=player},PlayerConfigurations={[0]={IsHuman=function()return w.human end,
  GetLeaderTypeName=function()return w.leader or 'LEADER_BAIQI' end}},
  PlayersVisibility={[0]={IsVisible=function()return w.visible end,IsRevealed=function()return w.revealed end}},
  YieldTypes={FOOD=0},CityCommandTypes={MANAGE=1,SWAP_TILE_OWNER=2,PARAM_MANAGE_CITIZEN=3,PARAM_SWAP_TILE_OWNER=4,PARAM_X=5,PARAM_Y=6},
  CityCommandResults={PLOTS=10,CITIZENS=11,LOCKED_CITIZENS=12},
  Game={GetLocalPlayer=function()return 0 end,GetCurrentGameTurn=function()return w.turn end,
    IsAllowStrategicCommands=function()return true end},
  GameConfiguration={IsAnyMultiplayer=function()return w.multi end,IsHotseat=function()return false end},
  UI={IsGameCoreBusy=function()return w.busy end,IsProcessingMessages=function()return w.processing end,
    GetInterfaceModeParameter=function(k)return k end},Map={GetGridSize=function()return 74,46 end,
    GetPlotByIndex=function(id)return plots[id]end,GetPlotDistance=function(x,y)
      if x==55 and y==34 then return w.sourceDistance else return 3 end end}}
E.Map.GetCityPlots=function()return {GetPurchasedPlots=function(_,city)
  if city==c then return w.transferred and {[8]=2353,[14]=2277}or {[8]=2353}end
  return w.transferred and {} or {[90]=2277}end}end
E.CityManager={GetCommandTargets=function(city,kind,p)
  if kind==1 then
    assert(p[3]==3)
    if city==c then return {[10]={[0]=2353},[11]={[0]=2},[12]={[0]=w.targetLocked or 0}}end
    if w.manageError then error('unknown source work data')end
    return {[10]=w.sourceHasPlot and {[7]=2277}or {},[11]={[7]=1},[12]={[7]=w.sourceLocked}}
  end
  assert(kind==2 and p[4]==4);return {[10]={[0]=2277}}
end,CanStartCommand=function(city,kind,p)
  w.reads=w.reads+1;assert(city==c and kind==2 and p[4]==4 and p[5]==57 and p[6]==30)
  if w.onPermission then w.onPermission(w.reads)end
  return w.allowed
end,RequestCommand=function(city,kind,p)
  assert(city==c and kind==2 and p[4]==4 and p[5]==57 and p[6]==30)
  w.requests[#w.requests+1]={city=city:GetID(),kind=kind,x=p[5],y=p[6]}
  if w.reenter then BaiqiFoodTileRescueRunner.Run(E,0)end
  if w.apply then w.transferred=true;w.surplus=0 end
  if w.throw then error('uncertain request')end
  return w.requestReturn
end}
