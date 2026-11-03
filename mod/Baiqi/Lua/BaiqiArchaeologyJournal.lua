BaiqiArchaeologyJournal={}
local J=BaiqiArchaeologyJournal
local MAX=2147483647
local top={version=true,owner=true,serial=true,operations=true}
local fields={token=true,sequence=true,unitID=true,unitType=true,homeCityID=true,cityX=true,cityY=true,buildingIndex=true,x=true,y=true,resourceIndex=true,resourceType=true,turn=true,stage=true,baselineWorkIDs=true,works=true,artifactIndex=true,artifactType=true,actingPlayerID=true,choicePlayerID=true,choiceTurn=true,targetPlayerID=true,newWorkID=true}
local function Plain(value) return type(value)=="table" and getmetatable(value)==nil end
local function Number(value) return type(value)=="number" and value==value and value>-math.huge and value<math.huge end
local function Integer(value,maximum) if not Number(maximum) or maximum<0 or maximum>MAX or maximum%1~=0 then return false end return Number(value) and value>=0 and value<=maximum and value%1==0 end
local function Key(id) if Integer(id,MAX) then return id==0 and "0" or string.format("%.0f",id) end end
local function Token(owner,sequence) if Integer(owner,MAX) and Integer(sequence,MAX) and sequence>=1 then return "archaeology:"..Key(owner)..":"..Key(sequence) end end
local function New(owner) if Integer(owner,MAX) then return {version=1,owner=owner,serial=0,operations={}} end end
local function Validate(state,owner)
  if not Integer(owner,MAX) or not Plain(state) then return false end
  if state.version~=1 or state.owner~=owner then return false end
  if not Integer(state.serial,MAX) or not Plain(state.operations) then return false end
  for field in pairs(state) do if not top[field] then return false end end
  local count,sequences,allWorks=0,{},{}
  local unresolvedCount=0
  for key,op in pairs(state.operations) do
    count=count+1
    if count>256 or not Plain(op) then return false end
    for field in pairs(op) do if not fields[field] then return false end end
    if type(key)~="string" then return false end
    if not Integer(op.sequence,state.serial) or op.sequence<1 then return false end
    if key~=Key(op.unitID) then return false end
    if sequences[op.sequence] then return false end
    sequences[op.sequence]=true
    if op.token~=Token(owner,op.sequence) then return false end
    if op.unitType~="UNIT_ARCHAEOLOGIST" then return false end
    if not Integer(op.homeCityID,MAX) or not Integer(op.cityX,MAX) or not Integer(op.cityY,MAX) or not Integer(op.buildingIndex,MAX) or not Integer(op.x,MAX) or not Integer(op.y,MAX) or not Integer(op.resourceIndex,MAX) or not Integer(op.turn,MAX) then return false end
    if op.resourceType~="RESOURCE_ANTIQUITY_SITE" and op.resourceType~="RESOURCE_SHIPWRECK" then return false end
    if op.stage~="EXCAVATE_ARMED" and op.stage~="CHOICE_ARMED" and op.stage~="OBSERVED" then return false end
    if not Plain(op.baselineWorkIDs) then return false end
    local n=0
    for k,v in pairs(op.baselineWorkIDs) do
      n=n+1
      if not Integer(k,64) or k<1 or n>64 then return false end
      if not Integer(v,MAX) then return false end
    end
    for i=1,n do
      local value=op.baselineWorkIDs[i]
      if not Integer(value,MAX) or (i>1 and value<=op.baselineWorkIDs[i-1]) then return false end
    end
    if not Plain(op.works) then return false end
    local wCount=0
    for k,v in pairs(op.works) do
      wCount=wCount+1
      if wCount>64 then return false end
      if type(k)~="string" or k~=Key(tonumber(k)) then return false end
      if v~=true then return false end
      local wk=k
      if allWorks[wk] then return false end
      allWorks[wk]=true
    end
    if op.stage=="EXCAVATE_ARMED" then
      if op.artifactIndex~=nil or op.artifactType~=nil or op.actingPlayerID~=nil or op.choicePlayerID~=nil or op.choiceTurn~=nil or op.targetPlayerID~=nil or op.newWorkID~=nil then return false end
      unresolvedCount=unresolvedCount+1
    else
      if not Integer(op.artifactIndex,MAX) then return false end
      if not Integer(op.artifactType,5) then return false end
      if not Integer(op.actingPlayerID,MAX) then return false end
      if op.choicePlayerID~=op.actingPlayerID then return false end
      if not Integer(op.choiceTurn,MAX) or op.choiceTurn<op.turn then return false end
      if op.artifactType==0 or op.artifactType==3 or op.artifactType==4 then
        if not Integer(op.targetPlayerID,MAX) then return false end
      else
        if op.targetPlayerID~=nil then return false end
      end
      if op.stage=="CHOICE_ARMED" then
        if op.newWorkID~=nil then return false end
        unresolvedCount=unresolvedCount+1
      else
        if not Integer(op.newWorkID,MAX) then return false end
        if not op.works[Key(op.newWorkID)] then return false end
        local found=false
        for _,id in ipairs(op.baselineWorkIDs) do if id==op.newWorkID then found=true break end end
        if found then return false end
      end
    end
  end
  if unresolvedCount>1 then return false end
  return true
end
function J.Integer(value,maximum) return Integer(value,maximum) end
function J.UnitKey(id) return Key(id) end
function J.Token(owner,sequence) return Token(owner,sequence) end
function J.New(owner) return New(owner) end
function J.Validate(state,owner) local ok,valid=pcall(Validate,state,owner) return ok and valid==true end
function J.Clone(state,owner)
  if not J.Validate(state,owner) then return nil end
  local ok,result=pcall(function()
    local copy={version=1,owner=owner,serial=state.serial,operations={}}
    for key,op in pairs(state.operations) do
      local entry={}
      for field,value in pairs(op) do
        if field=="baselineWorkIDs" then
          local arr={}
          for i,v in ipairs(value) do arr[i]=v end
          entry[field]=arr
        elseif field=="works" then
          local map={}
          for k,v in pairs(value) do map[k]=v end
          entry[field]=map
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
        if field=="baselineWorkIDs" then
          local arr1, arr2 = value, other[field]
          if not arr2 then return false end
          local n1=0; for _ in ipairs(arr1) do n1=n1+1 end
          local n2=0; for _ in ipairs(arr2) do n2=n2+1 end
          if n1~=n2 then return false end
          for i=1,n1 do if arr1[i]~=arr2[i] then return false end end
        elseif field=="works" then
          local map1, map2 = value, other[field]
          if not map2 then return false end
          local c1=0; for _ in pairs(map1) do c1=c1+1 end
          local c2=0; for _ in pairs(map2) do c2=c2+1 end
          if c1~=c2 then return false end
          for k,v in pairs(map1) do if map2[k]~=v then return false end end
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
