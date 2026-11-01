local w=TestWorld
w.scientistType=6;w.scientistClass=6;w.scientistIndividual=80;w.scientistCharges=0
w.slots={-1};w.workTypes={};w.slotType=0
local function rows(data)
 local t={};for _,r in ipairs(data) do
  t[r.Index]=r;t[r.Hash]=r
  for _,key in ipairs({'UnitType','DistrictType','GreatPersonClassType','GreatPersonIndividualType','BuildingType','GreatWorkSlotType','GreatWorkType'}) do if r[key] then t[r[key]]=r end end
 end
 return setmetatable(t,{__call=function() local i=0;return function() i=i+1;return data[i] end end})
end
for index,name in ipairs({'WRITER','ARTIST','MUSICIAN'}) do
 GameInfo.Units[index+5]={Index=index+5,Hash=205+index,UnitType='UNIT_GREAT_'..name}
end
GameInfo.GreatPersonClasses=rows({{Index=6,Hash=906,GreatPersonClassType='GREAT_PERSON_CLASS_WRITER'},
 {Index=7,Hash=907,GreatPersonClassType='GREAT_PERSON_CLASS_ARTIST'}, {Index=8,Hash=908,GreatPersonClassType='GREAT_PERSON_CLASS_MUSICIAN'}})
GameInfo.GreatPersonIndividuals=rows({{Index=80,Hash=880,GreatPersonIndividualType='GREAT_PERSON_INDIVIDUAL_CREATOR',GreatPersonClassType='GREAT_PERSON_CLASS_WRITER'}})
GameInfo.GreatWorks=rows({{Index=0,Hash=1000,GreatWorkType='GREATWORK_FIRST',GreatWorkObjectType='GREATWORKOBJECT_WRITING',GreatPersonIndividualType='GREAT_PERSON_INDIVIDUAL_CREATOR'},
 {Index=1,Hash=1001,GreatWorkType='GREATWORK_SECOND',GreatWorkObjectType='GREATWORKOBJECT_WRITING',GreatPersonIndividualType='GREAT_PERSON_INDIVIDUAL_CREATOR'},
 {Index=2,Hash=1002,GreatWorkType='GREATWORK_OTHER',GreatWorkObjectType='GREATWORKOBJECT_WRITING',GreatPersonIndividualType='GREAT_PERSON_INDIVIDUAL_OTHER'}})
GameInfo.GreatWorkSlotTypes=rows({{Index=0,Hash=1100,GreatWorkSlotType='GREATWORKSLOT_PALACE'},
 {Index=1,Hash=1101,GreatWorkSlotType='GREATWORKSLOT_MUSIC'}})
GameInfo.GreatWork_ValidSubTypes=rows({{Index=0,Hash=1200,GreatWorkSlotType='GREATWORKSLOT_PALACE',GreatWorkObjectType='GREATWORKOBJECT_WRITING'}})
GameInfo.Buildings=rows({{BuildingType='BUILDING_PALACE',Index=2,Hash=102,PrereqDistrict='DISTRICT_CITY_CENTER'}})
GameInfo.Districts[7].DistrictType='DISTRICT_CITY_CENTER';GameInfo.Districts.DISTRICT_CITY_CENTER=GameInfo.Districts[7]
local buildings={HasBuilding=function(_,index) return index==2 and not w.missingBuilding end,
 IsPillaged=function() return w.buildingPillaged or false end,GetNumGreatWorkSlots=function() return #w.slots end,
 GetGreatWorkInSlot=function(_,building,slot) assert(building==2);return w.slots[slot+1] end,
 GetGreatWorkSlotType=function() return w.slotType end,
 GetGreatWorkTypeFromIndex=function(_,index) return w.workTypes[index] end}
function w.objects.city:GetBuildings() return buildings end
function w.objects.city:GetOwner() return w.cityOwner or 7 end
Cities={GetCityInPlot=function(x,y) if x==2 and y==3 then return w.objects.city end end}
local created={}
Events.GreatWorkCreated={Add=function(fn) created[fn]=true end,Remove=function(fn) created[fn]=nil end}
function w.FireWork(...) for fn in pairs(created) do fn(...) end end
function w.WorkSubscriptions() local n=0;for _ in pairs(created) do n=n+1 end;return n end
function w.PlaceWork(index,kind) w.slots[1]=index;w.workTypes[index]=kind or 0 end
function w.SetCreativeKind(kind)
 w.scientistType=kind;w.scientistClass=kind
 GameInfo.GreatPersonIndividuals[80].GreatPersonClassType=GameInfo.GreatPersonClasses[kind].GreatPersonClassType
 local object=({[6]='GREATWORKOBJECT_WRITING',[7]='GREATWORKOBJECT_PORTRAIT',[8]='GREATWORKOBJECT_MUSIC'})[kind]
 GameInfo.GreatWorks[0].GreatWorkObjectType=object;GameInfo.GreatWorks[1].GreatWorkObjectType=object
 GameInfo.GreatWork_ValidSubTypes[0].GreatWorkObjectType=object
end
