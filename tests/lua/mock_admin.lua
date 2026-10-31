include=function() end
TestAdmin={turn=1,leader='LEADER_BAIQI',active=true,tech=-1,civic=-1,requests={},policyCalls=0,policyChanged=false,slots={-1,-1}}
local w=TestAdmin
local function Rows(rows)
 local t={};for _,r in ipairs(rows) do t[r.Index]=r;t[r.PolicyType or r.TechnologyType or r.CivicType or r.GovernmentSlotType]=r end
 return setmetatable(t,{__call=function() local i=0;return function() i=i+1;return rows[i] end end})
end
GameInfo={Technologies=Rows({{Index=0,Hash=100,TechnologyType='TECH_MINING'},{Index=1,Hash=101,TechnologyType='TECH_POTTERY'}}),
 Civics=Rows({{Index=0,Hash=200,CivicType='CIVIC_CODE_OF_LAWS'}}),
 Policies=Rows({{Index=0,Hash=300,PolicyType='POLICY_DISCIPLINE',GovernmentSlotType='SLOT_MILITARY'},
 {Index=1,Hash=301,PolicyType='POLICY_URBAN_PLANNING',GovernmentSlotType='SLOT_ECONOMIC'}}),
 GovernmentSlots=Rows({{Index=0,GovernmentSlotType='SLOT_MILITARY'},{Index=1,GovernmentSlotType='SLOT_ECONOMIC'}})}
local techs={GetResearchingTech=function() return w.tech end,HasTech=function() return false end,
 CanResearch=function() return true end,GetResearchCost=function() return 25 end,GetResearchPath=function(_,hash) return {hash} end}
local culture={GetProgressingCivic=function() return w.civic end,HasCivic=function() return false end,
 CanProgress=function() return true end,GetCultureCost=function() return 20 end,GetCivicPath=function(_,hash) return {hash} end,
 PolicyChangeMade=function() return w.policyChanged end,CivicCompletedThisTurn=function() return true end,
 GetNumPolicySlotsOpen=function() return 2 end,GetNumPolicySlots=function() return 2 end,
 GetSlotPolicy=function(_,i) return w.slots[i+1] end,GetSlotType=function(_,i) return i end,
 IsPolicyUnlocked=function() return true end,IsPolicyObsolete=function() return false end,
 CanSlotPolicy=function() error('Unqualified native signature must not be called') end,
 RequestPolicyChanges=function(_,clear,add) w.policyCalls=w.policyCalls+1;w.clear=clear;w.add=add end}
Players={[7]={IsTurnActive=function() return w.active end,GetTechs=function() return techs end,GetCulture=function() return culture end}}
PlayerConfigurations={[7]={GetLeaderTypeName=function() return w.leader end,IsHuman=function() return true end}}
Game={GetLocalPlayer=function() return 7 end,GetCurrentGameTurn=function() return w.turn end,IsAllowStrategicCommands=function() return true end}
GameConfiguration={IsAnyMultiplayer=function() return false end}
PlayerOperations={RESEARCH=1,PROGRESS_CIVIC=2,PARAM_TECH_TYPE='tech',PARAM_CIVIC_TYPE='civic',PARAM_INSERT_MODE='mode',VALUE_EXCLUSIVE=3}
UI={RequestPlayerOperation=function(pid,op,params) w.requests[#w.requests+1]={pid=pid,op=op,params=params} end}
