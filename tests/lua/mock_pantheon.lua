local w=TestAdmin
w.faith={pantheon=-1,can=true,balance=50,claimed={},inReligion={},requests={},pending={}}
local f=w.faith
local rows={
 {Index=0,Hash=501,BeliefType='BELIEF_FOLLOWER',BeliefClassType='BELIEF_CLASS_FOLLOWER'},
 {Index=2,Hash=502,BeliefType='BELIEF_CITY_PATRON_GODDESS',BeliefClassType='BELIEF_CLASS_PANTHEON'},
 {Index=5,Hash=505,BeliefType='BELIEF_GOD_OF_THE_FORGE',BeliefClassType='BELIEF_CLASS_PANTHEON'}}
GameInfo.Beliefs=setmetatable({},{__call=function() local i=0;return function() i=i+1;return rows[i] end end})
Players[7].GetReligion=function() return {
 GetPantheon=function() return f.pantheon end,
 CanCreatePantheon=function() return f.can and f.pantheon==-1 and f.balance>=25 end} end
Game.GetReligion=function() return {
 IsInSomePantheon=function(_,index) return f.claimed[index] end,
 IsInSomeReligion=function(_,index) return f.inReligion[index] end} end
PlayerOperations.FOUND_PANTHEON=20;PlayerOperations.PARAM_BELIEF_TYPE='belief'
local original=UI.RequestPlayerOperation
UI.RequestPlayerOperation=function(pid,op,params)
 if op~=20 then return original(pid,op,params) end
 assert(pid==7 and params.mode==PlayerOperations.VALUE_EXCLUSIVE)
 f.requests[#f.requests+1]=params;f.pending[#f.pending+1]=params
end
function f.Apply()
 for _,params in ipairs(f.pending) do
  for _,row in ipairs(rows) do
   if row.Hash==params.belief then
    assert(row.BeliefClassType=='BELIEF_CLASS_PANTHEON' and not f.claimed[row.Index] and not f.inReligion[row.Index])
    assert(f.pantheon==-1 and f.balance>=25)
    f.balance=f.balance-25;f.pantheon=row.Index;f.claimed[row.Index]=true
   end
  end
 end
 f.pending={}
end
