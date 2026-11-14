-- Bounded diagnostic records, separate from planning performance samples.
local function Finite(v)
  return type(v)=='number' and v==v and v>-math.huge and v<math.huge
end
local function Copy(row)
  local out={};for k,v in pairs(row) do out[k]=v end;return out
end
return function(capacity)
  assert(Finite(capacity) and capacity>=1 and capacity<=4096 and capacity%1==0,'Invalid census capacity')
  local enabled,retired=true,false
  local total,dropped,invalid=0,0,0
  local rows={}
  local api={}
  function api.Record(row)
    if not enabled then return false end
    total=total+1
    local valid=type(row)=='table'
    if valid then
      for k,v in pairs(row) do
        local t=type(v)
        if type(k)~='string' or not(t=='string' or t=='boolean' or Finite(v)) then valid=false;break end
      end
    end
    if not valid then invalid=invalid+1;return false end
    if #rows==capacity then dropped=dropped+1;return false end
    rows[#rows+1]=Copy(row);return true
  end
  function api.Stop() enabled=false end
  function api.Retire() enabled=false;retired=true end
  function api.Snapshot()
    local out={enabled=enabled,retired=retired,total_calls=total,dropped=dropped,
      invalid_rows=invalid,capacity=capacity,rows={}}
    for i,row in ipairs(rows) do out.rows[i]=Copy(row) end
    return out
  end
  return api
end
