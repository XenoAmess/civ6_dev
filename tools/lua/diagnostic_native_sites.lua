-- Passive calls at explicitly selected source sites; no SDK table mutation.
local M={}
local function Pack(...)return{n=select('#',...),...}end
local function Integer(v)return type(v)=='number'and v==v and v%1==0 and v>=-1 and v<=2147483647 end
local function Scalar(v)
 local t=type(v)
 return t=='boolean'or(t=='string'and #v<=256)or(t=='number'and v==v and v~=math.huge and v~=-math.huge)
end
function M.New(o)
 assert(type(o)=='table'and type(o.context)=='string'and type(o.frame)=='function'and type(o.describe)=='function'and type(o.unpack)=='function')
 local capacity=o.capacity or 4096;assert(Integer(capacity)and capacity>=1 and capacity<=16384)
 local s={marker='passive-native-sites-v1',active=true,paused=false,retired=false,calls=0,dropped=0,metadataErrors=0,afterErrors=0,rows={}}
 local descriptorFields={owner=true,id=true,x=true,y=true}
 local function Before(site,kind,target,args)
  s.calls=s.calls+1
  if #s.rows>=capacity then s.dropped=s.dropped+1;return nil end
  local row={sequence=#s.rows+1,context=o.context,site=site,kind=kind,argumentCount=args.n,returned=false,metadataKnown=false,argumentTypes={}}
  s.rows[#s.rows+1]=row
  local ok,err=pcall(function()
   local turn,pid=o.frame();assert(Integer(turn)and turn>=0 and Integer(pid)and pid>=0,'Unknown Core frame')
   row.turn=turn;row.localPlayer=pid
   if kind=='GLOBAL'then row.ownerScope='GLOBAL'
   else
    local d=o.describe(kind,target);assert(type(d)=='table'and Integer(d.owner),'Unknown Core target owner')
    local count=0;for k,v in pairs(d)do
     count=count+1;assert(count<=8 and descriptorFields[k]and Scalar(v),'Unsupported Core target metadata')
     if k=='id'then assert(Integer(v)and v>=0,'Unknown Core target identity')end
     row[k]=v
    end
    row.ownerScope=kind
   end
   for i=1,math.min(args.n,8)do row.argumentTypes[i]=type(args[i])end
   row.argumentTypeDetailsOmitted=math.max(0,args.n-8)
   -- Property values/journals remain original references only in native args.
   -- Keep small scalar key/delta facts; never traverse mutable game state.
   local first=kind=='GLOBAL'and 1 or 2
   if Scalar(args[first])then row.firstParameter=args[first]end
   row.metadataKnown=true
  end)
  if not ok then s.metadataErrors=s.metadataErrors+1;row.metadataErrorType=type(err)end
  return row
 end
 local function Invoke(site,kind,target,original,args)
  if not s.active or s.paused then return original(o.unpack(args,1,args.n))end
  local known,row=pcall(Before,site,kind,target,args)
  if not known then s.metadataErrors=s.metadataErrors+1;row=nil end
  -- Let the original error propagate unchanged. A non-returning row stays
  -- returned=false; it is never converted into an inferred success.
  local result=Pack(original(o.unpack(args,1,args.n)))
  if row then local ok=pcall(function()row.returned=true;row.returnCount=result.n end);if not ok then s.afterErrors=s.afterErrors+1 end end
  return o.unpack(result,1,result.n)
 end
 local function Site(site,kind)
  assert(type(site)=='string'and #site>0 and #site<=160 and(kind=='PLAYER'or kind=='UNIT'or kind=='CITY'or kind=='PLOT'or kind=='TREASURY'or kind=='GLOBAL'))
 end
 function s.Method(site,kind,target,key)
  Site(site,kind);assert(kind~='GLOBAL'and type(key)=='string')
  -- Resolve the native method once before evaluating the call arguments,
  -- matching a colon call; bind the actual receiver, not a proxy object.
  local original=target[key]
  return function(...)return Invoke(site,kind,target,original,Pack(target,...))end
 end
 function s.Static(site,kind,original)
  Site(site,kind)
  return function(...)
   local args=Pack(...);local target=kind~='GLOBAL'and args[1]or nil
   return Invoke(site,kind,target,original,args)
  end
 end
 function s.Freeze()
  assert(s.active and not s.retired);s.paused=true;return true
 end
 function s.Retire()
  s.active=false;s.retired=true;return true
 end
 return s
end
return M
