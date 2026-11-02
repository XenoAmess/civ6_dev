-- Metadata only. Unknown or malformed receipts are retained, never repaired.
BaiqiReligiousJournal={}
local J=BaiqiReligiousJournal
local MAX=2147483647
local top={version=true,owner=true,serial=true,operations=true}
local fields={token=true,sequence=true,unitID=true,unitType=true,religion=true,
  charges=true,x=true,y=true,cityID=true,cityX=true,cityY=true,turn=true,stage=true}
function J.Integer(value,maximum)
  return type(value)=="number" and value>=0 and value<=maximum and value==math.floor(value)
end
function J.UnitKey(id)
  if J.Integer(id,9007199254740991) then return string.format("%.0f",id) end
end
function J.Token(owner,sequence)
  return "religion:"..string.format("%.0f",owner)..":"..string.format("%.0f",sequence)
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
    if type(key)~="string" or key~=J.UnitKey(op.unitID) or op.unitType~="UNIT_MISSIONARY"
      or not J.Integer(op.sequence,state.serial) or op.sequence<1 or sequences[op.sequence]
      or op.token~=J.Token(owner,op.sequence) or not J.Integer(op.religion,MAX)
      or not J.Integer(op.charges,1000000) or op.charges<1
      or not J.Integer(op.x,MAX) or not J.Integer(op.y,MAX) or not J.Integer(op.turn,MAX)
      or (op.stage~="ARMED" and op.stage~="OBSERVED" and op.stage~="LEGACY_UNKNOWN") then return false end
    sequences[op.sequence]=true
    if op.stage=="LEGACY_UNKNOWN" then
      if op.cityID~=nil or op.cityX~=nil or op.cityY~=nil then return false end
    else
      if not J.Integer(op.cityID,MAX) or not J.Integer(op.cityX,MAX) or not J.Integer(op.cityY,MAX)
        or op.cityX~=op.x or op.cityY~=op.y then return false end
    end
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
