-- Passive diagnostics: forward the original calls, never make gameplay orders.
local M={}
local stateKeys={"gold","netGold","cities","cityPopulation","builders","queuedBuilders",
  "settlers","queuedSettlers","reservedSettlers","traders","queuedTraders","tradeCapacity",
  "army","queuedArmy","maintenance","committedMaintenance","resourceAffordable","archaeologistDemand"}
local configKeys={"goldReserve","netGoldMin","buildersPerCity","maxSettlers","settlerMinPop","armyPerCity"}
local function Pack(...) return {n=select("#",...),...} end
local function Scalar(v)
  local t=type(v)
  return t=="string" or t=="boolean" or (t=="number" and v==v and v~=math.huge and v~=-math.huge)
end

function M.Install(o)
  assert(type(o)=="table" and type(o.getTables)=="function" and type(o.getPublished)=="function"
    and type(o.publish)=="function" and type(o.unpack)=="function")
  assert(o.getPublished()==nil,"Observer namespace occupied")
  local planner,cities,units=o.getTables()
  assert(type(planner)=="table" and type(cities)=="table" and type(units)=="table")
  assert(type(o.game)=="table" and type(o.game.GetCurrentGameTurn)=="function"
    and (type(o.unitRows)=="table" or type(o.unitRows)=="userdata"))
  local s={counts={recruit=0,city=0,unit_op=0,unit_cmd=0},errors=0,drops=0,samples={},entries={}}
  local function Sense(fn)
    local ok=pcall(fn)
    if not ok then s.errors=s.errors+1 end
  end
  local function Before(kind,args)
    s.counts[kind]=s.counts[kind]+1
    if #s.samples>=4096 then s.drops=s.drops+1;return nil end
    local r={kind=kind,turn=o.game.GetCurrentGameTurn(),argc=args.n,returned=false}
    if kind=="recruit" then
      assert(type(args[1])=="string" and type(args[2])=="table" and type(args[3])=="table")
      r.role=args[1];r.state={};r.config={};r.unknownFields={}
      for _,group in ipairs({{stateKeys,args[2],r.state,"state."},{configKeys,args[3],r.config,"config."}}) do
        for _,key in ipairs(group[1]) do
          local value=group[2][key]
          if Scalar(value) then group[3][key]=value else r.unknownFields[#r.unknownFields+1]=group[4]..key end
        end
      end
      if #r.unknownFields>0 then s.errors=s.errors+1 end
    else
      local actor=args[1]
      r.actorID=actor:GetID();r.owner=actor:GetOwner();r.operation=args[2]
      assert(Scalar(r.actorID) and Scalar(r.owner) and Scalar(r.operation))
      if kind~="city" then
        local definition=o.unitRows[actor:GetUnitType()]
        assert(definition and type(definition.UnitType)=="string")
        r.unitType=definition.UnitType
      end
      if args[3]~=nil then
        assert(type(args[3])=="table");r.params={};local n=0
        for k,v in pairs(args[3]) do
          n=n+1;assert(n<=32 and Scalar(k) and Scalar(v))
          r.params[k]=v
        end
      end
    end
    s.samples[#s.samples+1]=r
    return r
  end
  local function Add(target,key,kind)
    local original=target[key];assert(type(original)=="function")
    local wrapper=function(...)
      local args=Pack(...);local record
      Sense(function()record=Before(kind,args)end)
      local result=Pack(original(...))
      if record then Sense(function()
        record.returned=true;record.returnCount=result.n
        if kind=="recruit" then assert(type(result[1])=="boolean");record.allowed=result[1] end
      end) end
      return o.unpack(result,1,result.n)
    end
    s.entries[#s.entries+1]={target=target,key=key,original=original,wrapper=wrapper}
  end
  Add(planner,"AllowRecruit","recruit")
  Add(cities,"RequestOperation","city")
  Add(units,"RequestOperation","unit_op")
  Add(units,"RequestCommand","unit_cmd")
  local function Owned()
    local p,c,u=o.getTables()
    assert(p==planner and c==cities and u==units,"Foreign API table")
    for _,e in ipairs(s.entries) do assert(e.target[e.key]==e.wrapper,"Foreign binding preserved") end
  end
  function s.Restore()
    assert(o.getPublished()==s,"Foreign namespace preserved");Owned()
    for _,e in ipairs(s.entries) do e.target[e.key]=e.original;assert(e.target[e.key]==e.original) end
    o.publish(nil);assert(o.getPublished()==nil)
  end
  local ok,err=pcall(function()
    for _,e in ipairs(s.entries) do assert(e.target[e.key]==e.original);e.target[e.key]=e.wrapper end
    o.publish(s);assert(o.getPublished()==s,"Publication not retained");Owned()
  end)
  if not ok then
    for _,e in ipairs(s.entries) do if e.target[e.key]==e.wrapper then e.target[e.key]=e.original end end
    if o.getPublished()==s then o.publish(nil) end
    error(err)
  end
  return s
end
return M
