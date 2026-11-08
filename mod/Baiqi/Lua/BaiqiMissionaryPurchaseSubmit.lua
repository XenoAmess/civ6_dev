local M={}
local MAX=2147483647
local fields={"cityID","owner","x","y","unitType","unitHash","religionIndex","faithYieldIndex",
  "formationType","cost","faithBalance","operation","unitKey","yieldKey","formationKey"}
local function Object(v)return type(v)=="table"or type(v)=="userdata"end
local function Int(v,lo,hi)return type(v)=="number"and v>=lo and v<=hi and v%1==0 end
local function Number(v)return type(v)=="number"and v==v and v>-math.huge and v<math.huge end
local function Call(o,k,...)
  assert(Object(o)and type(o[k])=="function")
  return o[k](o,...)
end
local function Equal(a,b)
  if not Object(a)or not Object(b)then return false end
  for _,key in ipairs(fields)do if a[key]==nil or a[key]~=b[key]then return false end end
  return true
end
local function Bridge(E)
  assert(type(E.Bridge)=="function")
  local b=E.Bridge()
  assert(type(b)=="table"and b.version==1 and b.marker=="baiqi-missionary-purchase-v1"
    and type(b.Inspect)=="function"and type(b.Prepare)=="function")
  return b
end
function M.Request(E,pid,cityID,reserve)
  local armedToken
  local ok,a,b,c=pcall(function()
    assert(Object(E)and Int(pid,0,MAX)and Int(cityID,0,MAX)and Number(reserve)and reserve>=0)
    assert(type(E.Current)=="function"and type(E.Demand)=="function"
      and Object(E.Quote)and type(E.Quote.Quote)=="function")
    -- This is the supplied adapter. Controller owns the actual SDK reference.
    local commands=E.CityManager
    assert(Object(commands)and type(commands.RequestCommand)=="function")
    local writer=commands.RequestCommand
    local bridge=Bridge(E)
    local function Fresh()
      local p=E.Current(pid);assert(Object(p))
      local city=Call(Call(p,"GetCities"),"FindID",cityID)
      assert(Call(city,"GetOwner")==pid and Call(city,"GetID")==cityID)
      assert(E.Demand(p,pid)==true and Bridge(E)==bridge and E.CityManager==commands
        and commands.RequestCommand==writer)
      return p,city
    end
    local p,city=Fresh()
    assert(bridge.Inspect(pid)=="OPEN")
    local quote=E.Quote.Quote(E,p,pid,city,reserve)
    assert(Object(quote)and quote.cityID==cityID and quote.owner==pid)
    local function CurrentQuote()
      local owner,found=Fresh()
      local q=E.Quote.Quote(E,owner,pid,found,reserve)
      assert(Equal(quote,q))
      -- Qualification can run callbacks; recheck their consumers afterwards.
      local current,latest=Fresh()
      assert(Call(latest,"GetX")==quote.x and Call(latest,"GetY")==quote.y)
      return current,latest
    end
    CurrentQuote()
    assert(bridge.Inspect(pid)=="OPEN"and Bridge(E)==bridge)
    local granted,token=bridge.Prepare(pid,cityID,quote.x,quote.y,quote.unitHash,
      quote.religionIndex,quote.cost,quote.faithBalance,reserve)
    if granted~=true or type(token)~="string"or #token==0 then return "UNAVAILABLE",nil,"permission_unconfirmed"end
    armedToken=token
    local _,fresh=CurrentQuote()
    local stage,actualToken=bridge.Inspect(pid,token)
    if stage=="OBSERVED"and actualToken==token then return "OBSERVED",token,"already_observed"end
    assert(stage=="ARMED"and actualToken==token)
    Fresh()
    local params={[quote.unitKey]=quote.unitHash,[quote.yieldKey]=quote.faithYieldIndex,
      [quote.formationKey]=quote.formationType}
    -- Exactly one request; false, void and thrown results never clear intent.
    local submitted=pcall(writer,fresh,quote.operation,params)
    if Bridge(E)==bridge then
      local receipt,receiptToken=bridge.Inspect(pid,token)
      if receipt=="OBSERVED"and receiptToken==token then return "OBSERVED",token,"purchase_observed"end
    end
    return "ARMED",token,submitted and"awaiting_receipt"or"command_result_unknown"
  end)
  if ok then return a,b,c end
  if armedToken then return "ARMED",armedToken,"boundary_unavailable_after_permission"end
  return "UNAVAILABLE",nil,"boundary_unavailable"
end
BaiqiMissionaryPurchaseSubmit=M
return M
