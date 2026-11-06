BaiqiSettlementJournal = {}
local J = BaiqiSettlementJournal
local MAX = 2147483647
local TOP = {version=true, owner=true, serial=true, operations=true}
local FIELDS = {token=true, sequence=true, unitID=true, unitType=true, x=true, y=true, plot=true, turn=true, requestID=true, stage=true, empty=true, conflictingCity=true, cityID=true}
local TYPES = {UNIT_SETTLER=true}
local STAGES = {PREPARED=true, ARMED=true, OBSERVED=true, LEGACY_UNKNOWN=true}

local function Plain(t) return type(t)=="table" and getmetatable(t)==nil end
function J.Integer(value, maximum)
  return type(maximum)=="number" and maximum==maximum and maximum>=0 and maximum<math.huge
    and maximum==math.floor(maximum) and type(value)=="number" and value==value
    and value>=0 and value<=maximum and value==math.floor(value)
end

function J.UnitKey(id)
  if J.Integer(id, 9007199254740991) then return string.format("%.0f", id) end
end

function J.Token(owner, sequence)
  if J.Integer(owner, MAX) and J.Integer(sequence, MAX) and sequence >= 1 then
    return "settle:" .. string.format("%.0f", owner) .. ":" .. string.format("%.0f", sequence)
  end
end

function J.New(owner)
  if J.Integer(owner, MAX) then
    return {version=1, owner=owner, serial=0, operations={}}
  end
end

local function RequestID(s)
  if type(s) ~= "string" or #s > 96 then return false end
  local a, b, c = s:match("^([0-9]+):([0-9]+):([0-9]+)$")
  if not a or not b or not c then return false end
  if (a ~= "0" and a:sub(1,1) == "0") or (b ~= "0" and b:sub(1,1) == "0") or (c ~= "0" and c:sub(1,1) == "0") then return false end
  return true
end
function J.Validate(state, owner)
  if not J.Integer(owner, MAX) or not Plain(state) or state.version ~= 1
    or state.owner ~= owner or not J.Integer(state.serial, MAX) or not Plain(state.operations) then return false end
  for key in pairs(state) do if not TOP[key] then return false end end
  local count, sequences = 0, {}
  for key, op in pairs(state.operations) do
    count = count + 1
    if count > 256 or not Plain(op) then return false end
    for field in pairs(op) do if not FIELDS[field] then return false end end
    if type(key) ~= "string" or key ~= J.UnitKey(op.unitID) or not TYPES[op.unitType]
      or not J.Integer(op.sequence, state.serial) or op.sequence < 1 or sequences[op.sequence]
      or op.token ~= J.Token(owner, op.sequence) or not J.Integer(op.turn, MAX)
      or not STAGES[op.stage] or type(op.empty) ~= "boolean" or type(op.conflictingCity) ~= "boolean" then return false end
    sequences[op.sequence] = true
    if op.stage == "PREPARED" or op.stage == "ARMED" then
      if op.empty ~= true or not J.Integer(op.x, MAX) or not J.Integer(op.y, MAX) or not J.Integer(op.plot, MAX) or op.cityID ~= nil then return false end
      if not RequestID(op.requestID) then return false end
    elseif op.stage == "OBSERVED" then
      if op.empty ~= true or not J.Integer(op.x, MAX) or not J.Integer(op.y, MAX) or not J.Integer(op.plot, MAX) or not J.Integer(op.cityID, MAX) or op.conflictingCity ~= false then return false end
      if not RequestID(op.requestID) then return false end
    elseif op.stage == "LEGACY_UNKNOWN" then
      if op.empty ~= false or op.x ~= nil or op.y ~= nil or op.plot ~= nil or op.cityID ~= nil or op.conflictingCity ~= false or op.requestID ~= "legacy" then return false end
    end
  end
  return true
end

function J.Clone(state, owner)
  if not J.Validate(state, owner) then return nil end
  local result = {version=1, owner=owner, serial=state.serial, operations={}}
  for key, op in pairs(state.operations) do
    local copy = {}
    for field, value in pairs(op) do copy[field] = value end
    result.operations[key] = copy
  end
  return result
end

function J.Equal(a, b, owner)
  if not J.Validate(a, owner) or not J.Validate(b, owner) or a.serial ~= b.serial then return false end
  for key, op in pairs(a.operations) do
    local other = b.operations[key]
    if not other then return false end
    for field, value in pairs(op) do if other[field] ~= value then return false end end
  end
  for key in pairs(b.operations) do if not a.operations[key] then return false end end
  return true
end
