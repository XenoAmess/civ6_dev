-- Separate proposal metadata. Never reads or writes founding transaction state.
BaiqiSettlerGoalsCore={}
local M=BaiqiSettlerGoalsCore
local MAX=2147483647
function M.Create(C,G,J,U,E)
  local ok,api,reason=pcall(function()
    if type(C)~='table'or type(G)~='table'or type(J)~='table'or type(U)~='table'or type(E)~='table'
      or type(C.leader)~='string'or C.leader==''or type(C.settlerGoalsKey)~='string'
      or C.settlerGoalsKey==''or C.settlerGoalsKey==C.settlementIntentKey then return nil,'config' end
    for _,k in ipairs({'New','Clone'})do if type(G[k])~='function'then return nil,'schema' end end
    for _,k in ipairs({'Integer','UnitKey'})do if type(J[k])~='function'then return nil,'identity' end end
    if type(U.Classify)~='function'then return nil,'identity' end
    for _,k in ipairs({'Game','GameConfiguration','Players','PlayerConfigurations','GameInfo','Map','PlayersVisibility'})do
      if E[k]==nil then return nil,'engine' end
    end
    local KEY=C.settlerGoalsKey
    local busy=false
    local function Owner(pid,active)
      if not J.Integer(pid,MAX)or pid~=E.Game.GetLocalPlayer()
        or E.GameConfiguration.IsAnyMultiplayer()~=false then return nil end
      local hotseat=E.GameConfiguration.IsHotseat
      if hotseat~=nil and(type(hotseat)~='function'or hotseat()~=false)then return nil end
      local p,c=E.Players[pid],E.PlayerConfigurations[pid]
      if not p or not c or c:GetLeaderTypeName()~=C.leader then return nil end
      local human
      if type(c.IsHuman)=='function'then human=c:IsHuman()
      elseif type(p.IsHuman)=='function'then human=p:IsHuman()end
      if human~=true or type(p.GetProperty)~='function'or type(p.SetProperty)~='function'then return nil end
      if active and(p:IsTurnActive()~=true or E.Game.IsAllowStrategicCommands(pid)~=true
        or not J.Integer(E.Game.GetCurrentGameTurn(),MAX))then return nil end
      return p
    end
    local function Dims(pid)
      local w,h=E.Map.GetGridSize()
      if not G.New(pid,w,h)then return nil end
      return w,h
    end
    local function Bank(p,pid,w,h)
      local raw=p:GetProperty(KEY)
      if raw==nil then return G.New(pid,w,h),true end
      return G.Clone(raw,pid,w,h),false
    end
    local function Equal(a,b)
      if not a or not b then return a==b end
      for _,k in ipairs({'version','owner','width','height'})do if a[k]~=b[k]then return false end end
      for key,g in pairs(a.goals)do
        local other=b.goals[key];if not other then return false end
        for _,k in ipairs({'unitID','unitType','plot','x','y'})do if g[k]~=other[k]then return false end end
      end
      for key in pairs(b.goals)do if not a.goals[key]then return false end end
      return true
    end
    local function Fresh(p,pid,w,h,old,missing,turn)
      if Owner(pid,true)~=p or E.Game.GetCurrentGameTurn()~=turn then return false end
      local nw,nh=Dims(pid);if nw~=w or nh~=h then return false end
      local now,absent=Bank(p,pid,w,h)
      if not now or absent~=missing or not Equal(old,now)then return false end
      local fw,fh=Dims(pid)
      return fw==w and fh==h and Owner(pid,true)==p and E.Game.GetCurrentGameTurn()==turn
    end
    local function Persist(p,pid,w,h,old,missing,value,turn,qualify)
      local write=G.Clone(value,pid,w,h)
      if not write or not Fresh(p,pid,w,h,old,missing,turn)then return 'UNAVAILABLE',nil,'state_changed' end
      if qualify and not qualify()then return 'UNAVAILABLE',nil,'proposal_changed' end
      if not Fresh(p,pid,w,h,old,missing,turn)then return 'UNAVAILABLE',nil,'state_changed' end
      p:SetProperty(KEY,write)
      local actual=G.Clone(p:GetProperty(KEY),pid,w,h)
      local nw,nh=Dims(pid)
      if not actual or not Equal(value,actual)or nw~=w or nh~=h or Owner(pid,true)~=p
        or E.Game.GetCurrentGameTurn()~=turn then return 'UNAVAILABLE',nil,'persist_unconfirmed' end
      return 'READY',G.Clone(actual,pid,w,h),'persisted'
    end
    local function Snapshot(pid)
      local p=Owner(pid,false);if not p then return 'UNAVAILABLE',nil,'owner' end
      local w,h=Dims(pid);if not w then return 'UNAVAILABLE',nil,'map' end
      local value=Bank(p,pid,w,h)
      if not value then return 'UNAVAILABLE',nil,'invalid_plan' end
      local nw,nh=Dims(pid)
      if Owner(pid,false)~=p or nw~=w or nh~=h then return 'UNAVAILABLE',nil,'context_changed' end
      return 'READY',value,'proposal'
    end
    local function Read(pid,id)
      local key=J.UnitKey(id);if not key then return 'UNAVAILABLE',nil,'unit_id' end
      local s,bank,why=Snapshot(pid);if s~='READY'then return s,nil,why end
      return 'READY',bank.goals[key],'proposal'
    end
    local function Remember(pid,id,index,x,y)
      local p=Owner(pid,true);if not p then return 'UNAVAILABLE',nil,'owner' end
      local w,h=Dims(pid);if not w then return 'UNAVAILABLE',nil,'map' end
      local turn=E.Game.GetCurrentGameTurn();local key=J.UnitKey(id)
      if not key or not J.Integer(index,MAX)or not J.Integer(x,MAX)or not J.Integer(y,MAX)
        or x>=w or y>=h or index~=y*w+x then return 'UNAVAILABLE',nil,'input' end
      local function Facts()
        local s,f=U.Classify(J,E,pid,id)
        if s~='LIVE'or not f or f.id~=id or f.unitType~='UNIT_SETTLER'
          or f.formation~=1 or f.dead~=false or f.delayed~=false
          or type(f.moves)~='number'or f.moves<=0 then return nil end
        local plot=E.Map.GetPlotByIndex(index);local vis=E.PlayersVisibility[pid]
        if not plot or plot:GetIndex()~=index or plot:GetX()~=x or plot:GetY()~=y
          or not vis or vis:IsRevealed(x,y)~=true then return nil end
        return f
      end
      local initial=Facts();if not initial then return 'UNAVAILABLE',nil,'actor_or_site' end
      local old,missing=Bank(p,pid,w,h);if not old then return 'UNAVAILABLE',nil,'invalid_plan' end
      local value=G.Clone(old,pid,w,h)
      -- Retiring stale proposals is not a consumption or founding receipt.
      for other,g in pairs(value.goals)do
        if other~=key then
          local s=U.Classify(J,E,pid,g.unitID)
          if s=='ABSENT'or s=='ALIAS'or s=='CONSUMED'then value.goals[other]=nil end
        end
      end
      for other,g in pairs(value.goals)do if other~=key and g.plot==index then return 'UNAVAILABLE',nil,'reserved' end end
      value.goals[key]={unitID=id,unitType='UNIT_SETTLER',plot=index,x=x,y=y}
      if not G.Clone(value,pid,w,h)then return 'UNAVAILABLE',nil,'capacity_or_schema' end
      local function Qualify()
        local f=Facts();if not f then return false end
        for _,k in ipairs({'id','unitType','x','y','moves','formation','dead','delayed'})do
          if f[k]~=initial[k]then return false end
        end
        return true
      end
      if Equal(old,value)then
        if not Qualify()or not Fresh(p,pid,w,h,old,missing,turn)then return 'UNAVAILABLE',nil,'state_changed' end
        return 'READY',G.Clone(value,pid,w,h).goals[key],'unchanged'
      end
      local s,bank,why=Persist(p,pid,w,h,old,missing,value,turn,Qualify)
      if s~='READY'then return s,nil,why end
      return s,bank.goals[key],why
    end
    local function Forget(pid,id)
      local p=Owner(pid,true);local key=J.UnitKey(id)
      if not p or not key then return 'UNAVAILABLE',nil,'owner_or_unit' end
      local w,h=Dims(pid);if not w then return 'UNAVAILABLE',nil,'map' end
      local turn=E.Game.GetCurrentGameTurn();local old,missing=Bank(p,pid,w,h)
      if not old then return 'UNAVAILABLE',nil,'invalid_plan' end
      if old.goals[key]==nil then
        if not Fresh(p,pid,w,h,old,missing,turn)then return 'UNAVAILABLE',nil,'state_changed' end
        return 'READY',nil,'absent'
      end
      local value=G.Clone(old,pid,w,h);value.goals[key]=nil
      local s,_,why=Persist(p,pid,w,h,old,missing,value,turn)
      return s,nil,why
    end
    local function Protected(fn)
      return function(...)
        if busy then return 'UNAVAILABLE',nil,'reentrant' end
        busy=true;local good,a,b,c=pcall(fn,...);busy=false
        if not good then return 'UNAVAILABLE',nil,'handler_error' end
        return a,b,c
      end
    end
    return {Snapshot=Protected(Snapshot),Read=Protected(Read),Remember=Protected(Remember),Forget=Protected(Forget)},nil
  end)
  if not ok then return nil,'dependencies_unavailable' end
  return api,reason
end
return M
