-- Player intent comes from the ordinary army -> enemy-city map interaction.
include("BaiqiRequisition")
include("PopupDialog")
BaiqiActions={}
local confirming,pending=false,nil

local function Notice(text)
  local popup=PopupDialogInGame:new("BaiqiCityNotice")
  popup:AddText(text)
  popup:AddConfirmButton("确定",function() end)
  popup:Open()
end

function BaiqiActions.Poll()
  if pending==nil then return end
  local player=Players[pending.playerID]
  local result=player and player:GetProperty("BAIQI_REQUISITION_RESULT")
  if type(result)=="table" and result.id==pending.requestID then
    pending=nil
    if result.stage=="UNKNOWN" then Notice("征取结果尚未核实，本次操作已冻结。")
    elseif result.stage=="REJECTED" then Notice("城市状态或资格已变化，本次征取未执行。") end
  elseif pending.turn~=Game.GetCurrentGameTurn() then
    pending=nil
    Notice("上一回合征取缺少可核实的回执，请先查看目标与金币余额。")
  end
end

function BaiqiActions.Interact(unit,x,y,nativeMove)
  local pid=Game.GetLocalPlayer()
  if unit==nil or unit:GetOwner()~=pid or BaiqiRequisition.Player(pid)==nil then return false end
  local visibility=PlayersVisibility[pid]
  if visibility==nil or not visibility:IsVisible(x,y) then return false end
  local city=CityManager.GetCityAt(x,y)
  if city==nil or city:GetOwner()==pid then return false end
  local quote=BaiqiRequisition.Quote(pid,unit:GetID(),city:GetOwner(),city:GetID(),"city")
  if quote==nil then return false end
  BaiqiActions.Poll()
  if confirming or pending then return true end
  local journal=Players[pid]:GetProperty(BaiqiConfig.requisitionKey)
  if BaiqiRequisition.Conflict(journal,quote.unitID,x,y) then Notice("该军队或城市有尚未核实的征取操作。"); return true end
  local cityName=Locale.Lookup(city:GetName())
  local popup=PopupDialogInGame:new("BaiqiCityInteraction")
  popup:AddText("「"..cityName.."」已可接管。[NEWLINE]支付 "..quote.cost..
    " 金币征取城市，并结束这支军队本回合行动。城市内政随后由AI接管。")
  confirming=true
  popup:AddConfirmButton("征取城市（"..quote.cost.."金币）",function()
    confirming=false
    local fresh=BaiqiRequisition.Quote(pid,quote.unitID,quote.targetOwner,quote.cityID,"city")
    if fresh==nil or fresh.cost~=quote.cost or fresh.population~=quote.population
      or BaiqiRequisition.RequestID(fresh)~=BaiqiRequisition.RequestID(quote) then
      Notice("城市状态或报价已变化，请重新与城市交互。"); return
    end
    fresh.confirmed=true;fresh.requestID=BaiqiRequisition.RequestID(fresh);fresh.OnStart="BaiqiRequisition"
    pending=fresh
    UI.RequestPlayerOperation(pid,PlayerOperations.EXECUTE_SCRIPT,fresh)
  end)
  popup:AddCustomButton("继续正常进攻",function()
    confirming=false
    if Game.GetLocalPlayer()~=pid or BaiqiRequisition.Player(pid)==nil then return end
    local current=Players[pid]:GetUnits():FindID(quote.unitID)
    local target=CityManager.GetCityAt(quote.x,quote.y)
    if current==nil or current:GetOwner()~=pid or current:GetMovesRemaining()<=0 or target==nil
      or target:GetOwner()~=quote.targetOwner or target:GetID()~=quote.cityID then return end
    nativeMove(current,quote.x,quote.y)
  end)
  popup:AddCancelButton("取消",function() confirming=false end)
  popup:Open()
  return true
end

function BaiqiActions.WrapMove(nativeMove)
  return function(unit,x,y)
    if BaiqiUIGuard and BaiqiUIGuard.Civilian(unit) then return false end
    if BaiqiActions.Interact(unit,x,y,nativeMove) then return true end
    return nativeMove(unit,x,y)
  end
end
