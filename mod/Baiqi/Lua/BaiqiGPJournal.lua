-- Save-safe metadata only. Never coerce or repair an unknown journal in place.
BaiqiGPJournal = {}
local J=BaiqiGPJournal
local MAX=2147483647
local top={version=true,owner=true,serial=true,operations=true}
local fields={token=true,sequence=true,unitID=true,unitType=true,class=true,
  individual=true,charges=true,turn=true,stage=true,eventSeen=true}
local types={UNIT_GREAT_SCIENTIST=true,UNIT_GREAT_ENGINEER=true,UNIT_GREAT_MERCHANT=true}
function J.Integer(value,maximum)
  return type(value)=="number" and value>=0 and value<=maximum and value==math.floor(value)
end
function J.UnitKey(id)
  if J.Integer(id,9007199254740991) then return string.format("%.0f",id) end
end
function J.Token(owner,sequence)
  return "gp:"..string.format("%.0f",owner)..":"..string.format("%.0f",sequence)
end
function J.New(owner) return {version=1,owner=owner,serial=0,operations={}} end
function J.Validate(state,owner)
  if not J.Integer(owner,MAX) or type(state)~="table" or state.version~=1
    or state.owner~=owner or not J.Integer(state.serial,MAX) or type(state.operations)~="table" then return false end
  for key in pairs(state) do if not top[key] then return false end end
  local count,sequences=0,{}
  for key,op in pairs(state.operations) do
    count=count+1
    if count>256 or type(op)~="table" then return false end
    for field in pairs(op) do if not fields[field] then return false end end
    if type(key)~="string" or key~=J.UnitKey(op.unitID) or not types[op.unitType]
      or not J.Integer(op.sequence,state.serial) or op.sequence<1 or sequences[op.sequence]
      or op.token~=J.Token(owner,op.sequence) or not J.Integer(op.class,MAX)
      or not J.Integer(op.individual,MAX) or not J.Integer(op.charges,1000000) or op.charges<1
      or not J.Integer(op.turn,MAX) or type(op.eventSeen)~="boolean"
      or (op.stage~="ARMED" and op.stage~="OBSERVED" and op.stage~="LEGACY_UNKNOWN") then return false end
    sequences[op.sequence]=true
  end
  return true
end
function J.Clone(state,owner)
  if not J.Validate(state,owner) then return nil end
  local result={version=1,owner=owner,serial=state.serial,operations={}}
  for key,op in pairs(state.operations) do
    local copy={};for field,value in pairs(op) do copy[field]=value end
    result.operations[key]=copy
  end
  return result
end
function J.Equal(a,b,owner)
  if not J.Validate(a,owner) or not J.Validate(b,owner) or a.serial~=b.serial then return false end
  for key,op in pairs(a.operations) do
    local other=b.operations[key];if not other then return false end
    for field,value in pairs(op) do if other[field]~=value then return false end end
  end
  for key in pairs(b.operations) do if not a.operations[key] then return false end end
  return true
end
