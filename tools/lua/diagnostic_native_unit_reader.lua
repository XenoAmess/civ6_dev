-- Read-only access to the native qualifier behind the existing UI guard proxy.
-- No writes, hooks, manager replacement, or fallback binding.
local M={version=1}
function M.New(E)
  assert(type(E)=='table'and type(E.GetGuardManager)=='function'and type(E.GetMetatable)=='function')
  local getManager,getMeta=E.GetGuardManager,E.GetMetatable
  local manager=getManager();local meta=getMeta(manager)
  assert(type(manager)=='table'and type(meta)=='table')
  local native=meta.__index
  assert((type(native)=='table'or type(native)=='userdata')and native~=manager)
  local qualifier=native.CanStartOperation;assert(type(qualifier)=='function')
  local unpackValues=table.unpack or unpack
  local invalid,busy=false,false
  local function pack(...)return{n=select('#',...),...}end
  local function check()
    assert(not invalid and E.GetGuardManager==getManager and E.GetMetatable==getMeta,'READ_PORT_CHANGED')
    assert(getManager()==manager and getMeta(manager)==meta and meta.__index==native and native.CanStartOperation==qualifier,'READ_BINDING_CHANGED')
    assert(not invalid,'READ_REENTRY')
  end
  local function invoke(fn,...)
    if busy or invalid then invalid=true;error('READ_REENTRY_OR_INVALID')end
    busy=true
    local ok,err=pcall(check);local result
    if ok then result=pack(pcall(fn,...));ok=result[1];err=result[2]end
    if ok then ok,err=pcall(check)end
    busy=false
    if not ok then invalid=true;error(err)end
    return unpackValues(result,2,result.n)
  end
  local api={}
  function api.Check()return invoke(function()return true end)end
  function api.CanStartOperation(...)return invoke(qualifier,...)end
  function api.State()return{invalid=invalid,busy=busy}end
  assert(api.Check())
  return api
end
return M
