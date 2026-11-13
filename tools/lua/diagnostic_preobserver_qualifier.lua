-- Function body inserted only by the explicit private v2 builder.
local t=Game.GetCurrentGameTurn();assert(Integer(t))
if t~=88 and t~=89 then return nil end
assert(Game.GetLocalPlayer()==0)
local active=Players[0]:IsTurnActive();assert(type(active)=='boolean')
if not active then return nil end
local now=Automation.GetTime();assert(Finite(now))
if anchors[t]==nil then
  local n=Players[0]:GetCities():GetCount();assert(Integer(n))
  return{turnBefore=t,citiesBefore=n}
end
assert(Finite(anchors[t]) and now>=anchors[t])
if now>=anchors[t]+10 then return nil end
local n=Players[0]:GetCities():GetCount();assert(Integer(n))
return{turnBefore=t,citiesBefore=n}
