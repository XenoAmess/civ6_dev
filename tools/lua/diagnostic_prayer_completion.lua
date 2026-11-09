-- Own completion notification plus a best-effort snapshot, never reward attribution.
local M={}
local function finite(v)return type(v)=='number'and v==v and v~=math.huge and v~=-math.huge end
local function integer(v)return finite(v)and v>=0 and v<=2147483647 and v%1==0 end
function M.Install(E)
 assert(type(E)=='table'and getmetatable(E)==nil)
 local G,players,cfgs,gi=assert(E.Game),assert(E.Players),assert(E.PlayerConfigurations),assert(E.GameInfo)
 local target=E.cityID;assert(integer(target))
 local maximum=E.maxRecords;if maximum==nil then maximum=32 end
 assert(integer(maximum)and maximum>=1 and maximum<=128)
 local project=assert(gi.Projects.PROJECT_ENHANCE_DISTRICT_HOLY_SITE)
 assert(project.ProjectType=='PROJECT_ENHANCE_DISTRICT_HOLY_SITE'and integer(project.Index))
 local cls=assert(gi.GreatPersonClasses.GREAT_PERSON_CLASS_PROPHET)
 assert(integer(cls.Index)and cls.GreatPersonClassType=='GREAT_PERSON_CLASS_PROPHET')
 local event=assert(E.Events.CityProjectCompleted);local add,remove=event.Add,event.Remove
 assert(type(add)=='function'and type(remove)=='function')
 local function scope()
  local turn=G.GetCurrentGameTurn()
  if not integer(turn)or turn<99 or turn>250 or G.GetLocalPlayer()~=0 then return nil end
  local cfg=cfgs[0]
  if not cfg or cfg:IsHuman()~=true or cfg:GetLeaderTypeName()~='LEADER_BAIQI'then return nil end
  local p=players[0];if not p then return nil end
  local city=p:GetCities():FindID(target)
  if not city or city:GetID()~=target or city:GetOwner()~=0 then return nil end
  return p,turn
 end
 assert(scope(),'own scope unavailable')
 local h={samples={},matches=0,ignored=0,errors=0,drops=0,removeErrors=0,active=false,restored=false}
 local function own(p)
  local r=assert(p:GetReligion());local pts=assert(p:GetGreatPeoplePoints())
  local value={created=r:GetReligionTypeCreated(),earned=r:GetNumBeliefsEarned(),held=r:HasReligiousFoundingUnit(),
   faith=r:GetFaithBalance(),points=pts:GetPointsTotal(cls.Index),perTurn=pts:GetPointsPerTurn(cls.Index)}
  assert(value.created==-1 or integer(value.created));assert(integer(value.earned)and type(value.held)=='boolean')
  for _,key in ipairs({'faith','points','perTurn'})do assert(finite(value[key])and value[key]>=0)end
  return value
 end
 local callback
 callback=function(playerID,cityID,projectID)
  if not h.active or playerID~=0 or cityID~=target or projectID~=project.Index then return end
  local ok,record=pcall(function()
   local p,turn=scope();if not p then h.ignored=h.ignored+1;return nil end
   h.matches=h.matches+1
   if #h.samples>=maximum then h.drops=h.drops+1;return nil end
   local row={playerID=playerID,cityID=cityID,projectID=projectID,turn=turn,status='UNKNOWN',
    observation='COMPLETION_CALLBACK_NOT_REWARD_ATTRIBUTION'}
   local good,snapshot=pcall(function()
    local a,b=own(p),own(p)
    for key,value in pairs(a)do assert(b[key]==value,'own state changed')end
    local current,t=scope();assert(current==p and t==turn,'scope changed')
    return a
   end)
   if good then row.status='KNOWN';row.own=snapshot
   else h.errors=h.errors+1;row.reason='own_snapshot_unavailable_or_changed'end
   return row
  end)
  if ok then
   if record then h.samples[#h.samples+1]=record end
  else h.errors=h.errors+1 end
 end
 function h.Restore()
  if h.restored then return true end
  local ok,result=pcall(remove,callback)
  if not ok or result==false then h.removeErrors=h.removeErrors+1;return false end
  h.active=false;h.restored=true;return true
 end
 local ok,result=pcall(add,callback)
 if not ok or result==false then
  h.active=false;local cleaned,removed=pcall(remove,callback)
  error('Project observer Add unavailable; cleanup acknowledgment='..tostring(cleaned and removed~=false))
 end
 h.active=true
 return h
end
return M
