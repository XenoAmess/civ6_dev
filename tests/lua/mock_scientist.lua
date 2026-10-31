-- Native-shaped district hints and a delayed command consumer.
local w=TestWorld;local o=w.objects
w.queueSize=1;w.scientistPlot=42;w.scientistMoves=2;w.scientistCharges=1
w.scientistFormation=1;w.withScientist=true;w.completed=true;w.commandRequests={};w.scientistUnitReads=0
local function rows(data)
 local t={};for _,r in ipairs(data) do t[r.Index]=r;t[r.Hash]=r
  local name=r.UnitType or r.DistrictType or r.GreatPersonIndividualType or r.CommandType or r.GreatPersonClassType
  if name then t[name]=r end
 end
 return setmetatable(t,{__call=function() local i=0;return function() i=i+1;return data[i] end end})
end
GameInfo.Units=rows({GameInfo.Units[0],GameInfo.Units[1],GameInfo.Units[2],
 {UnitType='UNIT_GREAT_SCIENTIST',Index=3,Hash=203},
 {UnitType='UNIT_GREAT_GENERAL',Index=4,Hash=204,FormationClass='FORMATION_CLASS_SUPPORT'},
 {UnitType='UNIT_GREAT_ADMIRAL',Index=5,Hash=205,FormationClass='FORMATION_CLASS_SUPPORT'}})
GameInfo.Districts=rows({{DistrictType='DISTRICT_CAMPUS',Index=7,Hash=701}})
GameInfo.GreatPersonIndividuals=rows({{GreatPersonIndividualType='GREAT_PERSON_INDIVIDUAL_TEST',Index=70,Hash=770,
 GreatPersonClassType='GREAT_PERSON_CLASS_SCIENTIST',ActionRequiresCompletedDistrictType='DISTRICT_CAMPUS'}})
GameInfo.UnitCommands=rows({{CommandType='UNITCOMMAND_ACTIVATE_GREAT_PERSON',Index=1,Hash=501}})
GameInfo.GreatPersonClasses=rows({{GreatPersonClassType='GREAT_PERSON_CLASS_SCIENTIST',Index=5,Hash=905}})
local activated={}
Events.UnitGreatPersonActivated={Add=function(fn) activated[fn]=true end,Remove=function(fn) activated[fn]=nil end}
function w.FireActivation(...) for fn in pairs(activated) do fn(...) end end
function w.ActivationSubscriptions() local count=0;for _ in pairs(activated) do count=count+1 end;return count end
local function plot(index,x)
 return {GetIndex=function() return index end,GetX=function() return x end,GetY=function() return 3 end,
  GetOwner=function() return 7 end}
end
local plots={[42]=plot(42,2),[43]=plot(43,3)}
Map.GetPlotByIndex=function(index) return plots[index] end
Map.GetPlot=function(x) return plots[x==2 and 42 or 43] end
Map.GetPlotDistance=function(x,y,x2,y2) return math.abs(x-x2) end
Map.GetPlotXYWithRangeCheck=function(x,y,dx,dy) if dx==0 and dy==0 then return Map.GetPlot(x,y) end end
PlayersVisibility[7].IsRevealed=function(_,x) return not (w.hiddenTarget and x==3) end
PlayersVisibility[7].IsVisible=function() return not w.hiddenEnemy end
Units.GetUnitsInPlot=function(p)
 w.scientistUnitReads=w.scientistUnitReads+1
 if w.enemy and p:GetIndex()==43 then return {{GetOwner=function() return 8 end}} end
 return {}
end
function o.player:GetDiplomacy() return {IsAtWarWith=function(_,pid) return pid==8 end} end
local function members(list)
 return function() local i=0;return function() i=i+1;if list[i] then return i,list[i] end end end
end
function o.city:GetDistricts()
 local district={GetType=function() return 7 end,GetX=function() return 3 end,GetY=function() return 3 end}
 return {HasDistrict=function(_,index,completed) assert(index==7 and completed==true);return w.completed end,
  Members=members({district})}
end
local gp={GetIndividual=function() return w.scientistIndividual or 70 end,GetClass=function() return w.scientistClass or 5 end,GetActionCharges=function() return w.scientistCharges end}
local scientist={GetID=function() return w.scientistID or 4 end,GetOwner=function() return w.scientistOwner or 7 end,
 GetUnitType=function() return w.scientistType or 3 end,GetPlotId=function() return w.stalePlotId or w.scientistPlot end,
 GetX=function() return plots[w.scientistPlot]:GetX() end,GetY=function() return 3 end,
 GetMovesRemaining=function() return w.scientistMoves end,GetFormationUnitCount=function() return w.scientistFormation end,
 GetGreatPerson=function() return gp end,IsReadyToMove=function() return w.scientistReady~=false end}
local general=setmetatable({GetID=function() return 5 end,GetUnitType=function() return 4 end},{__index=o.army})
local admiral=setmetatable({GetID=function() return 6 end,GetUnitType=function() return 5 end},{__index=o.army})
function o.player:GetUnits()
 local list={o.army,general,admiral};if w.withScientist then list[#list+1]=scientist end
 return {Members=members(list),FindID=function(_,id)
  if id==4 and w.findScientistAlias then return scientist end
  for _,u in ipairs(list) do if u:GetID()==id then return u end end
 end}
end
UnitManager.GetMoveToPathEx=function(u,index)
 local start=Map.GetPlot(u:GetX(),u:GetY()):GetIndex()
 return {plots=start==index and {index} or {start,index}}
end
UnitManager.GetQueuedDestination=function() return w.queuedDestination end
UnitManager.CanStartCommand=function(unit,hash,visibility,results)
 assert(unit:GetID()==4 and hash==501 and visibility==false and results==true)
 return w.scientistPlot==43 and not w.rejectActivation
end
UnitManager.RequestCommand=function(unit,hash,...)
 assert(unit:GetID()==4 and hash==501 and select('#',...)==0)
 w.commandRequests[#w.commandRequests+1]={unit=unit:GetID(),hash=hash,charges=w.scientistCharges}
end
UnitManager.RequestOperation=function(unit,op,params)
 assert(unit:GetID()==4,'Military unit reached background request sink')
 w.unitRequests[#w.unitRequests+1]={unit=unit:GetID(),op=op,params=params}
end
UI.IsGameCoreBusy=function() return w.busy or false end
UI.IsProcessingMessages=function() return w.processing or false end
