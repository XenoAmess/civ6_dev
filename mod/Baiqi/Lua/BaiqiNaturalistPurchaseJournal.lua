BaiqiNaturalistPurchaseJournal={}
local J=BaiqiNaturalistPurchaseJournal
local MAX=2147483647
local fields={token=true,sequence=true,cityID=true,unitType=true,unitHash=true,x=true,y=true,
  cost=true,faithBefore=true,reserve=true,turn=true,stage=true,baselineUnitIDs=true,
  newUnitID=true,faithAfter=true}
local function Plain(value)
  return type(value)=="table" and getmetatable(value)==nil
end
local function Number(value)
  return type(value)=="number" and value==value and value>-math.huge and value<math.huge
end
local function Integer(value,maximum)
  if not Number(maximum) or maximum<0 or maximum>MAX or maximum%1~=0 then return false end
  return Number(value) and value>=0 and value<=maximum and value%1==0
end
local function Key(sequence)
  if Integer(sequence,MAX) and sequence>=1 then return string.format("%.0f",sequence) end
end
local function Token(owner,sequence)
  if Integer(owner,MAX) and Integer(sequence,MAX) and sequence>=1 then
    return "purchase:"..string.format("%.0f",owner)..":"..string.format("%.0f",sequence)
  end
end
local function New(owner)
  if Integer(owner,MAX) then return {version=1,owner=owner,serial=0,operations={}} end
end
local function Validate(state,owner)
  if not Integer(owner,MAX) or not Plain(state) then return false end
  if state.version~=1 or state.owner~=owner then return false end
  if not Integer(state.serial,MAX) or not Plain(state.operations) then return false end
  local top={version=true,owner=true,serial=true,operations=true}
  for field in pairs(state) do if not top[field] then return false end end
  local count,sequences=0,{}
  local armedCount=0
  for key,op in pairs(state.operations) do
    count=count+1
    if count>256 or not Plain(op) then return false end
    for field in pairs(op) do if not fields[field] then return false end end
    if type(key)~="string" then return false end
    if not Integer(op.sequence,state.serial) or op.sequence<1 then return false end
    if key~=Key(op.sequence) then return false end
    if sequences[op.sequence] then return false end
    sequences[op.sequence]=true
    if op.token~=Token(owner,op.sequence) then return false end
    if op.unitType~="UNIT_NATURALIST" then return false end
    if not Integer(op.cityID,MAX) or not Integer(op.x,MAX) or not Integer(op.y,MAX) or not Integer(op.turn,MAX) then return false end
    if not Number(op.unitHash) or op.unitHash<-2147483648 or op.unitHash>4294967295 or op.unitHash%1~=0 then return false end
    if not Number(op.cost) or op.cost<=0 then return false end
    if not Number(op.faithBefore) or op.faithBefore<0 then return false end
    if not Number(op.reserve) or op.reserve<0 then return false end
    if op.faithBefore-op.cost<op.reserve then return false end
    if op.stage~="ARMED" and op.stage~="OBSERVED" then return false end
    if op.stage=="ARMED" then
      if op.newUnitID~=nil or op.faithAfter~=nil then return false end
      armedCount=armedCount+1
    else
      if not Integer(op.newUnitID,MAX) then return false end
      if not Number(op.faithAfter) or op.faithAfter<0 then return false end
      if op.faithBefore-op.faithAfter~=op.cost then return false end
    end
    if not Plain(op.baselineUnitIDs) then return false end
    local n=0
    for k,v in pairs(op.baselineUnitIDs) do
      n=n+1
      if not Integer(k,256) or k<1 or n>256 then return false end
      if not Integer(v,MAX) then return false end
    end
    for i=1,n do
      local value=op.baselineUnitIDs[i]
      if not Integer(value,MAX) or (i>1 and value<=op.baselineUnitIDs[i-1]) then return false end
    end
    if op.stage=="OBSERVED" then
      local found=false
      for _,id in ipairs(op.baselineUnitIDs) do if id==op.newUnitID then found=true break end end
      if found then return false end
    end
  end
  if armedCount>1 then return false end
  return true
end
function J.Integer(value,maximum)
  return Integer(value,maximum)
end
function J.Key(sequence)
  return Key(sequence)
end
function J.Token(owner,sequence)
  return Token(owner,sequence)
end
function J.New(owner)
  return New(owner)
end
function J.Validate(state,owner)
  local ok,valid=pcall(Validate,state,owner)
  return ok and valid==true
end
function J.Clone(state,owner)
  if not J.Validate(state,owner) then return nil end
  local ok,result=pcall(function()
    local copy={version=1,owner=owner,serial=state.serial,operations={}}
    for key,op in pairs(state.operations) do
      local entry={}
      for field,value in pairs(op) do
        if field=="baselineUnitIDs" then
          local arr={}
          for i,v in ipairs(value) do arr[i]=v end
          entry[field]=arr
        else
          entry[field]=value
        end
      end
      copy.operations[key]=entry
    end
    return copy
  end)
  if ok then return result end
end
function J.Equal(a,b,owner)
  if not J.Validate(a,owner) or not J.Validate(b,owner) then return false end
  local ok,equal=pcall(function()
    if a.serial~=b.serial then return false end
    for key,op in pairs(a.operations) do
      local other=b.operations[key]
      if not other then return false end
      for field,value in pairs(op) do
        if field=="baselineUnitIDs" then
          local arr1, arr2 = value, other[field]
          if not arr2 then return false end
          local n1=0
          for _ in ipairs(arr1) do n1=n1+1 end
          local n2=0
          for _ in ipairs(arr2) do n2=n2+1 end
          if n1~=n2 then return false end
          for i=1,n1 do if arr1[i]~=arr2[i] then return false end end
        else
          if other[field]~=value then return false end
        end
      end
    end
    for key in pairs(b.operations) do if a.operations[key]==nil then return false end end
    return true
  end)
  return ok and equal==true
end
return J
