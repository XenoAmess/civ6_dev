-- Persistent desired reassignment. Unknown is a read status, never a terminal
-- stage that prevents a late real effect from being observed.
BaiqiFoodTileJournal={}
local J=BaiqiFoodTileJournal
local MAX=2147483647
local fields={token=true,sequence=true,cityID=true,cityX=true,cityY=true,
  sourceCityID=true,sourceX=true,sourceY=true,plotID=true,plotX=true,plotY=true,
  mapWidth=true,mapHeight=true,turn=true,stage=true,observedTurn=true,observedSurplus=true}
local function Plain(v)return type(v)=="table" and getmetatable(v)==nil end
local function Number(v,lo,hi)return type(v)=="number" and v==v and v>=lo and v<=hi end
local function Int(v,lo,hi)return Number(v,lo,hi) and v%1==0 end
function J.Integer(v)return Int(v,0,MAX) end
function J.Key(id)if J.Integer(id)then return string.format("%.0f",id)end end
function J.Token(pid,seq)
  if J.Integer(pid) and Int(seq,1,MAX) then return "foodtile:"..J.Key(pid)..":"..J.Key(seq) end
end
function J.New(pid)
  if J.Integer(pid)then return {version=1,owner=pid,serial=0,records={}}end
end
local function Validate(s,pid)
  if not J.Integer(pid) or not Plain(s) or s.version~=1 or s.owner~=pid
    or not J.Integer(s.serial) or not Plain(s.records) then return false end
  local top={version=true,owner=true,serial=true,records=true}
  for k in pairs(s)do if not top[k]then return false end end
  local count,seen=0,{}
  for key,r in pairs(s.records)do
    count=count+1;if count>128 or type(key)~="string" or not Plain(r) then return false end
    for k in pairs(r)do if not fields[k]then return false end end
    if not J.Integer(r.cityID) or key~=J.Key(r.cityID) or not J.Integer(r.sourceCityID)
      or r.sourceCityID==r.cityID or not Int(r.sequence,1,s.serial) or seen[r.sequence]
      or r.token~=J.Token(pid,r.sequence) or not J.Integer(r.turn)
      or not Int(r.mapWidth,1,512) or not Int(r.mapHeight,1,512)
      or not Int(r.plotID,0,r.mapWidth*r.mapHeight-1)
      or not Int(r.cityX,0,r.mapWidth-1) or not Int(r.cityY,0,r.mapHeight-1)
      or not Int(r.sourceX,0,r.mapWidth-1) or not Int(r.sourceY,0,r.mapHeight-1)
      or not Int(r.plotX,0,r.mapWidth-1) or not Int(r.plotY,0,r.mapHeight-1) then return false end
    seen[r.sequence]=true
    if r.stage=="ARMED" then
      if r.observedTurn~=nil or r.observedSurplus~=nil then return false end
    elseif r.stage=="OBSERVED" then
      if not Int(r.observedTurn,r.turn,MAX) or not Number(r.observedSurplus,0,1000000) then return false end
    else return false end
  end
  return true
end
function J.Validate(s,pid)local ok,valid=pcall(Validate,s,pid);return ok and valid==true end
function J.Clone(s,pid)
  if not J.Validate(s,pid)then return nil end
  local copy={version=1,owner=pid,serial=s.serial,records={}}
  for key,r in pairs(s.records)do local nextRecord={};for field,value in pairs(r)do nextRecord[field]=value end;copy.records[key]=nextRecord end
  return copy
end
function J.Equal(a,b,pid)
  if not J.Validate(a,pid) or not J.Validate(b,pid) or a.serial~=b.serial then return false end
  for key,r in pairs(a.records)do
    local other=b.records[key];if not other then return false end
    for field in pairs(fields)do if r[field]~=other[field]then return false end end
  end
  for key in pairs(b.records)do if not a.records[key]then return false end end
  return true
end
return J
