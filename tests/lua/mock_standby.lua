local w=TestWorld
w.allowStandby=true;w.armyTypes={6,6,5,5}
local normal={Index=0,Hash=301,ProjectType='PROJECT_TEST'}
local standby={Index=1,Hash=302,ProjectType='PROJECT_BAIQI_STANDBY'}
GameInfo.Projects=setmetatable({[0]=normal,[301]=normal,[1]=standby,[302]=standby},
 {__call=function() local i=0;return function() i=i+1;return ({normal,standby})[i] end end})
local city=TestWorld.objects.city;local original=city.GetBuildQueue
function city:GetBuildQueue()
 local q=original(self);local can=q.CanProduce;local id=self:GetID()
 q.CanProduce=function(self,hash,...)
  if hash==302 then return w.allowStandby and not w.rejectStandby end
  return can(self,hash,...)
 end
 q.GetCurrentProductionTypeHash=function()
  local entry=w.queues[id][1]
  local row=entry and ((entry.ProjectType and GameInfo.Projects[entry.ProjectType]) or (entry.UnitType and GameInfo.Units[entry.UnitType]))
  return row and row.Hash or 0
 end
 return q
end
