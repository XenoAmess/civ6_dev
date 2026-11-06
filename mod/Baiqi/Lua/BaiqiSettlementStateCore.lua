-- Core metadata storage only. READY is never an authorization to emit an order.
BaiqiSettlementStateCore = {}
local M=BaiqiSettlementStateCore
function M.Create(C,J,E)
  local ok,api,reason=pcall(function()
    if type(C)~="table" or type(J)~="table" or type(E)~="table"
      or type(C.leader)~="string" or C.leader==""
      or type(C.settlementIntentKey)~="string" or C.settlementIntentKey=="" then return nil,"config" end
    for _,k in ipairs({"Integer","Validate","Clone","New","Equal","UnitKey","Token"}) do
      if type(J[k])~="function" then return nil,"journal_api" end
    end
    for _,k in ipairs({"Game","GameConfiguration","Players","PlayerConfigurations","GameInfo"}) do
      if E[k]==nil then return nil,"engine" end
    end
    local KEY,MAX=C.settlementIntentKey,2147483647
    local busy=false
    local function Owner(pid,active)
      if not J.Integer(pid,MAX) or pid~=E.Game.GetLocalPlayer()
        or E.GameConfiguration.IsAnyMultiplayer()~=false then return nil end
      local hotseat=E.GameConfiguration.IsHotseat
      if hotseat~=nil and (type(hotseat)~="function" or hotseat()~=false) then return nil end
      local player,config=E.Players[pid],E.PlayerConfigurations[pid]
      if not player or not config or config:GetLeaderTypeName()~=C.leader then return nil end
      local human
      if type(config.IsHuman)=="function" then human=config:IsHuman()
      elseif type(player.IsHuman)=="function" then human=player:IsHuman() end
      if human~=true or type(player.GetProperty)~="function" or type(player.SetProperty)~="function" then return nil end
      if active and (player:IsTurnActive()~=true or E.Game.IsAllowStrategicCommands(pid)~=true
        or not J.Integer(E.Game.GetCurrentGameTurn(),MAX)) then return nil end
      return player
    end
    local function SnapshotValue(player,pid)
      local raw=player:GetProperty(KEY)
      if raw==nil then return "UNAVAILABLE",nil,"journal_missing" end
      local copy=J.Clone(raw,pid)
      if not copy then return "UNAVAILABLE",nil,"journal_invalid" end
      return "READY",copy,"existing"
    end
    local function WriteNew(player,pid,state)
      local write=J.Clone(state,pid)
      if not write then return "UNAVAILABLE",nil,"new_journal_invalid" end
      -- Enumeration/read callbacks may have installed a record after the first
      -- nil read. Preserve it rather than overwriting with a new empty journal.
      if player:GetProperty(KEY)~=nil then return "UNAVAILABLE",nil,"journal_changed" end
      player:SetProperty(KEY,write)
      local raw=player:GetProperty(KEY)
      if not J.Equal(state,raw,pid) then return "UNAVAILABLE",nil,"persist_unconfirmed" end
      local copy=J.Clone(raw,pid)
      if not copy then return "UNAVAILABLE",nil,"persist_unconfirmed" end
      return "READY",copy,"initialized"
    end
    local function Legacy(player,pid,turn)
      local state=J.New(pid)
      if not state then return nil end
      local count,seen=0,{}
      for _,unit in player:GetUnits():Members() do
        count=count+1;if count>512 then return nil end
        local id=unit:GetID();local key=J.UnitKey(id)
        if not key or seen[key] or unit:GetOwner()~=pid then return nil end
        seen[key]=true
        local index=unit:GetType()
        if not J.Integer(index,MAX) then return nil end
        local def=E.GameInfo.Units[index]
        if not def or type(def.UnitType)~="string" then return nil end
        if def.UnitType=="UNIT_SETTLER" then
          if state.serial>=256 then return nil end
          state.serial=state.serial+1
          state.operations[key]={token=J.Token(pid,state.serial),sequence=state.serial,
            unitID=id,unitType="UNIT_SETTLER",turn=turn,requestID="legacy",
            stage="LEGACY_UNKNOWN",empty=false,conflictingCity=false}
        end
      end
      if J.Validate(state,pid) then return state end
    end
    local function Initialize(pid,savedGameFlag)
      local player=Owner(pid,true)
      if not player then return "UNAVAILABLE",nil,"owner" end
      local raw=player:GetProperty(KEY)
      if raw~=nil then
        local copy=J.Clone(raw,pid)
        if not copy then return "UNAVAILABLE",nil,"journal_invalid" end
        return "READY",copy,"existing"
      end
      if type(savedGameFlag)~="boolean" then return "UNAVAILABLE",nil,"load_kind_unknown" end
      local state
      if savedGameFlag==false then state=J.New(pid)
      else state=Legacy(player,pid,E.Game.GetCurrentGameTurn()) end
      if not state then return "UNAVAILABLE",nil,"legacy_inventory_unknown" end
      return WriteNew(player,pid,state)
    end
    local function Snapshot(pid)
      local player=Owner(pid,false)
      if not player then return "UNAVAILABLE",nil,"owner" end
      return SnapshotValue(player,pid)
    end
    local function Protected(fn)
      return function(...)
        if busy then return "UNAVAILABLE",nil,"reentrant" end
        busy=true
        local good,a,b,c=pcall(fn,...)
        busy=false
        if not good then return "UNAVAILABLE",nil,"handler_error" end
        if a~="READY" then return "UNAVAILABLE",nil,c end
        return a,b,c
      end
    end
    return {Initialize=Protected(Initialize),Snapshot=Protected(Snapshot)},nil
  end)
  if not ok then return nil,"dependencies_unavailable" end
  return api,reason
end
