-- Stateful consumer: queued operations apply only when the test acknowledges them.
local w=TestAdmin
w.gov={points=2,spent=0,owned={},pending={},requests={},illegal={},neutralized=0,appoint=true}
local g=w.gov
local function Rows(rows,key)
 local t={};for _,r in ipairs(rows) do t[r.Index]=r;t[r[key]]=r end
 return setmetatable(t,{__call=function() local i=0;return function() i=i+1;return rows[i] end end})
end
GameInfo.Governors=Rows({{Index=3,Hash=930,GovernorType='GOVERNOR_THE_RESOURCE_MANAGER'},
 {Index=4,Hash=940,GovernorType='GOVERNOR_SECRET'},
 {Index=5,Hash=950,GovernorType='GOVERNOR_UNAVAILABLE'}},'GovernorType')
GameInfo.GovernorsCannotAssign=Rows({{Index=0,GovernorType='GOVERNOR_SECRET',CannotAssign=true}},'GovernorType')
GameInfo.GovernorPromotions=Rows({{Index=9,Hash=990,GovernorPromotionType='PROMOTION_REAL',BaseAbility=false}},'GovernorPromotionType')
GameInfo.GovernorPromotionSets=Rows({{Index=0,GovernorType='GOVERNOR_THE_RESOURCE_MANAGER',GovernorPromotion='PROMOTION_REAL'}},'GovernorType')
local cities={}
for i=1,2 do
 local id=i
 cities[i]={GetID=function() return id end,GetOwner=function() return 7 end,GetPopulation=function() return id*3 end}
end
g.cities=cities
local pg={}
function pg:GetGovernorPoints() return g.points end
function pg:GetGovernorPointsSpent() return g.spent end
function pg:GetAssignedGovernor(city)
 for _,v in pairs(g.owned) do if v.city==city then return v end end
end
function pg:GetGovernorList()
 local list={};for _,v in pairs(g.owned) do list[#list+1]=v end
 return #list>0,list
end
function pg:HasGovernor(hash) assert(hash==930 or hash==940 or hash==950);return g.owned[hash]~=nil end
function pg:CanEverAppointGovernor(hash) return hash~=950 end
function pg:CanAppoint() return g.appoint and g.points>g.spent end
function pg:CanAssignGovernor(hash,city,report)
 assert(hash==930 and report==true)
 return g.owned[hash]~=nil and not g.illegal[city:GetID()]
end
function pg:CanPromoteGovernor(hash) return g.owned[hash]~=nil and g.points>g.spent end
function pg:CanEarnPromotion(hash,promotion) assert(promotion==990);return self:CanPromoteGovernor(hash) and not g.owned[hash].promoted end
Players[7].GetGovernors=function() return pg end
Players[7].GetCities=function() return {Members=function() local i=0;return function() i=i+1;if cities[i] then return i,cities[i] end end end} end
PlayerOperations.APPOINT_GOVERNOR=10;PlayerOperations.ASSIGN_GOVERNOR=11;PlayerOperations.PROMOTE_GOVERNOR=12
PlayerOperations.PARAM_GOVERNOR_TYPE='governor';PlayerOperations.PARAM_PLAYER_ONE='owner'
PlayerOperations.PARAM_CITY_DEST='city';PlayerOperations.PARAM_GOVERNOR_PROMOTION_TYPE='promotion'
local original=UI.RequestPlayerOperation
UI.RequestPlayerOperation=function(pid,op,params)
 if op<10 then return original(pid,op,params) end
 assert(pid==7 and params.governor==3,'Setter requires Index, not Hash')
 local request={pid=pid,op=op,params=params}
 g.requests[#g.requests+1]=request;g.pending[#g.pending+1]=request
end
function g.Apply()
 for _,r in ipairs(g.pending) do
  if r.op==10 then
   assert(g.points>g.spent and not g.owned[930]);g.spent=g.spent+1
   local v={GetType=function() return 3 end,GetNeutralizedTurns=function() return g.neutralized end}
   v.GetAssignedCity=function() return v.city end;v.HasPromotion=function(_,hash) assert(hash==990);return v.promoted end
   g.owned[930]=v
  elseif r.op==11 then
   assert(r.params.owner==7 and not g.illegal[r.params.city]);g.owned[930].city=cities[r.params.city]
  else
   assert(r.params.promotion==9 and g.points>g.spent);g.spent=g.spent+1;g.owned[930].promoted=true
  end
 end
 g.pending={}
end
