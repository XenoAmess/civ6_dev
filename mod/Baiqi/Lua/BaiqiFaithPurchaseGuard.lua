local G={}
local MAX=2147483647
local function Object(v)return type(v)=='table'or type(v)=='userdata'end
local function Integer(n)return type(n)=='number'and n==n and n>=0 and n<=MAX and n%1==0 end
local function Key(k)return type(k)=='string'and #k>0 and #k<=128 end
function G.Open(E,player,pid)
 local function Read()
  assert(Object(E)and Integer(pid)and Object(E.Config)and Object(player)and type(player.GetProperty)=='function')
  local nk,mk=E.Config.naturalistPurchaseIntentKey,E.Config.missionaryPurchaseIntentKey
  assert(Key(nk)and Key(mk)and nk~=mk)
  local js={E.NaturalistJournal,E.MissionaryJournal};local keys={nk,mk}
  for _,j in ipairs(js)do
   assert(Object(j)and type(j.Validate)=='function'and type(j.Clone)=='function'and type(j.Equal)=='function')
  end
  assert(js[1]~=nil and js[2]~=nil)
  local function Snapshot(j,key)
   local value=player:GetProperty(key)
   if value==nil then return{absent=true}end
   assert(j.Validate(value,pid)==true)
   local copy=j.Clone(value,pid);assert(copy~=nil and j.Validate(copy,pid)==true)
   return{absent=false,state=copy}
  end
  local before={}
  for i=1,2 do before[i]=Snapshot(js[i],keys[i])end
  for i=1,2 do
   local after=Snapshot(js[i],keys[i]);local old=before[i]
   assert(old.absent==after.absent)
   if not after.absent then
    assert(js[i].Equal(old.state,after.state,pid)==true)
    for _,op in pairs(after.state.operations)do if op.stage=='ARMED'then return false end end
   end
  end
  return true
 end
 local ok,result=pcall(Read);return ok and result==true
end
BaiqiFaithPurchaseGuard=G
return G
