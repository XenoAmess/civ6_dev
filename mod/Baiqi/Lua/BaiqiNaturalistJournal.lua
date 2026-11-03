-- Metadata validation grants neither an operation nor a park effect.
BaiqiNaturalistJournal={}
local J=BaiqiNaturalistJournal
local MAX=2147483647
local top={version=true,owner=true,serial=true,operations=true}
local fields={token=true,sequence=true,unitID=true,unitType=true,charges=true,x=true,y=true,turn=true,stage=true}
local function Plain(value)
  return type(value)=="table" and getmetatable(value)==nil
end
function J.Integer(value,maximum)
  return type(maximum)=="number" and maximum>=0 and maximum<=MAX and maximum%1==0
    and type(value)=="number" and value>=0 and value<=maximum and value%1==0
end
function J.UnitKey(id)
  if J.Integer(id,MAX) then return string.format("%.0f",id) end
end
function J.Token(owner,sequence)
  if J.Integer(owner,MAX) and J.Integer(sequence,MAX) and sequence>=1 then
    return "park:"..string.format("%.0f",owner)..":"..string.format("%.0f",sequence)
  end
end
function J.New(owner)
  if J.Integer(owner,MAX) then return {version=1,owner=owner,serial=0,operations={}} end
end
local function Validate(state,owner)
  if not J.Integer(owner,MAX) or not Plain(state) or state.version~=1 or state.owner~=owner
    or not J.Integer(state.serial,MAX) or not Plain(state.operations) then return false end
  for field in pairs(state) do if not top[field] then return false end end
  local count,sequences=0,{}
  for key,op in pairs(state.operations) do
    count=count+1
    if count>256 or not Plain(op) then return false end
    for field in pairs(op) do if not fields[field] then return false end end
    if type(key)~="string" or not J.UnitKey(op.unitID) or key~=J.UnitKey(op.unitID)
      or op.unitType~="UNIT_NATURALIST" or not J.Integer(op.sequence,state.serial)
      or op.sequence<1 or sequences[op.sequence] or op.token~=J.Token(owner,op.sequence)
      or not J.Integer(op.charges,1000000) or op.charges<1
      or not J.Integer(op.x,MAX) or not J.Integer(op.y,MAX) or not J.Integer(op.turn,MAX)
      or (op.stage~="ARMED" and op.stage~="OBSERVED") then return false end
    sequences[op.sequence]=true
  end
  return true
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
      local entry={};for field,value in pairs(op) do entry[field]=value end
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
      local other=b.operations[key];if not other then return false end
      for field,value in pairs(op) do if other[field]~=value then return false end end
    end
    for key in pairs(b.operations) do if a.operations[key]==nil then return false end end
    return true
  end)
  return ok and equal==true
end
return J
