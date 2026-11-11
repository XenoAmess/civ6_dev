-- Normal-cost emergency Gold purchase, through the shipped building command.
-- A pending request survives turn changes in this executor; unknown is no retry.
include("BaiqiFlood")
BaiqiFloodPurchase={}
local pending
local committed={maintenance=0}
local function Number(v)
  return type(v)=="number" and v==v and v>-math.huge and v<math.huge
end
local function Integer(v)return Number(v) and v%1==0 end
local function Context(E,pid,turn)
  local player,config=E.Players[pid],E.PlayerConfigurations[pid]
  return Integer(pid) and pid>=0 and Integer(turn) and E.Game.GetLocalPlayer()==pid
    and E.Game.GetCurrentGameTurn()==turn and player and config and config:IsHuman()==true
    and config:GetLeaderTypeName()==E.config.leader and player:IsTurnActive()==true
    and E.Game.IsAllowStrategicCommands(pid)==true and E.GameConfiguration.IsAnyMultiplayer()==false
    and (not E.GameConfiguration.IsHotseat or E.GameConfiguration.IsHotseat()==false)
    and E.UI.IsGameCoreBusy()==false and E.UI.IsProcessingMessages()==false
end
local function Read(E,pid,id,turn)
  if not Context(E,pid,turn) or not Integer(id) or id<0 then return nil end
  local player=E.Players[pid]
  local city=player:GetCities():FindID(id)
  if not city or city:GetID()~=id or city:GetOwner()~=pid then return nil end
  local x,y=city:GetX(),city:GetY()
  if not Integer(x) or not Integer(y) or BaiqiFlood.City(E,pid,id,turn)~=true then return nil end
  local row=BaiqiFlood.Definition(E)
  local gold=E.GameInfo.Yields.YIELD_GOLD
  if not row or not gold or gold.YieldType~="YIELD_GOLD" or not Integer(gold.Index) or gold.Index<0 then return nil end
  local keys=E.CityCommandTypes
  if not Integer(keys.PURCHASE) or not Integer(keys.PARAM_BUILDING_TYPE) or not Integer(keys.PARAM_YIELD_TYPE)
    or keys.PARAM_BUILDING_TYPE==keys.PARAM_YIELD_TYPE then return nil end
  local reserve,minimum=E.config.goldReserve,E.config.netGoldMin
  local maintenance=row.Maintenance or 0
  if not Number(reserve) or reserve<0 or not Number(minimum) or not Number(maintenance) or maintenance<0 then return nil end
  local price=city:GetGold():GetPurchaseCost(gold.Index,row.Hash)
  local treasury=player:GetTreasury()
  local balance,income,upkeep=treasury:GetGoldBalance(),treasury:GetGoldYield(),treasury:GetTotalMaintenance()
  if not Number(price) or price<=0 or not Number(balance) or balance<0
    or not Number(income) or not Number(upkeep) or upkeep<0
    or balance-price<reserve then return nil end
  -- Native upkeep may update later than the building observation. Reserve all
  -- newly requested maintenance this turn, even if already partly reflected.
  local reserved=(committed.pid==pid and committed.turn==turn) and committed.maintenance or 0
  if income-upkeep-reserved-maintenance<minimum then return nil end
  return {city=city,id=id,x=x,y=y,index=row.Index,hash=row.Hash,gold=gold.Index,price=price,balance=balance,
    maintenance=maintenance,operation=keys.PURCHASE,buildingKey=keys.PARAM_BUILDING_TYPE,yieldKey=keys.PARAM_YIELD_TYPE,
    params={[keys.PARAM_BUILDING_TYPE]=row.Hash,[keys.PARAM_YIELD_TYPE]=gold.Index}}
end
local function Eligible(E,pid,id,turn)
  local before=Read(E,pid,id,turn)
  if not before then return nil end
  if E.CityManager.CanStartCommand(before.city,before.operation,true,before.params,false)~=true
    or E.CityManager.CanStartCommand(before.city,before.operation,false,before.params,true)~=true then return nil end
  local after=Read(E,pid,id,turn)
  if not after then return nil end
  for _,key in ipairs({"id","x","y","index","hash","gold","price","maintenance","operation","buildingKey","yieldKey"})do
    if before[key]~=after[key] then return nil end
  end
  if BaiqiFlood.City(E,pid,id,turn)~=true then return nil end
  local rule=BaiqiFlood.Definition(E)
  if not rule or (rule.Maintenance or 0)~=after.maintenance then return nil end
  local latest=E.Players[pid]:GetCities():FindID(id)
  if not latest or latest:GetID()~=id or latest:GetOwner()~=pid or latest:GetX()~=after.x or latest:GetY()~=after.y
    or not Context(E,pid,turn) then return nil end
  return after
end
local function Work(E,pid)
  local CityManager=E.CityManager
  local turn=E.Game.GetCurrentGameTurn()
  if not Context(E,pid,turn) then return false end
  if pending then
    if pending.pid~=pid then return false end
    local city=E.Players[pid]:GetCities():FindID(pending.id)
    if not city or city:GetID()~=pending.id or city:GetOwner()~=pid
      or city:GetX()~=pending.x or city:GetY()~=pending.y then return false end
    local row=BaiqiFlood.Definition(E)
    if not row or row.Index~=pending.index or row.Hash~=pending.hash then return false end
    local buildings=city:GetBuildings()
    if buildings:HasBuilding(pending.index)==true and buildings:IsPillaged(pending.index)==false then
      print("BAIQI|flood_purchase_observed|turn="..turn.."|city="..pending.id.."|hash="..pending.hash)
      pending=nil
      return true
    end
    if not pending.logged then
      print("BAIQI|flood_purchase_pending|turn="..turn.."|city="..pending.id)
      pending.logged=true
    end
    return false
  end
  local count=0
  for _,city in E.Players[pid]:GetCities():Members() do
    count=count+1
    if count>256 then return false end
    local quote=Eligible(E,pid,city:GetID(),turn)
    if quote then
      if committed.pid~=pid or committed.turn~=turn then committed={pid=pid,turn=turn,maintenance=0} end
      committed.maintenance=committed.maintenance+quote.maintenance
      -- Set before the native writer: an exception after dispatch is unknown.
      pending={pid=pid,id=quote.id,x=quote.x,y=quote.y,index=quote.index,hash=quote.hash,
        price=quote.price,balance=quote.balance,maintenance=quote.maintenance,turn=turn}
      print("BAIQI|flood_purchase_request|turn="..turn.."|source=BACKGROUND|city="..quote.id
        .."|hash="..quote.hash.."|gold="..quote.price.."|balance="..quote.balance)
      CityManager.RequestCommand(quote.city,quote.operation,quote.params)
      return true
    end
  end
  return false
end
function BaiqiFloodPurchase.Holds(pid,id)
  return pending~=nil and pending.pid==pid and pending.id==id
end
function BaiqiFloodPurchase.Run(E,pid)
  local ok,result=pcall(Work,E,pid)
  if not ok and pending and not pending.errorLogged then
    print("BAIQI|flood_purchase_unknown|city="..pending.id)
    pending.errorLogged=true
  end
  return ok and result==true
end
