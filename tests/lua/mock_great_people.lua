local w=TestAdmin
w.people={points=120,claimed={},pending={},requests={},units={}}
local p=w.people
Game.GetGreatPeople=function() return {
 GetTimeline=function() return {{Individual=7,Cost=60},{Individual=8,Cost=60}} end,
 CanRecruitPerson=function(_,pid,index) assert(pid==7 and (index==7 or index==8));return not p.claimed[index] and p.points>=60 end} end
PlayerOperations.RECRUIT_GREAT_PERSON=22;PlayerOperations.PARAM_GREAT_PERSON_INDIVIDUAL_TYPE='individual'
local original=UI.RequestPlayerOperation
UI.RequestPlayerOperation=function(pid,op,params)
 if op~=22 then return original(pid,op,params) end
 assert(pid==7 and (params.individual==7 or params.individual==8))
 assert(params.yield==nil,'Normal recruitment must not use gold or faith patronage')
 p.requests[#p.requests+1]=params.individual;p.pending[#p.pending+1]=params.individual
end
UnitManager={RequestOperation=function() error('Recruitment must not command armies or great people') end}
function p.Apply()
 for _,index in ipairs(p.pending) do
  assert(not p.claimed[index] and p.points>=60)
  p.claimed[index]=true;p.points=p.points-60;p.units[#p.units+1]=index
 end
 p.pending={}
end
