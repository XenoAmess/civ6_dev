-- City-only requisition and migration. Administration has no player settings API.
include("BaiqiConfig")
include("BaiqiPolicy")
include("BaiqiPlanner")
include("BaiqiRequisition")
include("BaiqiCapture")
include("BaiqiGPIntentGameplay")
include("BaiqiCreativeIntentGameplay")
include("BaiqiReligiousIntentGameplay")
include("BaiqiNaturalistIntentGameplay")

local function RetireLegacyControls()
  -- Remove withdrawn plot-effect gates without refunds, transfers or replay.
  if Game.GetProperty("BAIQI_WITHDRAWN_RIGHTS_CLEANED")~=2 then
    for index=0,Map.GetPlotCount()-1 do
      local plot=Map.GetPlotByIndex(index)
      if plot then
        plot:SetProperty("BAIQI_GRANARY_OUT",0)
        plot:SetProperty("BAIQI_GRANARY_IN",0)
      end
    end
    Game.SetProperty("BAIQI_RIGHTS_V1",nil)
    for _,pid in ipairs(PlayerManager.GetAliveIDs()) do
      local player=Players[pid]
      if player and player:GetProperty("BAIQI_STATE_V1")~=nil then player:SetProperty("BAIQI_STATE_V1",nil) end
    end
    Game.SetProperty("BAIQI_WITHDRAWN_RIGHTS_CLEANED",2)
  end
end

local function OnRequisition(playerID,params)
  local player=BaiqiRequisition.Player(playerID)
  if player==nil or type(params)~="table" or type(params.requestID)~="string" or #params.requestID>128 then return end
  -- Deleted requests are rejected before duplicate lookup and any native effect.
  if params.kind~=nil and params.kind~="city" then
    player:SetProperty("BAIQI_REQUISITION_RESULT",{id=params.requestID,stage="REJECTED",reason="invalid_target"})
    return
  end
  local ok,success,reason=pcall(BaiqiCapture.Request,playerID,params)
  local journal=player:GetProperty(BaiqiConfig.requisitionKey)
  local record=journal and journal.operations and journal.operations[params.requestID]
  if ok and success==false and type(record)=="table" and record.stage=="UNKNOWN" then
    -- One recovery attempt inside this already confirmed intent. Definite
    -- receipts can settle; ambiguous native calls remain frozen.
    local recovered,recoveryError=pcall(BaiqiCapture.Recover,playerID)
    journal=player:GetProperty(BaiqiConfig.requisitionKey)
    record=journal and journal.operations and journal.operations[params.requestID]
    if recovered and type(record)=="table" and record.stage=="COMMITTED" then reason="recovered" end
    if not recovered then print("BAIQI|recovery_handler_error|"..tostring(recoveryError)) end
  end
  local stage=type(record)=="table" and record.stage or (ok and "REJECTED" or "UNKNOWN")
  player:SetProperty("BAIQI_REQUISITION_RESULT",{id=params.requestID,stage=stage,reason=ok and reason or "handler_error"})
  if not ok then print("BAIQI|requisition_handler_error|"..tostring(success)) end
end

local standbyUnavailableLogged=false
local function MigrateStandby(playerID,params)
  if type(params)~="table" or params.standbyUnlockNeeded~=true
    or playerID~=Game.GetLocalPlayer() then return end
  local player=BaiqiRequisition.Player(playerID)
  if not player or player:GetProperty("BAIQI_STANDBY_UNLOCK_V1")~=nil then return end
  if player.AttachModifierByID==nil then
    if not standbyUnavailableLogged then
      print("BAIQI|standby_unlock_unavailable|reason=native_attach_missing")
      standbyUnavailableLogged=true
    end
    return
  end
  -- Persist intent BEFORE the void native call. Unknown outcomes never replay.
  local record={version=1,stage="SUBMITTED",turn=Game.GetCurrentGameTurn()}
  player:SetProperty("BAIQI_STANDBY_UNLOCK_V1",record)
  local ok,err=pcall(function() player:AttachModifierByID("BAIQI_ENABLE_STANDBY") end)
  record.stage=ok and "RETURNED" or "UNKNOWN"
  player:SetProperty("BAIQI_STANDBY_UNLOCK_V1",record)
  print("BAIQI|standby_unlock_request|stage="..record.stage.."|player="..tostring(playerID))
  if not ok then print("BAIQI|standby_unlock_unknown|"..tostring(err)) end
end

GameEvents.BaiqiRequisition.Add(OnRequisition)
GameEvents.BaiqiRequisitionRecover.Add(function(playerID,params)
  BaiqiCapture.Recover(playerID)
  RetireLegacyControls()
  MigrateStandby(playerID,params)
end)
GameEvents.OnGameTurnStarted.Add(RetireLegacyControls)
print("BAIQI|gameplay_loaded|version=2|mandatory_admin=true")
