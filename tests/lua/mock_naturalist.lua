-- Extends the native-binding-only missionary world with a different unit type.
local W=TestWorld
W.parkCharges=1;W.parkCandidates={42};W.parkBuilt={};W.parkRequests={};W.pathTargets={}
W.withMissionary=true
GameInfo.Units[60].UnitType='UNIT_NATURALIST'
GameInfo.UnitOperations.UNITOPERATION_DESIGNATE_PARK={OperationType='UNITOPERATION_DESIGNATE_PARK',Hash=1031611255,Index=7}
W.objects.missionary.GetParkCharges=function() return W.parkCharges end
for index=42,44 do
  local plot=Map.GetPlotByIndex(index)
  plot.IsNationalPark=function() return W.parkBuilt[index]==true end
end
local parks={}
function parks:GetPossibleParkTiles(pid)
  assert(self==parks and pid==7)
  local result={}
  for _,index in ipairs(W.parkCandidates) do if not W.parkBuilt[index] then result[#result+1]=index end end
  return result
end
Game.GetNationalParks=function(...) assert(select('#',...)==0);return parks end
local nativePath=UnitManager.GetMoveToPathEx
UnitManager.GetMoveToPathEx=function(unit,index,...)
  W.pathTargets[#W.pathTargets+1]=index
  if W.noPathIndex==index then return nil end
  return nativePath(unit,index,...)
end
local nativeCan=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(unit,operation,...)
  if operation==1031611255 then
    if W.onParkQualification then W.onParkQualification() end
    return W.parkLegal~=false
  end
  return nativeCan(unit,operation,...)
end
local nativeRequest=UnitManager.RequestOperation
UnitManager.RequestOperation=function(unit,operation,parameters)
  if operation==1031611255 then
    if W.onPark then W.onPark(unit,operation,parameters) end
    W.parkRequests[#W.parkRequests+1]={unit=unit:GetID(),operation=operation,parameters=parameters}
    if W.throwPark then error('unknown park request') end
    if W.autoPark then
      W.parkBuilt[W.missionaryPlot]=true;W.parkCharges=0;W.missionaryMoves=0;W.withMissionary=false
    end
    return
  end
  return nativeRequest(unit,operation,parameters)
end
