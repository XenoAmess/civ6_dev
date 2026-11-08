-- Information only. No return value authorizes a game operation.
BaiqiSettlementWarning={}
local function Integer(v,low)
  return type(v)=="number"and v>=low and v<=2147483647 and v%1==0
end
local function Object(v)return type(v)=="table"or type(v)=="userdata"end
local function Static(o,key,...)
  assert(Object(o));local f=o[key];assert(type(f)=="function");return f(...)
end
local function Method(o,key,...)
  assert(Object(o));local f=o[key];assert(type(f)=="function");return f(o,...)
end
local function Read(E,pid,index)
  if type(E)~="table"or getmetatable(E)~=nil or not Integer(pid,0)or not Integer(index,0)then
    return "UNKNOWN",nil,"invalid_arguments"
  end
  local ruleset=Static(E.GameConfiguration,"GetValue","RULESET")
  if ruleset=="RULESET_STANDARD"then return "NOT_APPLICABLE",nil,"no_loyalty_rules"end
  if ruleset~="RULESET_EXPANSION_1"and ruleset~="RULESET_EXPANSION_2"then return "UNKNOWN",nil,"unknown_ruleset"end
  assert(Object(E.PlayersVisibility));local visibility=E.PlayersVisibility[pid];assert(Object(visibility))
  local function Plot()
    local p=Static(E.Map,"GetPlotByIndex",index)
    local id,x,y=Method(p,"GetIndex"),Method(p,"GetX"),Method(p,"GetY")
    if id~=index or not Integer(x,0)or not Integer(y,0)then return nil end
    if Method(visibility,"IsRevealed",x,y)~=true or Method(visibility,"IsVisible",x,y)~=true then return nil end
    -- Owner and city getters are never called for hidden plots.
    local owner=Method(p,"GetOwner")
    if not Integer(owner,-1)or(owner~=-1 and owner~=pid)or Method(p,"IsCity")~=false then return nil end
    return {x=x,y=y,owner=owner}
  end
  local first=Plot();if not first then return "UNKNOWN",nil,"target_unavailable"end
  local values=Static(E.Map,"GetContinentPlotsLoyalty")
  if type(values)~="table"or getmetatable(values)~=nil then return "UNKNOWN",nil,"warning_table_unavailable"end
  local value=values[index]
  if value==nil then return "UNKNOWN",nil,"no_warning_entry"end
  if type(value)~="number"or value~=value or value< -1000 or value>1000 then return "UNKNOWN",nil,"invalid_warning"end
  if Static(E.GameConfiguration,"GetValue","RULESET")~=ruleset then return "UNKNOWN",nil,"ruleset_changed"end
  local fresh=Plot()
  if not fresh or fresh.x~=first.x or fresh.y~=first.y or fresh.owner~=first.owner then
    return "UNKNOWN",nil,"target_changed"
  end
  if value<0 then return "KNOWN_NEGATIVE",value,"negative_loyalty"end
  return "KNOWN_NONNEGATIVE",value,"nonnegative_loyalty"
end
function BaiqiSettlementWarning.Read(E,pid,index)
  local ok,stage,value,reason=pcall(Read,E,pid,index)
  if ok then return stage,value,reason end
  return "UNKNOWN",nil,"native_information_unavailable"
end
return BaiqiSettlementWarning
