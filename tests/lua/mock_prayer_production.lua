local w=TestWorld
w.completed[66]=true;w.completed[67]=true;w.canRecruit=false
local row={Index=0,Hash=910,ProjectType='PROJECT_ENHANCE_DISTRICT_HOLY_SITE',PrereqDistrict='DISTRICT_HOLY_SITE'}
local standby={Index=1,Hash=911,ProjectType='PROJECT_BAIQI_STANDBY'}
w.prayerDefinition=row;w.allowed[910]=true
GameInfo.Projects=setmetatable({[0]=row,[910]=row,PROJECT_ENHANCE_DISTRICT_HOLY_SITE=row,
 [1]=standby,[911]=standby,PROJECT_BAIQI_STANDBY=standby},{__call=function()
 local i=0;return function()i=i+1;if i==1 then return standby elseif i==2 then return row end end
end})
for _,city in ipairs(w.cities)do
 local get=city.GetDistricts
 city.GetDistricts=function()
  local d=get()
  d.IsPillaged=function(_,index)assert(index==3);return w.holyPillaged end
  return d
 end
end
w.holyPillaged=false
local getPeople=Game.GetGreatPeople
Game.GetGreatPeople=function()
 local p=getPeople()
 function p:CanRecruitPerson(pid,id)
  assert(pid==7 and id==0)
  if w.throwRecruit then error('native recruitment read unavailable')end
  return w.canRecruit
 end
 return p
end
local can=CityManager.CanStartOperation
CityManager.CanStartOperation=function(c,op,params)
 local result=can(c,op,params)
 if params[CityOperationTypes.PARAM_PROJECT_TYPE]==910 then
  if w.qualification[910]==2 and w.prayerShock then w.prayerShock()end
  if w.noPrayerOperation then return false end
 end
 return result
end
