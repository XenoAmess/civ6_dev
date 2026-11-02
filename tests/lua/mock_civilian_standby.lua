-- Bindings for native ready/awake/HOLD; actual controller and Core receipt run.
local w=TestWorld
w.standbyReady=true;w.activity=1797587246;w.skipLegal=true;w.autoSkip=true
ActivityTypes={ACTIVITY_AWAKE=1797587246,ACTIVITY_HOLD=75236491}
local unit=w.objects.missionary
unit.IsReadyToSelect=function() return w.standbyReady end
UnitManager.GetActivityType=function() return w.activity end
GameInfo.UnitOperations.UNITOPERATION_SKIP_TURN={Hash=745019656}
UnitOperationTypes.SKIP_TURN=nil
local can=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(u,op,...)
 if op==745019656 then
  if w.onCanSkip then w.onCanSkip() end
  return w.skipLegal and w.activity==ActivityTypes.ACTIVITY_AWAKE and w.standbyReady and w.missionaryMoves>0
 end
 return can(u,op,...)
end
local request=UnitManager.RequestOperation
UnitManager.RequestOperation=function(u,op,params)
 if op==745019656 then
  w.unitRequests[#w.unitRequests+1]={unit=u:GetID(),op=op,params=params}
  if w.throwSkip then error('injected unknown native standby outcome') end
  if w.autoSkip then w.activity=ActivityTypes.ACTIVITY_HOLD;w.standbyReady=false end
  return
 end
 return request(u,op,params)
end
