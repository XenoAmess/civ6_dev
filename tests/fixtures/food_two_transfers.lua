-- Patch the existing real bridge fixture with two actual distinct native sites.
YieldTypes=E.YieldTypes
W.surplus=-2;W.donor=6;W.sourceDistance=2;W.applied={};W.requests={}
local own=Players[0]:GetCities()
local target,source=own:FindID(458758),own:FindID(65536)
source.GetGrowth=function()return {GetFoodSurplus=function()return W.donor end}end
local function plot(id,x,y,food,district)
  return {GetIndex=function()return id end,GetX=function()return x end,GetY=function()return y end,
    GetOwner=function()return 0 end,GetYield=function()return food end,
    GetDistrictType=function()return district end,GetImprovementType=function()return -1 end}
end
local plots={[2276]=plot(2276,56,30,2,-1),[2277]=plot(2277,57,30,2,-1),[2353]=plot(2353,59,31,0,9)}
Map.GetPlotByIndex=function(id)return plots[id]end;E.Map.GetPlotByIndex=Map.GetPlotByIndex
E.Map.GetCityPlots=function()return {GetPurchasedPlots=function(_,city)
  local r={};if city==target then r[8]=2353 end
  for _,id in ipairs({2276,2277})do
    if (city==target and W.applied[id])or(city==source and not W.applied[id])then r[id]=id end
  end;return r
end}end
Cities.GetPlotPurchaseCity=function(p)return W.applied[p:GetIndex()]and target or source end
E.CityManager.GetCommandTargets=function(city,kind,params)
  local a,b,d={},{},{}
  if kind==E.CityCommandTypes.MANAGE then
    local count=0
    for _,id in ipairs({2276,2277})do
      if W.applied[id]then count=count+1 end
      if(city==target and W.applied[id])or(city==source and not W.applied[id])then
        a[id]=id;b[id]=1;d[id]=0
      end
    end
    if city==target then a[0]=2353;b[0]=2-count;d[0]=0 end
    return {[10]=a,[11]=b,[12]=d}
  end
  assert(city==target and kind==E.CityCommandTypes.SWAP_TILE_OWNER)
  for _,id in ipairs({2276,2277})do if not W.applied[id]then a[id]=id end end
  return {[10]=a}
end
E.CityManager.CanStartCommand=function(city,kind,p)
  assert(city==target and kind==2 and p[4]==4 and p[6]==30 and(p[5]==56 or p[5]==57))
  W.reads=W.reads+1;if W.onPermission then W.onPermission(W.reads)end
  return W.allowed
end
E.CityManager.RequestCommand=function(city,kind,p)
  local id=p[5]==56 and 2276 or 2277
  W.requests[#W.requests+1]={plotID=id,city=city:GetID()}
  if not W.noApply then W.applied[id]=true;W.surplus=W.surplus+1;W.donor=W.donor-2 end
  if W.throw then error('unknown submit reply')end
  return W.requestReturn
end
