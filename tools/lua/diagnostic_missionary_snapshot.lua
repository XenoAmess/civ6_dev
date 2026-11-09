-- UI exports only: unit religion/charges are flat methods in this context.
local M={}
local function Int(v,lo,hi)
 return type(v)=='number'and v>=lo and v<=hi and v%1==0
end
local function Finite(v)
 return type(v)=='number'and v==v and v>=0 and v<math.huge
end
local function Dense(t,max)
 assert(type(t)=='table'and getmetatable(t)==nil)
 local n,high=0,0
 for k in pairs(t)do n=n+1;assert(n<=max and Int(k,1,max));high=math.max(high,k)end
 assert(n==high);return n
end
local function Scope(E)
 local g=E.Game;local t=g.GetCurrentGameTurn()
 assert(Int(t,130,160)and g.GetLocalPlayer()==0)
 assert(E.GameConfiguration.IsAnyMultiplayer()==false)
 if E.GameConfiguration.IsHotseat~=nil then assert(E.GameConfiguration.IsHotseat()==false)end
 local cfg=E.PlayerConfigurations[0];local p=E.Players[0]
 assert(cfg:IsHuman()==true and cfg:GetLeaderTypeName()=='LEADER_BAIQI')
 assert(p:IsTurnActive()==true and g.IsAllowStrategicCommands(0)==true
  and E.UI.IsGameCoreBusy()==false and E.UI.IsProcessingMessages()==false)
 return t,p
end
local function Collect(E)
 local t,p=Scope(E);local religion=p:GetReligion()
 local created,faith=religion:GetReligionTypeCreated(),religion:GetFaithBalance()
 assert(Int(created,0,2147483647)and Finite(faith))
 local result={turn=t,rows={{'OWN',created,faith}}};local cs,seen,n={}, {},0
 local cities=p:GetCities();local expected=cities:GetCount();assert(Int(expected,1,256))
 for _,c in cities:Members()do
  n=n+1;assert(n<=expected and c:GetOwner()==0)
  local id,x,y,pop=c:GetID(),c:GetX(),c:GetY(),c:GetPopulation()
  assert(Int(id,0,2147483647)and not seen[id]and Int(x,0,2147483647)
   and Int(y,0,2147483647)and Int(pop,1,1000000));seen[id]=true
  local cr=c:GetReligion();local majority=cr:GetMajorityReligion();assert(Int(majority,-1,2147483647))
  local list=cr:GetReligionsInCity();local count=Dense(list,64);local fol,rs,total={}, {},0
  for i=1,count do
   local f=list[i];local r,v=f.Religion,f.Followers
   -- Native UI lists unaffiliated citizens as Religion=-1, including zero rows.
   assert(Int(r,-1,2147483647)and not rs[r]and Int(v,0,pop));rs[r]=true;total=total+v
   assert(total<=pop);fol[#fol+1]={'FOLLOWER',id,r,v}
  end
  table.sort(fol,function(a,b)return a[3]<b[3]end)
  cs[#cs+1]={id=id,row={'CITY',id,x,y,pop,majority},fol=fol}
 end
 assert(n==expected and cities:GetCount()==expected)
 table.sort(cs,function(a,b)return a.id<b.id end)
 for _,c in ipairs(cs)do result.rows[#result.rows+1]=c.row;for _,r in ipairs(c.fol)do result.rows[#result.rows+1]=r end end
 local us={};seen={};n=0
 for _,u in p:GetUnits():Members()do
  n=n+1;assert(n<=4096 and u:GetOwner()==0)
  local id,index=u:GetID(),u:GetUnitType();assert(Int(id,0,2147483647)and not seen[id]and Int(index,0,2147483647));seen[id]=true
  local def=assert(E.GameInfo.Units[index]);assert(type(def.UnitType)=='string')
  if def.UnitType=='UNIT_MISSIONARY'then
   local dead=u:IsDelayedDeath();assert(type(dead)=='boolean')
   if not dead then
    local x,y,r,ch,mv,fm=u:GetX(),u:GetY(),u:GetReligionType(),u:GetSpreadCharges(),u:GetMovesRemaining(),u:GetFormationUnitCount()
    assert(Int(x,0,2147483647)and Int(y,0,2147483647)and Int(r,0,2147483647)
     and Int(ch,0,1000000)and Finite(mv)and Int(fm,1,64)and #us<256)
    us[#us+1]={'UNIT',id,x,y,r,ch,mv,fm}
   end
  end
 end
 table.sort(us,function(a,b)return a[2]<b[2]end)
 for _,r in ipairs(us)do result.rows[#result.rows+1]=r end
 local after,actual=Scope(E);assert(after==t and actual==p
  and p:GetReligion():GetReligionTypeCreated()==created and p:GetReligion():GetFaithBalance()==faith)
 return result
end
function M.Read(E)
 local ok,r=pcall(function()
  local a,b=Collect(E),Collect(E);assert(a.turn==b.turn and #a.rows==#b.rows)
  for i,row in ipairs(a.rows)do assert(#row==#b.rows[i]);for k,v in ipairs(row)do assert(v==b.rows[i][k])end end
  return {status='KNOWN',turn=b.turn,rows=b.rows}
 end)
 return ok and r or{status='UNKNOWN'}
end
return M
