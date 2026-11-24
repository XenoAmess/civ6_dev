-- Separate internal diagnosis; never imported by the playable product.
return function(NewProfile,clock,getTurn,getPlayer,names,capacity)
  local function integer(x,max)return type(x)=='number'and x==x and x>=0 and x<=max and x%1==0 end
  assert(type(NewProfile)=='function'and type(clock)=='function'and type(getTurn)=='function'and type(getPlayer)=='function')
  assert(type(names)=='table'and integer(capacity,512)and capacity>=1)
  local selected,count={},0
  for _,name in ipairs(names)do assert(type(name)=='string'and name~=''and not name:find(':',1,true)and not selected[name]);selected[name]=true;count=count+1 end
  assert(count>=1 and count<=64)
  local entries=0;for key in pairs(names)do assert(integer(key,count)and key>=1);entries=entries+1 end;assert(entries==count)
  local unpack_=unpack or table.unpack
  local function pack(...)return{n=select('#',...),...}end
  local function read(fn)local ok,value=pcall(fn);if ok and integer(value,2147483647)then return value end end
  local p=NewProfile(clock,capacity,{aggregate_zero=true})
  local enabled,used,retired=false,false,false
  local definitions,metadataErrors=0,0
  local api={}
  local function Wrap(label,fn)
    assert(type(label)=='string'and type(fn)=='function')
    local name=label:match('([^:]+)$')
    if label:sub(1,24)~='Lua/BaiqiController.lua:'or not selected[name]then return fn end
    definitions=definitions+1
    local timed=p:Wrap(label,fn)
    return function(...)
      if not enabled or retired then return fn(...)end
      local before=#p.samples;local turn=read(getTurn);local n=select('#',...);local first=(...)
      local result=pack(pcall(timed,...))
      local after=read(getTurn);local row=p.samples[#p.samples]
      if #p.samples>before and row and row.name==label then
        row.turnStart=turn;row.turnEnd=after;row.argumentCount=n
        if name=='BaiqiController.RunNow'then row.allowOrders=type(first)=='boolean'and tostring(first)or'nil'end
        if turn==nil or after==nil then metadataErrors=metadataErrors+1 end
      end
      if not result[1]then error(result[2],0)end
      return unpack_(result,2,result.n)
    end
  end
  function api.Arm(player,turn)
    if player~=0 or not integer(turn,2147483647)or read(getPlayer)~=player or read(getTurn)~=turn then return false,'context'end
    if retired then return false,'retired'end
    if used then return false,'already_used'end
    used=true;enabled=true;return true,'armed'
  end
  function api.Stop()enabled=false;return true end
  function api.Retire()enabled=false;retired=true;return true end
  function api.Read()
    local out={marker='baiqi183-selected-nested/v1',enabled=enabled,used=used,retired=retired,
      definitions=definitions,selectedCount=count,metadataErrors=metadataErrors,
      totalCalls=p.totalCalls,capacity=p.capacity,dropped=p.dropped,invalidClock=p.invalidClock,zeroSuccess=p.zeroSuccess,rows={}}
    for i,row in ipairs(p.samples)do local r={};for k,v in pairs(row)do r[k]=v end;out.rows[i]=r end
    return out
  end
  return Wrap,api
end
