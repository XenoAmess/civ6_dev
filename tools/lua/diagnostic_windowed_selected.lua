-- Private diagnosis only; never loaded by the playable mod.
return function(NewProfile,clock,getTurn,getPlayer,names,capacity,first,last)
  local function integer(x,max)
    return type(x)=='number'and x==x and x>=0 and x<=max and x%1==0
  end
  local function finite(x)return type(x)=='number'and x==x and x>=0 and x<math.huge end
  assert(type(NewProfile)=='function'and type(clock)=='function'
    and type(getTurn)=='function'and type(getPlayer)=='function')
  assert(integer(capacity,2048)and capacity>=1 and integer(first,2147483646)
    and first>=1 and integer(last,2147483647)and last==first+1)
  assert(type(names)=='table')
  local selected,count={},0
  for _,name in ipairs(names)do
    assert(type(name)=='string'and name~=''and not name:find(':',1,true)and not selected[name])
    selected[name]=true;count=count+1
  end
  assert(count>=1 and count<=64)
  local entries=0
  for key in pairs(names)do assert(integer(key,count)and key>=1);entries=entries+1 end
  assert(entries==count)
  local unpack_=unpack or table.unpack
  local function pack(...)return{n=select('#',...),...}end
  local function read(fn)
    local ok,value=pcall(fn)
    if ok and integer(value,2147483647)then return value end
  end
  local function now()
    local ok,value=pcall(clock)
    if ok and finite(value)then return value end
  end
  local p=NewProfile(clock,capacity,{aggregate_zero=true})
  local enabled,used,retired=false,false,false
  local definitions,metadataErrors,gateErrors,anchorErrors,skipped=0,0,0,0,0
  local armTime,anchors=nil,{}
  local api={}
  local function eligible()
    if not enabled or retired then return nil end
    local turn,player=read(getTurn),read(getPlayer)
    if turn==nil or player==nil then metadataErrors=metadataErrors+1;return nil end
    local anchor=anchors[turn]
    if player~=0 or turn<first or turn>last or anchor==nil then skipped=skipped+1;return nil end
    local at=now()
    if at==nil or at<anchor then gateErrors=gateErrors+1;return nil end
    if at>=anchor+10 then skipped=skipped+1;return nil end
    return turn,anchor
  end
  local function capture(timed,label,name,site,turn,anchor,...)
    local before=#p.samples
    local n=select('#',...);local arg=(...)
    local result=pack(pcall(timed,...))
    local after=read(getTurn);local row=p.samples[#p.samples]
    if #p.samples>before and row and row.name==label then
      row.turnStart=turn;row.turnEnd=after;row.argumentCount=n
      row.anchor=anchor;row.site=site
      row.windowEligible=after==turn and row.started>=anchor and row.ended<=anchor+10
      if name=='BaiqiController.RunNow'then
        row.allowOrders=type(arg)=='boolean'and tostring(arg)or'nil'
      end
      if site~=nil then row.argumentCount=n-1 end -- Omit the forwarded callable.
      if after==nil then metadataErrors=metadataErrors+1 end
    end
    if not result[1]then error(result[2],0)end
    return unpack_(result,2,result.n)
  end
  local function Wrap(label,fn)
    assert(type(label)=='string'and type(fn)=='function')
    local name=label:match('([^:]+)$')
    if label:sub(1,24)~='Lua/BaiqiController.lua:'or not selected[name]then return fn end
    definitions=definitions+1
    local timed=p:Wrap(label,fn)
    return function(...)
      local turn,anchor=eligible()
      if turn==nil then return fn(...)end
      return capture(timed,label,name,nil,turn,anchor,...)
    end
  end
  local nativeLabel='Native.GetMoveToPathEx'
  local native=p:Wrap(nativeLabel,function(fn,...)return fn(...)end)
  function api.Path(site,fn,...)
    local turn,anchor=eligible()
    if turn==nil then return fn(...)end
    return capture(native,nativeLabel,'Native.GetMoveToPathEx',site,turn,anchor,fn,...)
  end
  function api.Arm(player,turn)
    if player~=0 or turn~=first-1 or read(getPlayer)~=player or read(getTurn)~=turn then return false,'context'end
    if retired then return false,'retired'end
    if used then return false,'already_used'end
    local at=now();if at==nil then return false,'clock'end
    armTime=at;used=true;enabled=true;return true,'armed'
  end
  function api.Anchor(player,turn)
    if not enabled or retired or player~=0 or not integer(turn,2147483647)
      or turn<first or turn>last or read(getPlayer)~=player or read(getTurn)~=turn then return false,'context'end
    local at=now()
    if anchors[turn]~=nil or at==nil or at<armTime
      or(turn==last and(anchors[first]==nil or at<anchors[first]))then
      anchorErrors=anchorErrors+1;return false,'anchor'
    end
    anchors[turn]=at;return true,'anchored'
  end
  function api.Stop()enabled=false;return true end
  function api.Retire()enabled=false;retired=true;return true end
  function api.Read()
    local out={marker='baiqi184-windowed-selected/v1',first=first,last=last,
      enabled=enabled,used=used,retired=retired,definitions=definitions,selectedCount=count,
      metadataErrors=metadataErrors,gateErrors=gateErrors,anchorErrors=anchorErrors,
      skippedOutsideWindows=skipped,totalCalls=p.totalCalls,capacity=p.capacity,
      dropped=p.dropped,invalidClock=p.invalidClock,zeroSuccess=p.zeroSuccess,rows={},anchors={}}
    for turn,at in pairs(anchors)do out.anchors[turn]=at end
    for i,row in ipairs(p.samples)do
      local r={};for key,value in pairs(row)do r[key]=value end;out.rows[i]=r
    end
    return out
  end
  return Wrap,api
end
