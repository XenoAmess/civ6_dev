local w=TestAdmin
w.era={allowed=1,active={},pending={},requests={},remaining=false}
local e=w.era
local rows={{Index=0,Hash=800,CommemorationType='COMMEMORATION_SCIENTIFIC'},
 {Index=1,Hash=801,CommemorationType='COMMEMORATION_CULTURAL'},
 {Index=2,Hash=802,CommemorationType='COMMEMORATION_INFRASTRUCTURE'}}
GameInfo.CommemorationTypes={};for _,r in ipairs(rows) do GameInfo.CommemorationTypes[r.Index]=r end
Game.GetEras=function() return {
 GetPlayerNumAllowedCommemorations=function() return e.remaining and e.allowed-#e.active or e.allowed end,
 GetPlayerActiveCommemorations=function() return e.active end,
 GetPlayerCommemorateChoices=function() return {0,1,2} end} end
EndTurnBlockingTypes={ENDTURN_BLOCKING_COMMEMORATION_AVAILABLE=90}
NotificationManager={GetFirstEndTurnBlocking=function() return #e.active<e.allowed and 90 or 0 end}
PlayerOperations.COMMEMORATE=21;PlayerOperations.PARAM_COMMEMORATION_TYPE='commemoration'
local original=UI.RequestPlayerOperation
UI.RequestPlayerOperation=function(pid,op,params)
 if op~=21 then return original(pid,op,params) end
 assert(pid==7 and params.commemoration<10,'Native setter needs Index')
 e.requests[#e.requests+1]=params.commemoration;e.pending[#e.pending+1]=params.commemoration
end
function e.Apply()
 for _,index in ipairs(e.pending) do
  assert(#e.active<e.allowed)
  for _,old in ipairs(e.active) do assert(old~=index) end
  e.active[#e.active+1]=index
 end
 e.pending={}
end
