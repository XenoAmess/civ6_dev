-- Durable intent transitions. UI is the sole native order emitter.
BaiqiSettlementIntentCore = {}
local M=BaiqiSettlementIntentCore
function M.Create(C,J,S,U,T,E)
  local good,api=pcall(function()
    if type(C)~="table" or type(J)~="table" or type(S)~="table" or type(U)~="table"
      or type(T)~="table" or type(E)~="table" or type(C.settlementIntentKey)~="string"
      or type(S.Initialize)~="function" or type(S.Snapshot)~="function"
      or type(U.Classify)~="function" or type(T.Read)~="function" then return nil end
    local MAX,KEY,busy=2147483647,C.settlementIntentKey,false
    local function Owner(pid,active)
      if not J.Integer(pid,MAX) or E.Game.GetLocalPlayer()~=pid
        or E.GameConfiguration.IsAnyMultiplayer()~=false then return nil end
      if E.GameConfiguration.IsHotseat~=nil and E.GameConfiguration.IsHotseat()~=false then return nil end
      local p,c=E.Players[pid],E.PlayerConfigurations[pid]
      if not p or not c or c:GetLeaderTypeName()~=C.leader then return nil end
      local human
      if type(c.IsHuman)=="function" then human=c:IsHuman()
      elseif type(p.IsHuman)=="function" then human=p:IsHuman() end
      if human~=true then return nil end
      if active and (p:IsTurnActive()~=true or E.Game.IsAllowStrategicCommands(pid)~=true
        or not J.Integer(E.Game.GetCurrentGameTurn(),MAX)) then return nil end
      return p
    end
    local function Bank(pid)
      local status,state=S.Snapshot(pid)
      if status=="READY" then return J.Clone(state,pid) end
    end
    local function CopyOp(state,pid,id)
      local copy=J.Clone(state,pid)
      return copy and copy.operations[J.UnitKey(id)]
    end
    local function Persist(player,pid,before,after,active)
      if Owner(pid,active)~=player or not J.Validate(after,pid)
        or not J.Equal(before,player:GetProperty(KEY),pid) then return false end
      local write=J.Clone(after,pid)
      player:SetProperty(KEY,write)
      return J.Equal(after,player:GetProperty(KEY),pid)
    end
    local function Fresh(pid,id,index,x,y)
      local s,u=U.Classify(J,E,pid,id)
      if s~="LIVE" or not u or u.id~=id or u.unitType~="UNIT_SETTLER"
        or u.formation~=1 or u.moves<=0 or u.x~=x or u.y~=y then return false end
      local ts,t=T.Read(J,E,pid,index,x,y)
      return ts=="EMPTY" and t and t.empty==true and (t.owner==-1 or t.owner==pid)
    end
    local function Request(pid,requestID)
      if type(requestID)~="string" or #requestID>96 then return false end
      local a,b,c=requestID:match("^([0-9]+):([0-9]+):([0-9]+)$")
      local current=E.Game.GetCurrentGameTurn()
      return a==string.format("%.0f",pid) and J.Integer(current,MAX)
        and b==string.format("%.0f",current) and c~=nil and J.Integer(tonumber(c),MAX)
        and tonumber(c)>=1 and c==string.format("%.0f",tonumber(c))
    end
    local function Initialize(pid,flag) return S.Initialize(pid,flag) end
    local function Snapshot(pid) return S.Snapshot(pid) end
    local function Prepare(pid,id,index,x,y,requestID)
      local player=Owner(pid,true)
      if not player or not J.Integer(id,MAX) or not Request(pid,requestID) then return "UNAVAILABLE",nil,"owner_or_request" end
      local before=Bank(pid)
      if not before then return "UNAVAILABLE",nil,"journal" end
      local key=J.UnitKey(id);local prior=before.operations[key]
      if prior and prior.stage~="PREPARED" then return "UNAVAILABLE",nil,"prior_intent" end
      if before.serial>=MAX or not Fresh(pid,id,index,x,y) then return "UNAVAILABLE",nil,"world" end
      local count=0;for _ in pairs(before.operations) do count=count+1 end
      if not prior and count>=256 then return "UNAVAILABLE",nil,"journal_bound" end
      local after=J.Clone(before,pid);after.serial=after.serial+1
      after.operations[key]={token=J.Token(pid,after.serial),sequence=after.serial,unitID=id,
        unitType="UNIT_SETTLER",x=x,y=y,plot=index,turn=E.Game.GetCurrentGameTurn(),
        requestID=requestID,stage="PREPARED",empty=true,conflictingCity=false}
      if not Request(pid,requestID) or not Persist(player,pid,before,after,true) then return "UNAVAILABLE",nil,"persist_unconfirmed" end
      return "PREPARED",CopyOp(after,pid,id),"unissued"
    end
    local function Commit(pid,id,token,requestID)
      local player=Owner(pid,true)
      if not player or not J.Integer(id,MAX) or type(token)~="string" or not Request(pid,requestID) then return false,nil,"owner_or_request" end
      local before=Bank(pid);local op=before and before.operations[J.UnitKey(id)]
      if not op or op.stage~="PREPARED" or op.token~=token or op.requestID~=requestID
        or op.turn~=E.Game.GetCurrentGameTurn() or op.empty~=true or op.conflictingCity~=false then return false,nil,"not_fresh_prepared" end
      if not Fresh(pid,id,op.plot,op.x,op.y) then return false,nil,"world" end
      local after=J.Clone(before,pid);after.operations[J.UnitKey(id)].stage="ARMED"
      if not Request(pid,requestID) or not Persist(player,pid,before,after,true) then return false,nil,"persist_unconfirmed" end
      -- This return occurs only on a new PREPARED -> ARMED write + readback.
      -- A later ARMED snapshot, repeated Commit, or reload never grants again.
      return true,token,"fresh_durable_ack"
    end
    local function Inspect(pid,id)
      local player=Owner(pid,false)
      if not player or not J.UnitKey(id) then return "UNAVAILABLE",nil,"owner_or_id" end
      local before=Bank(pid);local op=before and before.operations[J.UnitKey(id)]
      if not before then return "UNAVAILABLE",nil,"journal" end
      if not op then return "OPEN",nil,"no_intent" end
      if op.stage~="ARMED" then return op.stage,CopyOp(before,pid,id),"existing" end
      local stage,tile=T.Read(J,E,pid,op.plot,op.x,op.y)
      local after
      if stage=="FOREIGN_CITY" and not op.conflictingCity then
        after=J.Clone(before,pid);after.operations[J.UnitKey(id)].conflictingCity=true
      elseif stage=="OWN_CITY" and tile and op.empty==true and op.conflictingCity==false then
        local us=U.Classify(J,E,pid,id)
        if us=="ABSENT" or us=="CONSUMED" then
          after=J.Clone(before,pid)
          local observed=after.operations[J.UnitKey(id)];observed.stage="OBSERVED";observed.cityID=tile.cityID
        end
      end
      if after then
        if not Persist(player,pid,before,after,false) then return "UNAVAILABLE",nil,"persist_unconfirmed" end
        return after.operations[J.UnitKey(id)].stage,CopyOp(after,pid,id),"world_observed"
      end
      return "ARMED",CopyOp(before,pid,id),"awaiting_correlated_world_effect"
    end
    local function Protected(fn,failure)
      return function(...)
        if busy then return failure,nil,"reentrant" end
        busy=true;local ok,a,b,c=pcall(fn,...);busy=false
        if not ok then return failure,nil,"handler_error" end
        return a,b,c
      end
    end
    return {Initialize=Protected(Initialize,"UNAVAILABLE"),Snapshot=Protected(Snapshot,"UNAVAILABLE"),
      Prepare=Protected(Prepare,"UNAVAILABLE"),Commit=Protected(Commit,false),Inspect=Protected(Inspect,"UNAVAILABLE")}
  end)
  if not good or not api then return nil,"dependencies" end
  return api
end
