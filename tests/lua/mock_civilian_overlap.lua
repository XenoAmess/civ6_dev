local w=TestWorld;local o=w.objects
w.overlap=true;w.parkingReads=0
GameInfo.GreatPersonIndividuals[70].ActionRequiresCompletedDistrictType=nil
UnitManager.CanStartCommand=function() return false end
local scientist=o.player:GetUnits():FindID(4)
local other=setmetatable({GetID=function() return 7 end},{__index=scientist})
local original=o.player.GetUnits
function o.player:GetUnits()
 local collection=original(self)
 if w.secondCivilian then
  collection.Members=function() return ipairs({scientist,other}) end
  collection.FindID=function(_,id) if id==4 then return scientist elseif id==7 then return other end end
 end
 return collection
end
for _,index in ipairs({42,43}) do
 local p=Map.GetPlotByIndex(index)
 p.IsWater=function() return w.water or false end
 p.IsImpassable=function() return w.impassable or false end
end
Map.GetPlotByIndex(43).GetOwner=function() return w.foreignTarget and 8 or 7 end
Map.GetAdjacentPlot=function(x,y,dir) if x==2 and dir==0 then return Map.GetPlotByIndex(43) end end
Units.GetUnitsInPlot=function(plot)
 if plot:GetIndex()==42 and w.overlap then return {scientist,w.armyOnly and o.army or other} end
 if plot:GetIndex()==43 then
  w.parkingReads=w.parkingReads+1
  if w.occupiedTarget then return {o.army} end
 end
 return {}
end
local path=UnitManager.GetMoveToPathEx
UnitManager.GetMoveToPathEx=function(unit,index) if w.noPath then return {plots={}} end return path(unit,index) end
UnitManager.CanStartOperation=function(unit,op)
 if op==UnitOperationTypes.SKIP_TURN then return w.allowWait==true end
 return op==UnitOperationTypes.MOVE_TO and w.rejectMove~=true
end
UnitManager.RequestOperation=function(unit,op,params)
 assert(unit:GetID()==4 or (w.secondCivilian and unit:GetID()==7),'Army reached the background movement sink')
 table.insert(w.unitRequests,{unit=unit:GetID(),op=op,params=params})
end
