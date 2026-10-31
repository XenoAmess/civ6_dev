-- Delayed native move consumer for the real Controller, not a copied planner.
local w=TestWorld
w.withBuilder=true;w.queueSize=1;w.builderPlot=42;w.builderMoves=2;w.plotReads=0
local objects=w.objects
local function Plot(index,x)
 return {GetIndex=function() return index end,GetX=function() return x end,GetY=function() return 3 end,
  GetOwner=function() return 7 end,GetFeatureType=function() return -1 end,
  IsImprovementPillaged=function() return false end,GetImprovementType=function() return -1 end}
end
local plots={[42]=Plot(42,2),[43]=Plot(43,3)}
Map.GetPlotByIndex=function(index) return plots[index] end
Map.GetPlot=function(x) return plots[x==2 and 42 or 43] end
Map.GetPlotDistance=function(x1,y1,x2,y2) return math.abs(x2-x1) end
objects.builder.GetPlotId=function() return w.builderPlot end
objects.builder.GetX=function() return plots[w.builderPlot]:GetX() end
objects.builder.GetMovesRemaining=function() return w.builderMoves end
objects.builder.GetComponentID=function() return 3 end
objects.builder.IsReadyToMove=function() return w.ready~=false end
objects.city.GetCityAI=function() return {GetImprovementRecommendationsForBuilder=function() return {{ImprovementLocation=43}} end} end
GameInfo.Improvements=setmetatable({},{__call=function() local done=false;return function()
 if not done then done=true;return {Hash=904,Index=0} end end end})
UnitManager.GetMoveToPathEx=function(unit,index) return {plots=unit:GetPlotId()==index and {index} or {unit:GetPlotId(),index}} end
UnitManager.CanStartOperation=function(unit,op)
 if op==UnitOperationTypes.BUILD_IMPROVEMENT then return unit:GetPlotId()==43 end
 return true
end
UnitManager.GetQueuedDestination=function() return w.queuedDestination end
UI.IsGameCoreBusy=function() return w.busy or false end
UI.IsProcessingMessages=function() return w.processing or false end
PlayersVisibility[7].IsVisible=function() return w.visible~=false end
Units.GetUnitsInPlot=function(plot)
 w.plotReads=w.plotReads+1
 if plot:GetIndex()==43 and w.targetOccupied then return {objects.settler} end
 if plot:GetIndex()==43 and w.targetArmy then return {objects.army} end
 return {}
end
