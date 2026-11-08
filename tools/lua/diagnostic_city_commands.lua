local M = {}
local MAX_SAMPLES = 256
local MAX_PARAMS = 32

local function IsScalar(v)
  local t = type(v)
  return t == "string" or t == "boolean" or (t == "number" and v == v and v ~= math.huge and v ~= -math.huge)
end

local function Integer(v,low,high)
  return type(v)=="number"and v>=low and v<=high and v%1==0
end

local function Pack(...)
  return {n = select("#", ...), ...}
end

function M.Install(o)
  assert(type(o) == "table" and type(o.getTable) == "function" and type(o.getPublished) == "function" and type(o.publish) == "function" and type(o.unpack) == "function")
  assert(o.getPublished() == nil, "Observer namespace occupied")
  local target = o.getTable()
  assert(type(target) == "table", "Target must be table")
  local original = target.RequestCommand
  assert(type(original) == "function", "RequestCommand must be function")
  assert(type(o.game) == "table" and type(o.game.GetCurrentGameTurn) == "function", "Game context invalid")

  local s = {
    count = 0,
    errors = 0,
    drops = 0,
    samples = {},
    Restore = nil
  }

  local function Before(city, op, params)
    s.count = s.count + 1
    if #s.samples >= MAX_SAMPLES then
      s.drops = s.drops + 1
      return nil
    end

    local turn = o.game.GetCurrentGameTurn()
    if not Integer(turn,0,2147483647) then
      s.errors = s.errors + 1
      return nil
    end

    local cityID, owner
    if type(city) == "table" or type(city) == "userdata" then
      if type(city.GetID) == "function" then cityID = city:GetID() end
      if type(city.GetOwner) == "function" then owner = city:GetOwner() end
    end

    if not Integer(cityID,0,2147483647) or not Integer(owner,0,2147483647) then
      s.errors = s.errors + 1
      return nil
    end

    if not Integer(op,-2147483648,4294967295) then
      s.errors = s.errors + 1
      return nil
    end

    local copiedParams = nil
    if params ~= nil then
      if type(params) ~= "table" then
        s.errors = s.errors + 1
        return nil
      end
      copiedParams = {}
      local n = 0
      for k, v in pairs(params) do
        n = n + 1
        if n > MAX_PARAMS then
          s.errors = s.errors + 1
          return nil
        end
        if not IsScalar(k) or not IsScalar(v) then
          s.errors = s.errors + 1
          return nil
        end
        copiedParams[k] = v
      end
    end

    local r = {
      turn = turn,
      cityID = cityID,
      owner = owner,
      operation = op,
      params = copiedParams,
      returned = false
    }
    s.samples[#s.samples + 1] = r
    return r
  end

  local wrapper = function(...)
    local args = Pack(...)
    local record
    local ok, err = pcall(function() record = Before(args[1], args[2], args[3]) end)
    if not ok then s.errors = s.errors + 1 end

    local result = Pack(original(...))
    if record then
      local afterOK=pcall(function()
        record.returned = true
        record.returnCount = result.n
      end)
      if not afterOK then s.errors=s.errors+1 end
    end

    return o.unpack(result, 1, result.n)
  end

  s.Restore = function()
    assert(o.getPublished() == s, "Foreign namespace preserved")
    assert(o.getTable() == target, "Foreign API table")
    assert(target.RequestCommand == wrapper, "Foreign binding preserved")
    target.RequestCommand = original
    assert(target.RequestCommand == original)
    o.publish(nil)
    assert(o.getPublished() == nil)
  end

  local ok, err = pcall(function()
    target.RequestCommand = wrapper
    o.publish(s)
    assert(o.getPublished() == s, "Publication not retained")
    assert(o.getTable() == target, "Foreign API table")
    assert(target.RequestCommand == wrapper, "Foreign binding preserved")
  end)

  if not ok then
    if target.RequestCommand == wrapper then
      target.RequestCommand = original
    end
    if o.getPublished() == s then
      o.publish(nil)
    end
    error(err)
  end

  return s
end

return M
