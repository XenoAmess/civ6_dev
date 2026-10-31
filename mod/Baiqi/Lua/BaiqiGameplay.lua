-- City-only requisition and migration. Administration has no player settings API.
include("BaiqiConfig")
include("BaiqiPolicy")
include("BaiqiPlanner")
include("BaiqiRequisition")
include("BaiqiCapture")

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
  local stage=type(record)=="table" and record.stage or (ok and "REJECTED" or "UNKNOWN")
  player:SetProperty("BAIQI_REQUISITION_RESULT",{id=params.requestID,stage=stage,reason=ok and reason or "handler_error"})
  if not ok then print("BAIQI|requisition_handler_error|"..tostring(success)) end
end

GameEvents.BaiqiRequisition.Add(OnRequisition)
GameEvents.BaiqiRequisitionRecover.Add(function(playerID)
  BaiqiCapture.Recover(playerID)
  RetireLegacyControls()
end)
GameEvents.OnGameTurnStarted.Add(RetireLegacyControls)
print("BAIQI|gameplay_loaded|version=2|mandatory_admin=true")
