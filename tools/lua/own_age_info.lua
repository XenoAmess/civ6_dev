-- Diagnostic only: the returned data never authorizes a game operation.
local M={}
local function Integer(v,low)
  return type(v)=='number'and v==v and v>=low and v<=2147483647 and v%1==0
end
local function Object(v)return type(v)=='table'or type(v)=='userdata'end
local function Static(o,key,...)
  assert(Object(o));local f=o[key];assert(type(f)=='function');return f(...)
end
local function Method(o,key,...)
  assert(Object(o));local f=o[key];assert(type(f)=='function');return f(o,...)
end
local function Capture(E,pid)
  assert(Static(E.Game,'GetLocalPlayer')==pid)
  local turn=Static(E.Game,'GetCurrentGameTurn');assert(Integer(turn,0))
  local rules=Static(E.GameConfiguration,'GetValue','RULESET')
  if rules=='RULESET_STANDARD'then return {status='NOT_APPLICABLE'}end
  assert(rules=='RULESET_EXPANSION_1'or rules=='RULESET_EXPANSION_2')
  local eras=Static(E.Game,'GetEras')
  local era=Method(eras,'GetCurrentEra');local score=Method(eras,'GetPlayerCurrentScore',pid)
  local countdown=Method(eras,'GetNextEraCountdown')
  local heroic=Method(eras,'HasHeroicGoldenAge',pid)
  local golden=Method(eras,'HasGoldenAge',pid);local dark=Method(eras,'HasDarkAge',pid)
  assert(Integer(era,0)and Integer(score,0)and Integer(countdown,-1))
  assert(type(heroic)=='boolean'and type(golden)=='boolean'and type(dark)=='boolean')
  assert(not(dark and(heroic or golden)))
  return {status='KNOWN',player=pid,turn=turn,ruleset=rules,era=era,score=score,countdown=countdown,
    heroic=heroic,golden=golden,dark=dark,age=heroic and'HEROIC'or golden and'GOLDEN'or dark and'DARK'or'NORMAL'}
end
local function Read(E,pid)
  if type(E)~='table'or getmetatable(E)~=nil or not Integer(pid,0)then return {status='UNKNOWN'}end
  local first=Capture(E,pid)
  if first.status~='KNOWN'then return first end
  local fresh=Capture(E,pid);assert(fresh.status=='KNOWN')
  for _,key in ipairs({'player','turn','ruleset','era','score','countdown','heroic','golden','dark','age'})do
    assert(first[key]==fresh[key])
  end
  return first
end
function M.Read(E,pid)
  local ok,result=pcall(Read,E,pid)
  if ok then return result end
  return {status='UNKNOWN'}
end
return M
