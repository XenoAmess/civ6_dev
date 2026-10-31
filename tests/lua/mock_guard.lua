include=function() end
TestGuard={leader='LEADER_BAIQI',localPlayer=7,human=true,multi=false,unitCalls=0,cityCalls=0,playerCalls=0,cultureCalls=0}
local w=TestGuard
local culture={RequestChangeGovernment=function(self,hash) assert(self==w.culture);w.cultureCalls=w.cultureCalls+1;return hash,'native' end,
 RequestPolicyChanges=function(self,a,b) assert(self==w.culture);w.cultureCalls=w.cultureCalls+1 end,
 SetGovernmentChangeConsidered=function(self) w.cultureCalls=w.cultureCalls+1 end,
 GetSlotPolicy=function(self,index) assert(self==w.culture);return index,42 end}
w.culture=culture
local units={}
local player={GetCulture=function() return culture end,GetUnits=function() return {FindID=function(_,id) return units[id] end} end,
 GetTreasury=function(self) assert(self==w.player);return 'treasury',17 end}
w.player=player
Players={[7]=player}
PlayerConfigurations={[7]={GetLeaderTypeName=function() return w.leader end,IsHuman=function() return w.human end}}
Game={GetLocalPlayer=function() return w.localPlayer end}
GameConfiguration={IsAnyMultiplayer=function() return w.multi end}
GameInfo={Units={[0]={UnitType='UNIT_WARRIOR'},[1]={UnitType='UNIT_BUILDER'},[2]={UnitType='UNIT_SETTLER'},[3]={UnitType='UNIT_TRADER'}}}
function TestUnit(kind,owner,id)
 local unit={GetUnitType=function() return kind end,GetOwner=function() return owner or 7 end,GetID=function() return id or kind end}
 units[id or kind]=unit;return unit
end
function TestCity(owner) return {GetOwner=function() return owner end} end
UnitCommandTypes={ENTER_FORMATION=10,PARAM_UNIT_PLAYER='owner',PARAM_UNIT_ID='id'}
CityCommandTypes={RANGE_ATTACK=20,WMD_STRIKE=21,PURCHASE=22}
PlayerOperations={EXECUTE_SCRIPT=30,RESEARCH=31,PROGRESS_CIVIC=32,DIPLOMACY_MAKE_PEACE=33,LEVY_MILITARY=34}
UnitManager={}
for _,key in ipairs({'RequestOperation','RequestCommand','CanStartOperation','CanStartCommand'}) do
 UnitManager[key]=function(unit,action,params) w.unitCalls=w.unitCalls+1;w.lastUnit=unit;w.lastAction=action;return true,'native' end
end
CityManager={RequestOperation=function(city,op,params) w.cityCalls=w.cityCalls+1;return true end,
 RequestCommand=function(city,cmd,params) w.cityCalls=w.cityCalls+1;return true end}
UI={RequestPlayerOperation=function(pid,op,params) w.playerCalls=w.playerCalls+1;return true end}
