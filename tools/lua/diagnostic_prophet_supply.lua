-- Public supply/award observations only. No recruitment or spending authority.
local M={}
local function number(v)return type(v)=='number'and v==v and v~=math.huge and v~=-math.huge end
local function integer(v)return number(v)and v>=0 and v<=2147483647 and v%1==0 end
local function dense(list,max)
 if type(list)~='table'or getmetatable(list)~=nil then return nil end
 local n,highest=0,0
 for k in pairs(list)do
  n=n+1;if n>max or not integer(k)or k<1 or k>max then return nil end
  highest=math.max(highest,k)
 end
 if n~=highest then return nil end
 return n
end
function M.Read(E)
 local ok,result=pcall(function()
  assert(type(E)=='table'and getmetatable(E)==nil,'environment')
  local G=assert(E.Game);local t=G.GetCurrentGameTurn()
  assert(integer(t)and t>=150 and t<=250 and G.GetLocalPlayer()==0,'local context')
  local cfg=assert(E.PlayerConfigurations[0])
  assert(cfg:IsHuman()==true and cfg:GetLeaderTypeName()=='LEADER_BAIQI','leader')
  local p=assert(E.Players[0]);local gi=assert(E.GameInfo)
  local cls=assert(gi.GreatPersonClasses.GREAT_PERSON_CLASS_PROPHET)
  assert(integer(cls.Index)and cls.GreatPersonClassType=='GREAT_PERSON_CLASS_PROPHET','class')
  local religion=assert(p:GetReligion());local points=assert(p:GetGreatPeoplePoints())
  local function ownSnapshot()
   local own={created=religion:GetReligionTypeCreated(),earned=religion:GetNumBeliefsEarned(),
    hasProphet=religion:HasReligiousFoundingUnit(),faith=religion:GetFaithBalance(),
    points=points:GetPointsTotal(cls.Index),perTurn=points:GetPointsPerTurn(cls.Index)}
   assert(own.created==-1 or integer(own.created),'created')
   assert(integer(own.earned)and type(own.hasProphet)=='boolean','own status')
   for _,key in ipairs({'faith','points','perTurn'})do assert(number(own[key])and own[key]>=0,'own number')end
   return own
  end
  local own=ownSnapshot()
  local function definition(id)
   assert(integer(id),'individual')
   local row=assert(gi.GreatPersonIndividuals[id])
   assert(row.Index==id and row.GreatPersonClassType=='GREAT_PERSON_CLASS_PROPHET','definition')
  end
  local people=assert(G.GetGreatPeople())
  local timeline=people:GetTimeline();local count=dense(timeline,128);assert(count~=nil,'timeline')
  local current
  for i=1,count do
   local row=timeline[i]
   assert(type(row)=='table'and getmetatable(row)==nil and integer(row.Class),'current row')
   if row.Class==cls.Index then
    assert(current==nil,'duplicate current class')
    local id,claimant=row.Individual,row.Claimant
    if id==nil then
     assert(claimant==nil,'claimant without individual')
     current={supplyState='NONE_AVAILABLE'}
    else
     definition(id);assert(claimant==nil or integer(claimant),'claimant')
     current={supplyState=claimant==nil and'UNCLAIMED'or'CLAIMED',individual=id,claimant=claimant}
    end
   end
  end
  assert(current~=nil,'missing current class')
  local history=people:GetPastTimeline();count=dense(history,512);assert(count~=nil,'past timeline')
  local past,seen={},{}
  for i=1,count do
   local row=history[i]
   assert(type(row)=='table'and getmetatable(row)==nil and integer(row.Class),'past row')
   -- The shipped past tab filters unclaimed rows from GetPastTimeline too.
   if row.Class==cls.Index and row.Claimant~=nil then
    local id=row.Individual;definition(id)
    assert(not seen[id]and integer(row.Claimant),'past identity');seen[id]=true
    local granted=row.TurnGranted
    assert(granted==nil or(integer(granted)and granted<=t),'past turn')
    past[#past+1]={individual=id,claimant=row.Claimant,turnGranted=granted}
   end
  end
  local fresh=ownSnapshot()
  for key,value in pairs(own)do assert(fresh[key]==value,'own changed')end
  assert(G.GetLocalPlayer()==0 and G.GetCurrentGameTurn()==t and cfg:IsHuman()==true
   and cfg:GetLeaderTypeName()=='LEADER_BAIQI','context changed')
  return {status='KNOWN',turn=t,own=own,current=current,pastProphets=past}
 end)
 if not ok then return {status='UNKNOWN',reason='unavailable_or_invalid_public_supply_data'}end
 return result
end
return M
