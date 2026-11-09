local M={}
local function number(v)return type(v)=='number'and v==v and v~=math.huge and v~=-math.huge end
local function integer(v)return number(v)and v>=0 and v<=2147483647 and v%1==0 end
local function dense(list)
 if type(list)~='table'or getmetatable(list)~=nil then return nil end
 local n,max=0,0
 for k in pairs(list)do n=n+1;if n>128 or not integer(k)or k<1 or k>128 then return nil end;max=math.max(max,k)end
 if n~=max then return nil end
 return n
end
function M.Read(E)
 local ok,result=pcall(function()
  assert(type(E)=='table'and getmetatable(E)==nil,'environment')
  local G=assert(E.Game);local t=G.GetCurrentGameTurn();assert(integer(t)and t>=179 and t<=210,'turn')
  assert(G.GetLocalPlayer()==0,'player')
  local cfg=assert(E.PlayerConfigurations[0]);assert(cfg:IsHuman()==true and cfg:GetLeaderTypeName()=='LEADER_BAIQI','leader')
  local p=assert(E.Players[0]);local gi=assert(E.GameInfo);local yt=assert(E.YieldTypes)
  assert(integer(yt.GOLD)and integer(yt.FAITH)and yt.GOLD~=yt.FAITH,'yield')
  local religion=assert(p:GetReligion());local treasury=assert(p:GetTreasury())
  local gold,faith=treasury:GetGoldBalance(),religion:GetFaithBalance()
  assert(number(gold)and number(faith)and faith>=0,'balances')
  local cls=assert(gi.GreatPersonClasses.GREAT_PERSON_CLASS_PROPHET)
  assert(integer(cls.Index)and cls.GreatPersonClassType=='GREAT_PERSON_CLASS_PROPHET','class')
  local gp=assert(G.GetGreatPeople());local timeline=gp:GetTimeline();local size=dense(timeline)
  assert(size~=nil,'timeline')
  local entries,seen={},{}
  for i=1,size do
   local row=timeline[i]
   assert(type(row)=='table'and getmetatable(row)==nil and integer(row.Class),'row')
   if row.Class==cls.Index then
    local id=row.Individual
    assert(integer(id)and not seen[id]and(row.Claimant==nil or integer(row.Claimant)),'prophet row')
    local def=assert(gi.GreatPersonIndividuals[id])
    assert(def.Index==id and def.GreatPersonClassType=='GREAT_PERSON_CLASS_PROPHET','individual')
    seen[id]=true
    if row.Claimant==nil then entries[#entries+1]=id end
   end
  end
  local function cost(v)
   if v==nil then return 'UNKNOWN',nil end
   assert(number(v)and v>=0,'cost')
   return 'KNOWN',v
  end
  local quotes={}
  for _,id in ipairs(entries)do
   local recruit=gp:CanRecruitPerson(0,id)
   local canGold=gp:CanPatronizePerson(0,id,yt.GOLD)
   local canFaith=gp:CanPatronizePerson(0,id,yt.FAITH)
   assert(type(recruit)=='boolean'and type(canGold)=='boolean'and type(canFaith)=='boolean','eligibility')
   local goldStatus,goldCost=cost(gp:GetPatronizeCost(0,id,yt.GOLD))
   local faithStatus,faithCost=cost(gp:GetPatronizeCost(0,id,yt.FAITH))
   quotes[#quotes+1]={individual=id,canRecruit=recruit,canGold=canGold,canFaith=canFaith,
    goldCostStatus=goldStatus,faithCostStatus=faithStatus,goldCost=goldCost,faithCost=faithCost}
  end
  assert(G.GetLocalPlayer()==0 and G.GetCurrentGameTurn()==t and cfg:IsHuman()==true
   and cfg:GetLeaderTypeName()=='LEADER_BAIQI'and treasury:GetGoldBalance()==gold
   and religion:GetFaithBalance()==faith,'changed while reading')
  return {status='KNOWN',turn=t,gold=gold,faith=faith,quotes=quotes}
 end)
 if not ok then return {status='UNKNOWN',reason='unavailable_or_invalid_native_data'}end
 return result
end
return M
