-- Read-only synchronous bracket; does not prove clock synchronization.
local function is_fn(v) return type(v) == 'function' end
local function is_num(v) return type(v) == 'number' end
local function is_finite(v) return v == v and v ~= math.huge and v ~= -math.huge end

local function call_safe(fn)
  local ok, val = pcall(fn)
  if not ok then return nil, 'throw' end
  return val, nil
end

local function validate_num(val, label)
  if not is_num(val) then return nil, label .. '_type' end
  if not is_finite(val) then return nil, label .. '_finite' end
  if val < 0 then return nil, label .. '_range' end
  return val, nil
end

local function Sample(uiClock, coreClock)
  if not is_fn(uiClock) then return nil, 'uiClock_param' end
  if not is_fn(coreClock) then return nil, 'coreClock_param' end

  local a, err = call_safe(uiClock)
  if err then return nil, 'ui_before_' .. err end
  a, err = validate_num(a, 'ui_before')
  if err then return nil, err end

  local c, err = call_safe(coreClock)
  if err then return nil, 'core_' .. err end
  c, err = validate_num(c, 'core')
  if err then return nil, err end

  local z, err = call_safe(uiClock)
  if err then return nil, 'ui_after_' .. err end
  z, err = validate_num(z, 'ui_after')
  if err then return nil, err end

  if z < a then return nil, 'order' end

  return {a, c, z}, nil
end

return Sample
