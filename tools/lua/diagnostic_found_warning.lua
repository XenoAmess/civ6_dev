-- Passive pre-operation information. The supplied sensor must only read.
local M={}
function M.Install(o)
  assert(type(o)=='table' and type(o.getTable)=='function'
    and type(o.getPublished)=='function' and type(o.publish)=='function'
    and type(o.sense)=='function','Observer ports')
  local operation=o.foundOperation
  assert(type(operation)=='number' and operation>=-2147483648
    and operation<=2147483647 and operation%1==0,'Found operation')
  assert(o.getPublished()==nil,'Observer namespace occupied')
  local target=o.getTable()
  assert(type(target)=='table' and type(target.RequestOperation)=='function','Operation table')
  local original=target.RequestOperation
  local h={samples={},errors=0,drops=0}
  local function wrapper(...)
    if select(2,...)==operation then
      if #h.samples<16 then
        local ok,record=pcall(o.sense,...)
        if not ok or type(record)~='table' or getmetatable(record)~=nil then
          h.errors=h.errors+1
          record={status='UNKNOWN',reason='callback_error'}
        end
        h.samples[#h.samples+1]=record
      else h.drops=h.drops+1 end
    end
    return original(...)
  end
  local function Owned()
    assert(o.getPublished()==h,'Foreign namespace preserved')
    assert(o.getTable()==target,'Foreign API table preserved')
    assert(target.RequestOperation==wrapper,'Foreign binding preserved')
  end
  function h.Restore()
    Owned()
    target.RequestOperation=original
    assert(target.RequestOperation==original,'Restore binding failed')
    o.publish(nil)
    assert(o.getPublished()==nil,'Restore namespace failed')
  end
  local ok,err=pcall(function()
    assert(o.getTable()==target and target.RequestOperation==original
      and o.getPublished()==nil,'Observer ownership changed')
    target.RequestOperation=wrapper
    o.publish(h)
    Owned()
  end)
  if not ok then
    if target.RequestOperation==wrapper then target.RequestOperation=original end
    local known,published=pcall(o.getPublished)
    if known and published==h then pcall(o.publish,nil) end
    error(err)
  end
  return h
end
return M
