-- Native API ports only: no production permission, scheduling or receipt logic.
local W=TestWorld
W.withMissionary=true;W.archHome=66;W.archSlots={-1,-1,-1};W.archCandidates={42};W.archResource=9
W.archRequests={};W.choiceRequests={};W.archQualifies=0;W.artifactIndex=5;W.artifactType=0
W.actingPlayer=2;W.targetPlayer=3
GameInfo.Units[60].UnitType='UNIT_ARCHAEOLOGIST'
GameInfo.Buildings.BUILDING_MUSEUM_ARTIFACT={BuildingType='BUILDING_MUSEUM_ARTIFACT',Index=24,Hash=1182236625}
GameInfo.Resources[9]={ResourceType='RESOURCE_ANTIQUITY_SITE'}
GameInfo.Resources[10]={ResourceType='RESOURCE_SHIPWRECK'}
GameInfo.GreatWorkSlotTypes={[8]={GreatWorkSlotType='GREATWORKSLOT_ARTIFACT'}}
GameInfo.UnitOperations.UNITOPERATION_EXCAVATE={OperationType='UNITOPERATION_EXCAVATE',Hash=1548958412,Index=11}
local u=W.objects.missionary
u.GetArchaeologyHomeCity=function() return W.archHome end
u.GetArchaeology=function()
 return {GetActivationHighlightPlots=function() return W.archCandidates end,
  GetArtifactIndex=function() return W.artifactIndex end}
end
local units=W.objects.player.GetUnits
W.objects.player.GetUnits=function(self)
 local collection=units(self)
 collection.GetNextExtractingArchaeologist=function() if W.pendingArtifact and W.withMissionary then return u end end
 return collection
end
local buildings={HasBuilding=function(_,index) return index==24 and W.archMuseum~=false end,
 IsPillaged=function() return W.archPillaged==true end,
 GetNumGreatWorkSlots=function() return #W.archSlots end,
 GetGreatWorkSlotType=function() return 8 end,
 GetGreatWorkInSlot=function(_,index,slot) return W.archSlots[slot+1] end}
W.objects.city.GetBuildings=function() return buildings end
for index=42,44 do
 Map.GetPlotByIndex(index).GetResourceType=function() return W.archResource end
end
Game.GetArtifactByIndex=function(index)
 assert(index==W.artifactIndex)
 return {Type=W.artifactType,ActingPlayerID=W.actingPlayer,TargetPlayerID=W.targetPlayer}
end
PlayerConfigurations[2]={};PlayerConfigurations[3]={}
PlayerOperations.CHOOSE_ARTIFACT_PLAYER=-190000001
PlayerOperations.PARAM_PLAYER_ONE=-190000002
local can=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(unit,operation,...)
 if operation==1548958412 then
  W.archQualifies=W.archQualifies+1
  if W.onArchQualification then W.onArchQualification(W.archQualifies) end
  return W.archLegal~=false
 end
 return can(unit,operation,...)
end
local request=UnitManager.RequestOperation
UnitManager.RequestOperation=function(unit,operation,...)
 if operation==1548958412 then
  assert(select('#',...)==0)
  if W.onExcavate then W.onExcavate(unit,operation) end
  W.archRequests[#W.archRequests+1]={id=unit:GetID(),operation=operation}
  if W.autoExcavate then W.pendingArtifact=true;W.archResource=-1;W.missionaryMoves=0 end
  if W.throwExcavate then error('unknown excavation outcome') end
  return
 end
 return request(unit,operation,...)
end
UI.RequestPlayerOperation=function(pid,operation,params)
 if W.onChoice then W.onChoice(pid,operation,params) end
 W.choiceRequests[#W.choiceRequests+1]={pid=pid,operation=operation,params=params}
 if W.autoChoice then
  W.pendingArtifact=false;W.archSlots[1]=101
  if W.consumeArch then W.withMissionary=false end
  TestArchBridge.Emit(pid,W.missionaryID,2,3,24,101)
 end
 if W.throwChoice then error('unknown artifact choice outcome') end
end
