-- Passive finite target metadata. Never filter or retry the original call.
local M={}
local function Pack(...)return{n=select('#',...),...}end
local function Integer(v)return type(v)=='number'and v==v and v>=0 and v<=2147483647 and v%1==0 end
local function Scalar(v)local t=type(v);return t=='string'or t=='boolean'or(t=='number'and v==v and v~=math.huge and v~=-math.huge)end
function M.Install(o)
 assert(type(o)=='table'and type(o.context)=='string'and type(o.getPublished)=='function'and type(o.publish)=='function'and type(o.getManager)=='function'and type(o.unpack)=='function'and type(o.game)=='table'and type(o.game.GetCurrentGameTurn)=='function'and type(o.game.GetLocalPlayer)=='function')
 assert(o.getPublished()==nil,'Occupied diagnostic namespace')
 local cap=o.capacity or 256;assert(Integer(cap)and cap>=1 and cap<=1024)
 local s={writeCalls=0,tickCalls=0,metadataErrors=0,afterErrors=0,dropped=0,rows={},ticks={},active=true,retired=false}
 local bindings={}
 local planningScope,scopeDepth=nil,0
 local function Copy(value,depth,seen,budget)
  if value==nil or Scalar(value)then return value end
  assert(type(value)=='table'and depth<4 and not seen[value],'Unsupported diagnostic parameter')
  seen[value]=true;local result={}
  for k,v in pairs(value)do budget.n=budget.n+1;assert(budget.n<=128 and Scalar(k),'Parameter observation bound');result[k]=Copy(v,depth+1,seen,budget)end
  seen[value]=nil;return result
 end
 local function Before(b,args)
  if b.kind=='TICK'then
   s.tickCalls=s.tickCalls+1;local r=b.summary;r.calls=r.calls+1;r.argumentCount=args.n
   local ok,err=pcall(function()
    local turn,owner=o.game.GetCurrentGameTurn(),o.game.GetLocalPlayer();assert(Integer(turn)and Integer(owner),'Unknown planning authority')
    r.firstTurn=r.firstTurn or turn;r.lastTurn=turn;r.localPlayer=owner
    if r.owners[owner]==nil then r.ownerCount=r.ownerCount+1;assert(r.ownerCount<=128,'Planning owner bound');r.owners[owner]=0 end
    r.owners[owner]=r.owners[owner]+1;r.metadataKnown=true
   end)
   if not ok then s.metadataErrors=s.metadataErrors+1;r.metadataErrors=r.metadataErrors+1;r.metadataKnown=false;r.metadataErrorType=type(err)end
   return r
  end
  s.writeCalls=s.writeCalls+1
  if #s.rows>=cap then s.dropped=s.dropped+1;return nil end
  local row={sequence=#s.rows+1,context=o.context,domain=b.domain,method=b.key,kind=b.kind,argumentCount=args.n,metadataKnown=false,returned=false,planningScope=planningScope or'UNSCOPED',scopeDepth=scopeDepth};s.rows[#s.rows+1]=row
  local ok,err=pcall(function()
   row.turn=o.game.GetCurrentGameTurn();row.localPlayer=o.game.GetLocalPlayer();assert(Integer(row.turn)and Integer(row.localPlayer),'Unknown current authority')
   if b.kind=='ACTOR'then
    local actor=args[1];assert((type(actor)=='table'or type(actor)=='userdata')and type(actor.GetID)=='function'and type(actor.GetOwner)=='function','Unknown actor')
    row.id=actor:GetID();row.owner=actor:GetOwner();assert(Integer(row.id)and Integer(row.owner),'Unknown actor identity')
   elseif b.kind=='PLAYER'then row.id=args[1];row.owner=args[1];assert(Integer(row.owner),'Unknown player')
   else row.owner=row.localPlayer end
   if b.kind~='TICK'then
    local op=args[2];assert(type(op)=='number'and op==op and op>=-2147483648 and op<=4294967295 and op%1==0,'Unknown operation');row.operation=op;row.params=Copy(args[3],0,{},{n=0})
   end
   row.metadataKnown=true
  end)
  if not ok then s.metadataErrors=s.metadataErrors+1;row.metadataErrorType=type(err)end
  return row
 end
 local function Build(domain,key,kind,target)
  assert(type(domain)=='string'and type(key)=='string'and(kind=='ACTOR'or kind=='PLAYER'or kind=='TICK')and type(target)=='table'and type(target[key])=='function')
  for _,b in ipairs(bindings)do assert(not(b.target==target and b.key==key),'Duplicate observed binding')end
  local b={domain=domain,key=key,kind=kind,target=target,original=target[key]}
  b.wrapper=function(...)
   if not s.active or s.paused then return b.original(...)end
   local args=Pack(...);local known,row=pcall(Before,b,args)
   if not known then s.metadataErrors=s.metadataErrors+1;row=nil end
   local ret
   if b.kind=='TICK'then
    local priorScope,priorDepth=planningScope,scopeDepth;planningScope=b.domain..'.'..b.key;scopeDepth=scopeDepth+1
    ret=Pack(pcall(b.original,...));planningScope,scopeDepth=priorScope,priorDepth
    if not ret[1]then error(ret[2],0)end
   else ret=Pack(b.original(...))end
   if row then local ok=pcall(function()
    if b.kind=='TICK'then row.returned=row.returned+1;row.lastReturnCount=ret.n-1 else row.returned=true;row.returnCount=ret.n end
   end);if not ok then s.afterErrors=s.afterErrors+1 end end
   return o.unpack(ret,b.kind=='TICK'and 2 or 1,ret.n)
  end
  return b
 end
 local specs={{'UnitManager','RequestOperation','ACTOR'},{'UnitManager','RequestCommand','ACTOR'},{'CityManager','RequestOperation','ACTOR'},{'CityManager','RequestCommand','ACTOR'},{'UI','RequestPlayerOperation','PLAYER'}}
 for _,v in ipairs(specs)do bindings[#bindings+1]=Build(v[1],v[2],v[3],o.getManager(v[1]))end
 local function Rollback()
  for _,b in ipairs(bindings)do if b.target[b.key]==b.wrapper then b.target[b.key]=b.original end end
  local ok,value=pcall(o.getPublished);if ok and value==s then pcall(o.publish,nil)end
 end
 local ok,err=pcall(function()
  for _,b in ipairs(bindings)do b.target[b.key]=b.wrapper;assert(b.target[b.key]==b.wrapper)end
  o.publish(s);assert(o.getPublished()==s)
  for _,b in ipairs(bindings)do assert(o.getManager(b.domain)==b.target and b.target[b.key]==b.wrapper,'Publication changed native binding')end
 end)
 if not ok then s.active=false;Rollback();error(err,0)end
 function s.AddTick(domain,target,key)
  assert(s.active and not s.retired and not s.paused and s.BindingKnown())
  assert(#s.ticks<16,'Planning method bound')
  local b=Build(domain,key,'TICK',target);b.tick=true
  b.summary={context=o.context,domain=domain,method=key,kind='TICK',calls=0,returned=0,metadataErrors=0,owners={},ownerCount=0}
  target[key]=b.wrapper;assert(target[key]==b.wrapper);bindings[#bindings+1]=b;s.ticks[#s.ticks+1]=b.summary
 end
 function s.BindingKnown()
  if o.getPublished()~=s then return false end
  for _,b in ipairs(bindings)do
   if(not b.tick and o.getManager(b.domain)~=b.target)or b.target[b.key]~=b.wrapper then return false end
  end
  return true
 end
 function s.Freeze()
  assert(s.active and not s.retired and s.BindingKnown())
  s.paused=true;return true
 end
 function s.Restore()
  if s.retired then return true end
  assert(s.BindingKnown(),'Foreign diagnostic binding preserved')
  for _,b in ipairs(bindings)do b.target[b.key]=b.original;assert(b.target[b.key]==b.original)end
  s.active=false;s.retired=true;o.publish(nil);assert(o.getPublished()==nil);return true
 end
 return s
end
return M
