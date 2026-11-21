-- Passive own-project notifications only. Events do not establish rewards.
local M={}
local function integer(v)return type(v)=='number'and v>=0 and v<=2147483647 and v%1==0 end
function M.Install(E)
 assert(type(E)=='table'and getmetatable(E)==nil)
 local G,players,cfgs=assert(E.Game),assert(E.Players),assert(E.PlayerConfigurations)
 local cityID,projectID,first,last,maximum=E.cityID,E.projectIndex,E.minTurn,E.maxTurn,E.maxRecords
 assert(integer(cityID)and integer(projectID)and integer(first)and integer(last)and first<=last)
 assert(integer(maximum)and maximum>=1 and maximum<=128)
 local event=assert(E.Events.CityProjectCompleted);local add,remove=event.Add,event.Remove
 assert(type(add)=='function'and type(remove)=='function')
 local function Scope()
  local t=G.GetCurrentGameTurn();assert(integer(t)and t>=first and t<=last and G.GetLocalPlayer()==0)
  local cfg=assert(cfgs[0]);assert(cfg:IsHuman()==true and cfg:GetLeaderTypeName()=='LEADER_BAIQI')
  local c=assert(players[0]:GetCities():FindID(cityID));assert(c:GetID()==cityID and c:GetOwner()==0)
  return t
 end
 Scope()
 local h={samples={},matches=0,errors=0,drops=0,removeErrors=0,active=false,restored=false}
 local callback=function(...)
  local pid,cid,project=...
  if not h.active or pid~=0 or cid~=cityID or project~=projectID then return end
  h.matches=h.matches+1
  if #h.samples>=maximum then h.drops=h.drops+1;return end
  local r={playerID=pid,cityID=cid,projectID=project,arity=select('#',...),status='UNKNOWN',observation='NATIVE_COMPLETION_NOTIFICATION_ONLY_NOT_REWARD_ATTRIBUTION'}
  local ok,t=pcall(Scope)
  if ok then r.turn=t;r.status='KNOWN_EVENT_ONLY'else h.errors=h.errors+1;r.reason='scope_unavailable_or_changed'end
  h.samples[#h.samples+1]=r
 end
 function h.Restore()
  if h.restored then return true end
  h.active=false
  local ok,result=pcall(remove,callback)
  if not ok or result==false then h.removeErrors=h.removeErrors+1;return false end
  h.restored=true;return true
 end
 local ok,result=pcall(add,callback)
 if not ok or result==false then
  local good,value=pcall(remove,callback)
  error('Project observer Add unavailable; own cleanup acknowledgment='..tostring(good and value~=false))
 end
 h.active=true
 return h
end
return M
