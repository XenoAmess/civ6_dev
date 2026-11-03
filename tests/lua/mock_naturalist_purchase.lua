-- Native bindings only. The actual Quote, Core permit and Controller run later.
local W=TestWorld
W.withMissionary=false;W.faith=400;W.purchaseCost=300;W.purchaseRequests={};W.purchaseQualifications=0
W.parkCandidates={44};W.queueSize=1
GameInfo.Units.UNIT_NATURALIST=GameInfo.Units[60]
GameInfo.Yields={YIELD_FAITH={Index=5}}
MilitaryFormationTypes={STANDARD_MILITARY_FORMATION=0}
CityCommandTypes={PURCHASE=1490793096,PARAM_UNIT_TYPE=-1899860717,PARAM_YIELD_TYPE=730511874,
  PARAM_MILITARY_FORMATION_TYPE=2126768863}
for index=42,44 do
  local plot=Map.GetPlotByIndex(index)
  plot.IsWater=function() return W.waterTarget==true end
  plot.IsImpassable=function() return W.impassableTarget==true end
end
local city=W.objects.city
city.GetGold=function() return {GetPurchaseCost=function() return W.purchaseCost end} end
city.GetX=function() return 2 end;city.GetY=function() return 3 end
W.objects.player.GetReligion=function()
  return {GetFaithBalance=function() return W.faith end,GetReligionTypeCreated=function() return W.ownReligion end}
end
W.objects.missionary.IsDelayedDeath=function() return W.natureDead==true end
CityManager.CanStartCommand=function(c,op,visible,params,results)
  assert(c:GetID()==66 and op==CityCommandTypes.PURCHASE and visible==false and results==true)
  assert(params[CityCommandTypes.PARAM_UNIT_TYPE]==GameInfo.Units.UNIT_NATURALIST.Hash)
  assert(params[CityCommandTypes.PARAM_YIELD_TYPE]==5 and params[CityCommandTypes.PARAM_MILITARY_FORMATION_TYPE]==0)
  W.purchaseQualifications=W.purchaseQualifications+1
  if W.onPurchaseQualification then W.onPurchaseQualification(W.purchaseQualifications) end
  return W.purchaseLegal~=false
end
CityManager.RequestCommand=function(c,op,params)
  local raw=TestPurchaseBridge.store.BAIQI_NATURALIST_PURCHASE_INTENTS_V1
  assert(raw and raw.operations['1'].stage=='ARMED' and raw.operations['1'].cost==W.purchaseCost)
  assert(c:GetID()==66 and op==CityCommandTypes.PURCHASE)
  assert(params[CityCommandTypes.PARAM_UNIT_TYPE]==GameInfo.Units.UNIT_NATURALIST.Hash)
  W.purchaseRequests[#W.purchaseRequests+1]={city=c:GetID(),op=op,params=params}
  if W.onPurchase then W.onPurchase(c,op,params) end
  if W.throwPurchase then error('unknown native purchase result') end
  if W.autoPurchase then
    W.faith=W.faith-W.purchaseCost;W.withMissionary=true;W.missionaryID=900
    W.missionaryPlot=42;W.missionaryMoves=0;W.missionaryFormation=1;W.parkCharges=1
  end
end
