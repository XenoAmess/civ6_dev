-- Native-shaped repaired building head with no current production hash.
local w=TestWorld;local o=w.objects
w.productionMode=true;w.withTrader=false;w.ghost=true;w.granaryExists=true
w.granaryPillaged=false;w.granaryProgress=54;w.granaryCost=32
w.campusComplete=true;w.campusPillaged=true;w.campusProgress=45;w.campusCost=61
w.queues[66]={{Directive=1,BuildingType=0,Location={x=-9999,y=-9999},Modifiers=0}}
CityOperationTypes.VALUE_REMOVE_AT=777;CityOperationTypes.PARAM_QUEUE_LOCATION=778
local campus={DistrictType='DISTRICT_CAMPUS',Hash=707,Index=7}
GameInfo.Districts=setmetatable({[7]=campus,[707]=campus,DISTRICT_CAMPUS=campus},
 {__call=function() local done=false;return function() if not done then done=true;return campus end end end})
function o.city:GetBuildings()
 return {HasBuilding=function() return w.granaryExists end,IsPillaged=function() return w.granaryPillaged end}
end
function o.city:GetDistricts()
 return {HasDistrict=function() return w.campusComplete end,IsPillaged=function() return w.campusPillaged end}
end
local original=o.city.GetBuildQueue
function o.city:GetBuildQueue()
 local q=original(self);local id=self:GetID();local getHash=q.GetCurrentProductionTypeHash
 q.GetCurrentProductionTypeHash=function()
  if id==66 and w.ghost then return 0 end
  local head=w.queues[id][1]
  if head and head.BuildingType~=nil then return GameInfo.Buildings[head.BuildingType].Hash end
  if head and head.DistrictType~=nil then return GameInfo.Districts[head.DistrictType].Hash end
  return getHash()
 end
 q.GetBuildingProgress=function() return w.granaryProgress end
 q.GetBuildingCost=function() return w.granaryCost end
 q.GetDistrictProgress=function() return w.campusProgress end
 q.GetDistrictCost=function() return w.campusCost end
 q.HasBeenPlaced=function() return true end
 q.CanProduce=function(_,hash) return id==66 and hash==707 and w.campusPillaged end
 return q
end
CityManager.CanStartOperation=function(city,op,params)
 if params[CityOperationTypes.PARAM_INSERT_MODE]==777 then
  if w.onCleanupGate then w.onCleanupGate() end
  return not w.rejectCleanup
 end
 return true
end
function w.AcceptCleanup()
 local packet=w.cityRequests[#w.cityRequests]
 assert(packet.params[CityOperationTypes.PARAM_INSERT_MODE]==777 and packet.params[778]==0)
 table.remove(w.queues[66],1);w.ghost=false
end
