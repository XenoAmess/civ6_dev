-- Actual event facts only; no unit/player operation or permission from callbacks.
local MARKER="baiqi-archaeology-receipt-events-v1"
local previous=BaiqiArchaeologyReceiptEvents
if previous~=nil then
  local ok,owned=pcall(function() return type(previous)=="table" and previous.marker==MARKER end)
  if not ok or not owned then return previous end
end
local included=pcall(include,"BaiqiArchaeologyIntentGameplay")
local subscriptions,stopped={},false
local module={marker=MARKER}
function module.Shutdown()
  if stopped then return end
  stopped=true
  for _,owned in ipairs(subscriptions) do pcall(owned.remove,owned.callback) end
  subscriptions={}
end
pcall(function()
  if previous and type(previous.Shutdown)=="function" then previous.Shutdown() end
end)
BaiqiArchaeologyReceiptEvents=module
pcall(function()
  if not included then return end
  local core=BaiqiArchaeologyIntentGameplay
  if type(core)~="table" or core.version~=1 or core.marker~="baiqi-archaeology-core-v1"
    or type(core.ObserveCreated)~="function" then return end
  local bridge=core.bridge
  if type(bridge)~="table" or bridge.version~=1 or bridge.marker~="baiqi-archaeology-intent-v1"
    or type(ExposedMembers)~="table" or ExposedMembers.BaiqiArchaeologyBridge~=bridge then return end
  local event=Events and Events.GreatWorkCreated
  if (type(event)~="table" and type(event)~="userdata")
    or type(event.Add)~="function" or type(event.Remove)~="function" then return end
  local add,remove,observe=event.Add,event.Remove,core.ObserveCreated
  local function Callback(...)
    if stopped then return end
    local function Dispatch(...)
      if BaiqiArchaeologyIntentGameplay==core and core.version==1 and core.marker=="baiqi-archaeology-core-v1"
        and core.bridge==bridge and core.ObserveCreated==observe and bridge.version==1
        and bridge.marker=="baiqi-archaeology-intent-v1" and type(ExposedMembers)=="table"
        and ExposedMembers.BaiqiArchaeologyBridge==bridge then return observe(...) end
    end
    pcall(Dispatch,...)
  end
  if pcall(add,Callback) then subscriptions[#subscriptions+1]={remove=remove,callback=Callback} end
end)
return module
