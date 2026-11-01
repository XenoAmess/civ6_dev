local w=TestAdmin
w.religion={id=-1,earned=2,pantheon=5,beliefs={},found={},claimed={},forbidden={},requests={},pending={}}
local r=w.religion
local function rows(data)
 local t={};for _,row in ipairs(data) do t[row.Index]=row;t[row.Hash]=row;t[row.BeliefType or row.ReligionType]=row end
 return setmetatable(t,{__call=function() local i=0;return function() i=i+1;return data[i] end end})
end
GameInfo.Religions=rows({{Index=0,Hash=500,ReligionType='RELIGION_CUSTOM',Pantheon=false,RequiresCustomName=true},
 {Index=2,Hash=502,ReligionType='RELIGION_PREDEFINED',Pantheon=false,RequiresCustomName=false},
 {Index=5,Hash=505,ReligionType='RELIGION_PANTHEON',Pantheon=true,RequiresCustomName=false}})
GameInfo.Beliefs=rows({{Index=0,Hash=600,BeliefType='BELIEF_WORK_ETHIC',BeliefClassType='BELIEF_CLASS_FOLLOWER'},
 {Index=1,Hash=601,BeliefType='BELIEF_TITHE',BeliefClassType='BELIEF_CLASS_FOUNDER'},
 {Index=2,Hash=602,BeliefType='BELIEF_DEFENDER_OF_FAITH',BeliefClassType='BELIEF_CLASS_ENHANCER'},
 {Index=3,Hash=603,BeliefType='BELIEF_OTHER_WORSHIP',BeliefClassType='BELIEF_CLASS_WORSHIP'},
 {Index=4,Hash=604,BeliefType='BELIEF_FEED_THE_WORLD',BeliefClassType='BELIEF_CLASS_FOLLOWER'},
 {Index=5,Hash=605,BeliefType='BELIEF_PANTHEON',BeliefClassType='BELIEF_CLASS_PANTHEON'}})
Players[7].GetReligion=function() return {GetPantheon=function() return r.pantheon end,CanCreatePantheon=function() return false end,
 GetReligionTypeCreated=function() return r.id end,GetNumBeliefsEarned=function() return r.earned end} end
local world={HasBeenFounded=function(_,index) return r.found[index] or false end,
 IsInSomePantheon=function(_,index) return index==5 end,IsInSomeReligion=function(_,index) return r.claimed[index] or false end,
 IsTooManyForReligion=function(_,index,religion) assert(religion==r.id);return r.forbidden[index] or false end,
 GetReligions=function() if r.missingList then return nil end;return r.id<0 and {} or {{Founder=7,Religion=r.id,Beliefs=r.beliefs}} end}
Game.GetReligion=function() return world end
PlayerOperations.FOUND_RELIGION=50;PlayerOperations.ADD_BELIEF=51
PlayerOperations.PARAM_RELIGION_TYPE='religion';PlayerOperations.PARAM_RELIGION_CUSTOM_NAME='custom'
PlayerOperations.PARAM_BELIEF_TYPE='belief'
local original=UI.RequestPlayerOperation
UI.RequestPlayerOperation=function(pid,op,params)
 if op~=50 and op~=51 then return original(pid,op,params) end
 assert(pid==7 and params.mode==PlayerOperations.VALUE_EXCLUSIVE)
 local req={op=op,params=params};r.requests[#r.requests+1]=req;r.pending[#r.pending+1]=req
end
function r.Apply()
 assert(#r.pending==1,'Each operation must wait for native state')
 local req=table.remove(r.pending,1)
 if req.op==50 then
  local row=GameInfo.Religions[req.params.religion]
  assert(r.id==-1 and row and not row.Pantheon and not r.found[row.Index])
  if row.RequiresCustomName then assert(type(req.params.custom)=='string' and #req.params.custom>0) end
  r.id=row.Index;r.found[row.Index]=true
 else
  local row=GameInfo.Beliefs[req.params.belief]
  assert(r.id>=0 and row and row.BeliefClassType~='BELIEF_CLASS_PANTHEON' and #r.beliefs<r.earned)
  assert(not r.claimed[row.Index] and not r.forbidden[row.Index])
  if #r.beliefs==0 then assert(row.BeliefClassType=='BELIEF_CLASS_FOLLOWER') end
  for _,index in ipairs(r.beliefs) do assert(GameInfo.Beliefs[index].BeliefClassType~=row.BeliefClassType) end
  r.beliefs[#r.beliefs+1]=row.Index;r.claimed[row.Index]=true
 end
end
