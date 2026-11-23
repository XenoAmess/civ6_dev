-- A saved player choice, never a destruction receipt or a manual plot control.
BaiqiRazeChoiceCore={}
local M=BaiqiRazeChoiceCore
local MAX=2147483647
local function Integer(v)return type(v)=='number'and v==v and v>=0 and v<=MAX and v%1==0 end
local fields={version=true,kind=true,owner=true,cityID=true,plot=true,x=true,y=true,turn=true}
local function Copy(v,pid,index,x,y,turn)
  if type(v)~='table'or getmetatable(v)~=nil then return nil end
  local n=0;for k in pairs(v)do n=n+1;if n>8 or not fields[k]then return nil end end
  if n~=8 or v.version~=1 or v.kind~='PLAYER_RAZE_CHOICE' or v.owner~=pid
    or not Integer(v.cityID)or v.plot~=index or v.x~=x or v.y~=y
    or not Integer(v.turn)or v.turn>turn then return nil end
  return {version=1,kind=v.kind,owner=pid,cityID=v.cityID,plot=index,x=x,y=y,turn=v.turn}
end
function M.Create(C,E)
  if type(C)~='table'or type(C.leader)~='string'or C.leader==''
    or type(C.razeChoiceKey)~='string'or C.razeChoiceKey==''or type(E)~='table'then return nil end
  local KEY=C.razeChoiceKey
  local busy,faulted=false,false
  local function Owner(pid,active)
    if not Integer(pid)or E.Game.GetLocalPlayer()~=pid or E.GameConfiguration.IsAnyMultiplayer()~=false then return nil end
    if E.GameConfiguration.IsHotseat~=nil and E.GameConfiguration.IsHotseat()~=false then return nil end
    local p,c=E.Players[pid],E.PlayerConfigurations[pid]
    if not p or not c or c:GetLeaderTypeName()~=C.leader or c:IsHuman()~=true then return nil end
    if active and(p:IsTurnActive()~=true or E.Game.IsAllowStrategicCommands(pid)~=true)then return nil end
    return p
  end
  local function Plot(pid,index,x,y)
    if not Integer(index)or not Integer(x)or not Integer(y)then return nil end
    local w,h=E.Map.GetGridSize()
    if not Integer(w)or not Integer(h)or w<1 or h<1 or w*h>MAX
      or x>=w or y>=h or index~=y*w+x then return nil end
    local vis=E.PlayersVisibility[pid]
    if not vis or vis:IsRevealed(x,y)~=true or vis:IsVisible(x,y)~=true then return nil end
    local t=E.Map.GetPlotByIndex(index)
    if not t or t:GetIndex()~=index or t:GetX()~=x or t:GetY()~=y then return nil end
    return t
  end
  local function Read(pid,index,x,y)
    if faulted then return 'UNAVAILABLE',nil,'unconfirmed_choice_write' end
    local p=Owner(pid,false)
    if not p then return 'UNAVAILABLE',nil,'owner' end
    local turn=E.Game.GetCurrentGameTurn();local t=Plot(pid,index,x,y)
    if not Integer(turn)or not t then return 'UNAVAILABLE',nil,'site' end
    local raw=t:GetProperty(KEY)
    if Owner(pid,false)~=p or E.Game.GetCurrentGameTurn()~=turn or not Plot(pid,index,x,y)then
      return 'UNAVAILABLE',nil,'state_changed'
    end
    if raw==nil then return 'READY',false,'no_recorded_choice' end
    local value=Copy(raw,pid,index,x,y,turn)
    if not value then return 'UNAVAILABLE',nil,'invalid_choice' end
    return 'READY',true,'player_raze_choice',value
  end
  local function Remember(pid,cityID,index,x,y)
    if faulted then return 'UNAVAILABLE',nil,'unconfirmed_choice_write' end
    local p=Owner(pid,true);local turn=E.Game.GetCurrentGameTurn()
    if not p or not Integer(turn)or not Integer(cityID)then return 'UNAVAILABLE',nil,'owner_or_city' end
    local function Facts()
      if Owner(pid,true)~=p or E.Game.GetCurrentGameTurn()~=turn then return nil end
      local t=Plot(pid,index,x,y);if not t or t:IsCity()~=true or t:GetOwner()~=pid then return nil end
      local city=E.CityManager.GetCityAt(x,y);local own=p:GetCities():FindID(cityID)
      for _,v in ipairs({city or false,own or false})do
        if not v or v:GetID()~=cityID or v:GetOwner()~=pid or v:GetX()~=x or v:GetY()~=y then return nil end
      end
      return t
    end
    local t=Facts();if not t then return 'UNAVAILABLE',nil,'current_city' end
    local raw=t:GetProperty(KEY)
    if raw~=nil then
      local v=Copy(raw,pid,index,x,y,turn)
      if not v then faulted=true;return 'UNAVAILABLE',nil,'invalid_choice' end
      if not Facts()then return 'UNAVAILABLE',nil,'state_changed' end
      return 'READY',v,'already_recorded'
    end
    if not Facts()or t:GetProperty(KEY)~=nil then return 'UNAVAILABLE',nil,'state_changed' end
    local v={version=1,kind='PLAYER_RAZE_CHOICE',owner=pid,cityID=cityID,plot=index,x=x,y=y,turn=turn}
    -- Persist once before the original void request. An exception, including
    -- apply-then-throw, freezes expansion in this instance; it never retries.
    faulted=true
    t:SetProperty(KEY,v)
    local actual=Copy(t:GetProperty(KEY),pid,index,x,y,turn)
    if not actual or actual.cityID~=cityID or actual.turn~=turn or not Facts()then
      return 'UNAVAILABLE',nil,'persist_unconfirmed'
    end
    faulted=false
    return 'READY',actual,'recorded_player_choice'
  end
  local function Protected(fn)
    return function(...)
      if busy then return 'UNAVAILABLE',nil,'reentrant' end
      busy=true;local ok,a,b,c,d=pcall(fn,...);busy=false
      if not ok then return 'UNAVAILABLE',nil,'handler_error' end
      return a,b,c,d
    end
  end
  return {Read=Protected(Read),Remember=Protected(Remember)}
end
return M
