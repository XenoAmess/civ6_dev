include("BaiqiRequisition")
include("BaiqiRights")
include("PopupDialog")
BaiqiActions = {}
local message, pending, confirming, recoveredTurn = "", nil, false, nil
local reasons = {unavailable="当前不能使用",invalid_target="目标无效",owner_changed="目标归属已变化",
 wrong_unit="请选择近战、抗骑兵或骑兵陆军",formation="请先解除护送编队",no_moves="单位没有行动力",
 cooldown="该单位本回合已经征取",not_at_war="需要与目标交战",not_adjacent="军队需要与目标相邻",
 defense_unknown="无法核实防御",walls_remaining="先击破外部防御",city_healthy="城市生命须降至35%或以下",
 state_unknown="无法核实状态",insufficient_gold="金币不足",not_visible="需要当前可见的目标",
 pending_operation="此单位或目标有未决操作",quote_changed="报价已变化，请重新选择",
 building_profile_unsupported="当前粮仓效果被其他模组修改，暂不支持",
 no_operating_granary="目标没有完好的粮仓",rights_version="经营权存档无效",
 already_controlled="该粮仓已有经营权记录",rights_limit="经营权已达16处上限",no_recipient_city="需要自己的接收城市"}

local function Explain(reason) return reasons[reason] or tostring(reason) end

function BaiqiActions.Recover()
  local pid=Game.GetLocalPlayer()
  if BaiqiRequisition.Player(pid)==nil then return end
  local turn=Game.GetCurrentGameTurn()
  if recoveredTurn==turn then return end
  recoveredTurn=turn
  UI.RequestPlayerOperation(pid,PlayerOperations.EXECUTE_SCRIPT,{OnStart="BaiqiRequisitionRecover"})
end

function BaiqiActions.Status()
  if pending then
    local p=Players[pending.playerID]
    local j=p and p:GetProperty(BaiqiConfig.requisitionKey)
    local r=j and j.operations and j.operations[pending.requestID]
    local result=p and p:GetProperty("BAIQI_REQUISITION_RESULT")
    if r==nil and type(result)=="table" and result.id==pending.requestID then r=result end
    if type(r)=="table" then
      if r.stage=="COMMITTED" then message="征取完成，已结算金币和行动力"; pending=nil
      elseif r.stage=="UNKNOWN" then message="征取结果待核实，已冻结；不要重试或退款"; pending=nil
      elseif r.stage=="REJECTED" then message="征取未执行："..Explain(r.reason); pending=nil end
    elseif pending.turn~=Game.GetCurrentGameTurn() then
      message="上一回合征取缺少回执，请先核对目标与余额"; pending=nil
    end
  end
  return message
end

function BaiqiActions.Show(kind)
  kind=kind or "city"
  if confirming or pending then message="请先处理当前征取"; return end
  local pid=Game.GetLocalPlayer()
  if BaiqiRequisition.Player(pid)==nil then message="当前不能使用征取"; return end
  local unit=UI.GetHeadSelectedUnit()
  if unit==nil or unit:GetOwner()~=pid then message="请先选择自己的地面军队"; return end
  local visibility=PlayersVisibility[pid]
  local candidates,reason={},"军队需要与敌方城市相邻"
  for dir=0,5 do
    local plot=Map.GetAdjacentPlot(unit:GetX(),unit:GetY(),dir)
    if plot and visibility and visibility:IsVisible(plot:GetX(),plot:GetY()) then
      local city=CityManager.GetCityAt(plot:GetX(),plot:GetY())
      if city and city:GetOwner()~=pid then
        local q,why=BaiqiRequisition.Quote(pid,unit:GetID(),city:GetOwner(),city:GetID(),kind)
        if q then q.name=Locale.Lookup(city:GetName()); candidates[#candidates+1]=q
        else reason=Explain(why) end
      end
    end
  end
  table.sort(candidates,function(a,b) if a.y~=b.y then return a.y<b.y end return a.x<b.x end)
  local quote=candidates[1]
  if quote==nil then message=reason; return end
  local journal=Players[pid]:GetProperty(BaiqiConfig.requisitionKey)
  if BaiqiRequisition.Conflict(journal,quote.unitID,quote.x,quote.y) then message=Explain("pending_operation"); return end
  local popup=PopupDialogInGame:new("BaiqiRequisitionConfirm")
  local effect="取得整座城市，内政托管将接手后续生产。"
  if kind=="granary" then
    local recipient=Players[pid]:GetCities():FindID(quote.recipientCityID)
    if recipient==nil then message=Explain("no_recipient_city"); return end
    effect="粮仓留在原城；其1粮食、2住房改由「"..Locale.Lookup(recipient:GetName()).."」使用。原城失去对应收益。"
  end
  popup:AddText("征取「"..quote.name.."」"..(kind=="granary" and "的粮仓经营权" or "")..
    "（"..quote.x..","..quote.y.."）？[NEWLINE]支付 "..quote.cost.." 金币，并结束所选单位本回合行动。[NEWLINE]"..effect)
  confirming=true
  popup:AddConfirmButton("确认征取",function()
    confirming=false
    local fresh,why=BaiqiRequisition.Quote(pid,quote.unitID,quote.targetOwner,quote.cityID,kind,quote.recipientCityID)
    if fresh==nil then message=Explain(why); return end
    if BaiqiRequisition.RequestID(fresh)~=BaiqiRequisition.RequestID(quote)
      or fresh.cost~=quote.cost or fresh.population~=quote.population then message=Explain("quote_changed"); return end
    fresh.confirmed=true; fresh.requestID=BaiqiRequisition.RequestID(fresh); fresh.OnStart="BaiqiRequisition"
    pending=fresh
    message="正在核实征取结果；不会自动重试"
    UI.RequestPlayerOperation(pid,PlayerOperations.EXECUTE_SCRIPT,fresh)
  end)
  popup:AddCancelButton("取消",function() confirming=false; message="已取消征取，未提交操作" end)
  popup:Open()
end
