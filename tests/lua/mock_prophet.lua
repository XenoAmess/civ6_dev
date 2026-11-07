local w=TestWorld;local o=w.objects
w.scientistCharges=0;w.scientistClass=4;w.earnedBeliefs=0;w.foundingUnit=true;w.createdReligion=-1
local unit=GameInfo.Units[3];unit.UnitType='UNIT_GREAT_PROPHET'
GameInfo.Units.UNIT_GREAT_PROPHET=unit
local person=GameInfo.GreatPersonIndividuals[70];person.GreatPersonClassType='GREAT_PERSON_CLASS_PROPHET'
person.ActionCharges=0;person.ActionRequiresCompletedDistrictType=nil
local class={Index=4,Hash=904,GreatPersonClassType='GREAT_PERSON_CLASS_PROPHET'}
GameInfo.GreatPersonClasses[4]=class;GameInfo.GreatPersonClasses.GREAT_PERSON_CLASS_PROPHET=class
local required={Index=7,Hash=701,DistrictType='DISTRICT_HOLY_SITE'}
GameInfo.Districts.DISTRICT_HOLY_SITE=required;GameInfo.Districts[7]=required
GameInfo.UnitOperations={UNITOPERATION_FOUND_RELIGION={Index=0,Hash=901,OperationType='UNITOPERATION_FOUND_RELIGION'}}
function o.player:GetReligion()
 return {GetReligionTypeCreated=function() return w.createdReligion end,
 GetNumBeliefsEarned=function() return w.earnedBeliefs end,HasReligiousFoundingUnit=function() return w.foundingUnit end}
end
function o.city:GetDistricts()
 local d={GetType=function() return 7 end,GetX=function() return 3 end,GetY=function() return 3 end,
 IsComplete=function() return w.completed end,IsPillaged=function() return w.pillaged or false end}
 return {HasDistrict=function(_,index,completed) assert(index==7 and completed==true);return w.completed end,
 Members=function() return ipairs({d}) end}
end
UnitManager.CanStartOperation=function(unit,op,visibility,params)
 if op==901 then
  assert(visibility==nil and type(params)=='table' and next(params)==nil)
  if w.changeQualification then w.earnedBeliefs=2 end
  if w.changeFormation then w.scientistFormation=2 end
  if w.changeIndividual then w.scientistIndividual=71 end
  return w.scientistPlot==43 and not w.rejectFounding
 end
 return true
end
UnitManager.RequestOperation=function(unit,op,...)
 assert(unit:GetID()==4,'Military or unrelated unit reached prophet request sink')
 if op==901 then assert(select('#',...)==0,'Native founding operation takes no params') end
 table.insert(w.unitRequests,{unit=unit:GetID(),op=op,params=(...)})
end
