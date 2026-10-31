local w=TestAdmin
w.government={current=0,changed=false,free=true,can=true,requests={},pending={},anarchy={},locked={},retained=false}
local g=w.government
local function Rows(rows,key)
 local t={};for _,r in ipairs(rows) do t[r.Index]=r;t[r[key]]=r end
 return setmetatable(t,{__call=function() local i=0;return function() i=i+1;return rows[i] end end})
end
GameInfo.Governments=Rows({{Index=0,Hash=700,GovernmentType='GOVERNMENT_CHIEFDOM'},
 {Index=1,Hash=701,GovernmentType='GOVERNMENT_REPUBLIC'},
 {Index=2,Hash=702,GovernmentType='GOVERNMENT_OLIGARCHY'},
 {Index=3,Hash=703,GovernmentType='GOVERNMENT_MODERN'}},'GovernmentType')
GameInfo.Government_SlotCounts=Rows({
 {Index=0,GovernmentType='GOVERNMENT_CHIEFDOM',GovernmentSlotType='SLOT_MILITARY',NumSlots=2},
 {Index=1,GovernmentType='GOVERNMENT_REPUBLIC',GovernmentSlotType='SLOT_ECONOMIC',NumSlots=4},
 {Index=2,GovernmentType='GOVERNMENT_OLIGARCHY',GovernmentSlotType='SLOT_MILITARY',NumSlots=4},
 {Index=3,GovernmentType='GOVERNMENT_MODERN',GovernmentSlotType='SLOT_ECONOMIC',NumSlots=6}},'Index')
g.locked[703]=true
local culture=Players[7]:GetCulture()
culture.GetCurrentGovernment=function() return g.current end
culture.CanChangeGovernmentAtAll=function() return g.can end
culture.GovernmentChangeMade=function() return g.changed end
culture.CivicCompletedThisTurn=function() return g.free end
culture.IsGovernmentUnlocked=function(_,hash) assert(hash>=700);return not g.locked[hash] end
culture.GetAnarchyTurns=function(_,index) assert(index<10);return g.anarchy[index] or 0 end
culture.RequestChangeGovernment=function(_,hash)
 assert(hash>=700 and hash<710,'Request requires Hash')
 g.requests[#g.requests+1]=hash;g.pending[#g.pending+1]=hash
end
culture.SetGovernmentChangeConsidered=function(_,value) g.retained=value end
EndTurnBlockingTypes={ENDTURN_BLOCKING_CONSIDER_GOVERNMENT_CHANGE=88}
NotificationManager={GetFirstEndTurnBlocking=function() return g.blocker or 0 end}
function g.Apply()
 for _,hash in ipairs(g.pending) do
  assert(not g.locked[hash] and not g.changed and g.free and not g.anarchy[hash-700])
  g.current=hash-700;g.changed=true
 end
 g.pending={}
end
