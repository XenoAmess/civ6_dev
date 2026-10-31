-- Actual, queued and delayed accepted military production packets.
local w=TestWorld;local o=w.objects
w.productionMode=true;w.withTrader=false;w.allowedMilitary={[200]=true,[205]=true,[206]=true}
w.armyTypes={};w.cityCount=2
local old=GameInfo.Units
local rows={
 {UnitType='UNIT_SCOUT',Index=0,Hash=200,Combat=10,PromotionClass='PROMOTION_CLASS_RECON',Domain='DOMAIN_LAND',Maintenance=0},
 old[1],old[2],old[3],
 {UnitType='UNIT_SLINGER',Index=5,Hash=205,Combat=5,RangedCombat=15,Domain='DOMAIN_LAND',Maintenance=0},
 {UnitType='UNIT_WARRIOR',Index=6,Hash=206,Combat=20,Domain='DOMAIN_LAND',Maintenance=0},
 {UnitType='UNIT_SWORDSMAN',Index=7,Hash=207,Combat=35,Domain='DOMAIN_LAND',Maintenance=2},
 {UnitType='UNIT_RAM',Index=8,Hash=208,FormationClass='FORMATION_CLASS_SUPPORT',Maintenance=0},
 {UnitType='UNIT_GALLEY',Index=9,Hash=209,Combat=25,Domain='DOMAIN_SEA',Maintenance=0},
 {UnitType='UNIT_CATAPULT',Index=10,Hash=210,Combat=23,Bombard=35,PromotionClass='PROMOTION_CLASS_SIEGE',Maintenance=0}}
GameInfo.Units=setmetatable({},{__index=function(_,key)
 for _,r in ipairs(rows) do if key==r.Index or key==r.Hash or key==r.UnitType then return r end end
end,__call=function() local i=0;return function() i=i+1;return rows[i] end end})
local function members(list)
 return function() local i=0;return function() i=i+1;if list[i] then return i,list[i] end end end
end
function o.player:GetUnits()
 local list={}
 for i,index in ipairs(w.armyTypes) do
  local kind,id=index,100+i
  list[#list+1]=setmetatable({GetID=function() return id end,GetUnitType=function() return kind end},{__index=o.army})
 end
 return {Members=members(list),FindID=function(_,id) for _,u in ipairs(list) do if u:GetID()==id then return u end end end}
end
local originalCities=o.player.GetCities
function o.player:GetCities()
 local cities=originalCities(self);cities.GetCount=function() return w.cityCount end;return cities
end
local originalQueue=o.city.GetBuildQueue
function o.city:GetBuildQueue()
 local q=originalQueue(self)
 q.CanProduce=function(_,hash) return w.allowedMilitary[hash]==true or (w.allowProject and hash==301) end
 return q
end
CityManager.CanStartOperation=function(city,op,params)
 return w.rejectMilitaryHash==nil or params[CityOperationTypes.PARAM_UNIT_TYPE]~=w.rejectMilitaryHash
end
