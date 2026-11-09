-- Raw event observations only; this module cannot confirm or write a receipt.
local M={}
local function integer(v)return type(v)=='number'and v==v and v>=0 and v<=2147483647 and v%1==0 end
local function scalar(v)
 local t=type(v)
 return v==nil or t=='boolean'or(t=='string'and #v<=128)
  or(t=='number'and v==v and v~=math.huge and v~=-math.huge)
end
local function snapshot(value)
 assert(type(value)=='table'and getmetatable(value)==nil)
 local result,n={},0
 for k,v in pairs(value)do
  n=n+1;assert(n<=32 and type(k)=='string'and #k<=64 and scalar(v))
  result[k]=v
 end
 return result
end
function M.Install(E)
 assert(type(E)=='table'and getmetatable(E)==nil)
 local target,scope,read=E.unitID,E.scope,E.snapshot
 assert(integer(target)and type(scope)=='function'and type(read)=='function')
 local maximum=E.maxRecords;if maximum==nil then maximum=64 end
 assert(integer(maximum)and maximum>=1 and maximum<=128)
 local family=E.Events;assert(type(family)=='table'or type(family)=='userdata')
 local entries={}
 -- Resolve every binding before attaching the first callback.
 for _,name in ipairs({'UnitChargesChanged','UnitOperationStarted','UnitOperationDeactivated','UnitRemovedFromMap'})do
  local event=family[name];assert(type(event)=='table'or type(event)=='userdata')
  local add,remove=event.Add,event.Remove
  assert(type(add)=='function'and type(remove)=='function')
  entries[#entries+1]={name=name,add=add,remove=remove,attempted=false,removed=false}
 end
 local h={samples={},matches=0,ignored=0,errors=0,drops=0,removeErrors=0,active=false,restored=false}
 for _,entry in ipairs(entries)do
  local name=entry.name
  entry.callback=function(...)
   if not h.active then return end
   local argc=select('#',...);local pid,uid=...
   if pid~=0 or uid~=target then return end
   local args,valid={},argc<=8
   for i=1,math.min(argc,8)do
    local v=select(i,...)
    if scalar(v)then args[i]=v else valid=false end
   end
   local ok,turn=pcall(scope)
   if not ok then h.errors=h.errors+1;return end
   if not integer(turn)then h.ignored=h.ignored+1;return end
   h.matches=h.matches+1
   if #h.samples>=maximum then h.drops=h.drops+1;return end
   local row={event=name,turn=turn,argc=argc,args=args,snapshotStatus='UNKNOWN',
    observation='RAW_EVENT_NOT_RECEIPT_CONFIRMATION'}
   if valid then
    local good,value=pcall(function()return snapshot(read())end)
    if good then row.snapshotStatus='RAW';row.snapshot=value else h.errors=h.errors+1 end
   else h.errors=h.errors+1 end
   h.samples[#h.samples+1]=row
  end
 end
 function h.Restore()
  if h.restored then return true end
  h.active=false
  local all=true
  for _,entry in ipairs(entries)do
   if entry.attempted and not entry.removed then
    local ok,result=pcall(entry.remove,entry.callback)
    if ok and result~=false then entry.removed=true
    else all=false;h.removeErrors=h.removeErrors+1 end
   end
  end
  if all then h.restored=true end
  return all
 end
 for _,entry in ipairs(entries)do
  entry.attempted=true
  local ok,result=pcall(entry.add,entry.callback)
  if not ok or result==false then
   local cleaned=h.Restore()
   error('Missionary observer Add unavailable; cleanup acknowledged='..tostring(cleaned))
  end
 end
 h.active=true
 return h
end
return M
