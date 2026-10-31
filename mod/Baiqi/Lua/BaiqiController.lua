include("BaiqiConfig")
include("BaiqiPolicy")
include("BaiqiPlanner")

BaiqiController = {}
local C = BaiqiConfig
local elapsed, turn, requestCount, serial = 0, -1, 0, 0
local attempts, pendingUnits, pendingCities, reservations = {}, {}, {}, {}
local cityEvaluated, unitEvaluated, settlementTargets = {}, {}, {}
local queuedSettings = {}
local stopped, running = false, false
local status = "正在初始化托管"
local contextID, visibility
local lastReasons = {}

local function Log(kind, details)
  print("BAIQI|"..kind.."|turn="..tostring(Game.GetCurrentGameTurn()).."|"..(details or ""))
end

local function Reason(key, text)
  status = text
  if lastReasons[key] ~= text then Log("wait", "key="..key.."|reason="..text); lastReasons[key] = text end
end

local function PlayerContext()
  local id = Game.GetLocalPlayer()
  if id == nil or id < 0 or GameConfiguration.IsAnyMultiplayer() or GameConfiguration.IsHotseat() then return nil end
  local player, config = Players[id], PlayerConfigurations[id]
  if player == nil or config == nil or config:GetLeaderTypeName() ~= C.leader or not config:IsHuman() then return nil end
  local state = player:GetProperty(C.stateKey)
  if state == nil then state = {version=1, enabled=true, cities={}, units={}, protected={}} end
  if type(state) ~= "table" or state.version ~= C.version or type(state.cities) ~= "table"
    or type(state.units) ~= "table" or type(state.protected) ~= "table" then
    Reason("state", "托管存档版本不受支持，已停止操作"); return nil
  end
  return {player=id, localPlayer=id, isBaiqi=true, activeTurn=player:IsTurnActive(), enabled=state.enabled == true}, player, state
end

function BaiqiController.IsAvailable() return PlayerContext() ~= nil end

local function CityPaused(state, city)
  local record = state.cities[tostring(city:GetID())]
  return record ~= nil and record.x == city:GetX() and record.y == city:GetY() and record.paused == true
end

local function IsProtected(state, plot) return state.protected[tostring(plot:GetIndex())] == true end

local function SaveSetting(kind, id, value)
  local ctx = PlayerContext()
  if ctx == nil or ctx.activeTurn ~= true then return end
  local key = kind..":"..tostring(id)
  queuedSettings[key] = {kind=kind, id=id, value=value, turn=Game.GetCurrentGameTurn()}
  UI.RequestPlayerOperation(ctx.player, PlayerOperations.EXECUTE_SCRIPT,
    {OnStart="BaiqiSettings", kind=kind, id=id, value=value, turn=Game.GetCurrentGameTurn()})
  status = "正在保存托管设置"
end

local function SettingsAcknowledged(state)
  for key, setting in pairs(queuedSettings) do
    local value
    if setting.kind == "global" then value = state.enabled
    elseif setting.kind == "unit" then value = state.units[tostring(setting.id)]
    elseif setting.kind == "protect" then value = state.protected[tostring(setting.id)]
    elseif setting.kind == "city" then
      local record = state.cities[tostring(setting.id)]; value = record and record.paused
    end
    if value == setting.value then queuedSettings[key] = nil end
  end
  if next(queuedSettings) ~= nil then status = "等待设置确认；自动操作已暂停"; return false end
  return true
end

function BaiqiController.ToggleGlobal()
  local ctx, player, state = PlayerContext()
  if ctx then SaveSetting("global", nil, not state.enabled) end
end

function BaiqiController.ToggleCity()
  local ctx, player, state = PlayerContext()
  local city = UI.GetHeadSelectedCity()
  if ctx and city and city:GetOwner() == ctx.player then SaveSetting("city", city:GetID(), not CityPaused(state, city)) end
end

function BaiqiController.ToggleUnit()
  local ctx, player, state = PlayerContext()
  local unit = UI.GetHeadSelectedUnit()
  if ctx and unit and unit:GetOwner() == ctx.player then
    local def = GameInfo.Units[unit:GetUnitType()]
    if def and (def.UnitType == "UNIT_SETTLER" or def.UnitType == "UNIT_BUILDER") then
      SaveSetting("unit", unit:GetID(), state.units[tostring(unit:GetID())] ~= true)
    end
  end
end

function BaiqiController.ProtectPlot()
  local ctx, player, state = PlayerContext()
  local unit = UI.GetHeadSelectedUnit()
  local city = UI.GetHeadSelectedCity()
  local plot = unit and Map.GetPlot(unit:GetX(), unit:GetY()) or (city and Map.GetPlot(city:GetX(), city:GetY()))
  if ctx and plot and plot:GetOwner() == ctx.player then SaveSetting("protect", plot:GetIndex(), not IsProtected(state, plot)) end
end

local function Revealed(plot)
  return plot ~= nil and visibility ~= nil and visibility:IsRevealed(plot:GetX(), plot:GetY()) == true
end

-- Safety reads only currently visible units. No hidden-unit threat information.
local function Safe(plot, player)
  if not Revealed(plot) then return false end
  for dx=-C.threatRadius,C.threatRadius do
    for dy=-C.threatRadius,C.threatRadius do
      local near = Map.GetPlotXYWithRangeCheck(plot:GetX(), plot:GetY(), dx, dy, C.threatRadius)
      if near and visibility:IsVisible(near:GetX(), near:GetY()) then
        for _, other in pairs(Units.GetUnitsInPlot(near) or {}) do
          if other:GetOwner() ~= contextID and player:GetDiplomacy():IsAtWarWith(other:GetOwner()) then return false end
        end
      end
    end
  end
  return true
end

local function ResourceVisible(plot, player)
  local index = plot:GetResourceType()
  local row = index and GameInfo.Resources[index]
  return row ~= nil and player:GetResources():IsResourceVisible(row.Hash) == true
end

local function ClearPlot(plot, state, player)
  return Revealed(plot) and not IsProtected(state, plot) and not plot:IsCity()
    and not plot:IsNaturalWonder() and not plot:IsNationalPark()
    and plot:GetDistrictType() == -1 and plot:GetImprovementType() == -1
    and plot:GetFeatureType() == -1 and not ResourceVisible(plot, player)
end

local function NextRequest(key)
  if attempts[key] or requestCount >= C.requestsPerTurn then return nil end
  attempts[key] = true
  requestCount, serial = requestCount + 1, serial + 1
  return tostring(contextID)..":"..tostring(turn)..":"..tostring(serial)
end

local function UnitSnapshot(unit, state)
  local def = GameInfo.Units[unit:GetUnitType()]
  return {id=unit:GetID(), owner=unit:GetOwner(), type=def and def.UnitType,
    paused=state.units[tostring(unit:GetID())] == true,
    formationCount=unit.GetFormationUnitCount and unit:GetFormationUnitCount() or nil,
    moves=unit:GetMovesRemaining(), plot=unit:GetPlotId()}
end

local function RequestCivilian(ctx, state, unit, operation, plot, improvement)
  -- Re-read ownership, active player and persisted settings at the write boundary.
  local freshCtx, freshPlayer, freshState = PlayerContext()
  ctx, state = freshCtx, freshState
  if ctx == nil or not SettingsAcknowledged(state) then return false, "context_changed" end
  local allowed, reason = BaiqiPolicy.CanCivilian(ctx, UnitSnapshot(unit, state))
  local def = GameInfo.Units[unit:GetUnitType()]
  if not allowed or not BaiqiPolicy.ActionAllowed(def.UnitType, operation) then return false, reason end
  if not Safe(plot, Players[ctx.player]) or IsProtected(state, plot) then return false, "unsafe_or_protected" end
  local params = {}
  local action = UnitOperationTypes[operation]
  if action == nil then return false, "operation_unavailable" end
  if operation == "MOVE_TO" then
    if Map.GetPlotDistance(unit:GetX(), unit:GetY(), plot:GetX(), plot:GetY()) ~= 1 then return false, "not_adjacent" end
    if plot:GetOwner() ~= -1 and plot:GetOwner() ~= ctx.player then return false, "foreign_border" end
    params[UnitOperationTypes.PARAM_X], params[UnitOperationTypes.PARAM_Y] = plot:GetX(), plot:GetY()
  else
    if plot:GetIndex() ~= unit:GetPlotId() then return false, "not_current_plot" end
    if operation == "BUILD_IMPROVEMENT" then
      if improvement == nil or plot:GetOwner() ~= ctx.player then return false, "invalid_improvement" end
      params[UnitOperationTypes.PARAM_X], params[UnitOperationTypes.PARAM_Y] = unit:GetX(), unit:GetY()
      params[UnitOperationTypes.PARAM_IMPROVEMENT_TYPE] = improvement
    elseif operation == "REPAIR" and plot:GetOwner() ~= ctx.player then return false, "foreign_repair" end
  end
  if UnitManager.CanStartOperation(unit, action, nil, params) ~= true then return false, "engine_rejected" end
  local key = "unit:"..unit:GetID()..":"..unit:GetPlotId()..":"..operation..":"..plot:GetIndex()..":"..tostring(improvement)
  local id = NextRequest(key)
  if id == nil or pendingUnits[unit:GetID()] ~= nil then return false, "already_pending_or_budget" end
  pendingUnits[unit:GetID()] = {id=id, operation=action, plot=plot:GetIndex(), from=unit:GetPlotId(), kind=operation, moves=unit:GetMovesRemaining()}
  Log("request", "id="..id.."|source=BACKGROUND|unit="..unit:GetID().."|operation="..operation.."|plot="..plot:GetIndex())
  UnitManager.RequestOperation(unit, action, params)
  return true, "submitted"
end

local function PathStep(unit, target, player, state)
  if not Revealed(target) or not Safe(target, player) then return nil end
  local path = UnitManager.GetMoveToPathEx(unit, target:GetIndex())
  if type(path) ~= "table" or type(path.plots) ~= "table" or #path.plots < 2 or #path.plots > C.pathLimit then return nil end
  if path.plots[1] ~= unit:GetPlotId() or path.plots[#path.plots] ~= target:GetIndex() then return nil end
  for _, index in ipairs(path.plots) do
    local p = Map.GetPlotByIndex(index)
    if p == nil or not Revealed(p) or not Safe(p, player) or IsProtected(state, p)
      or (p:GetOwner() ~= -1 and p:GetOwner() ~= contextID) then return nil end
  end
  return Map.GetPlotByIndex(path.plots[2])
end

local function SettlementSites(player, state, unit)
  local result = {}
  local ai = player:GetGrandStrategicAI()
  if ai == nil then return result end
  for rank, recommendation in pairs(ai:GetSettlementRecommendations(12) or {}) do
    local plot = Map.GetPlotByIndex(recommendation.SettlingLocation)
    if plot and Revealed(plot) and not plot:IsWater() and not plot:IsImpassable() and not plot:IsCity()
      and plot:GetFeatureType() == -1
      and (plot:GetOwner() == -1 or plot:GetOwner() == contextID) and Safe(plot, player) and not IsProtected(state, plot) then
      -- Recommendations are hints. FOUND_CITY legality is checked at the destination.
      local distantEnough = true
      for _, owner in pairs(PlayerManager.GetAliveIDs()) do
        for _, city in Players[owner]:GetCities():Members() do
          if Revealed(Map.GetPlot(city:GetX(),city:GetY())) and Map.GetPlotDistance(plot:GetX(),plot:GetY(),city:GetX(),city:GetY()) <= 3 then distantEnough=false end
        end
      end
      local step = unit and PathStep(unit, plot, player, state) or nil
      if distantEnough and (unit == nil or step ~= nil or unit:GetPlotId() == plot:GetIndex()) then
        result[#result+1] = {index=plot:GetIndex(), score=100-(tonumber(rank) or 0), legal=true, revealed=true, safe=true,
          protected=false, plot=plot, step=step}
      end
    end
  end
  return result
end

local function ProcessSettler(ctx, player, state, unit)
  local here = Map.GetPlotByIndex(unit:GetPlotId())
  local target = BaiqiPlanner.Site(SettlementSites(player, state, unit), reservations, unit:GetID())
  local mayFound = player:GetCities():GetCount() == 0
    or settlementTargets[unit:GetID()] == here:GetIndex()
    or (target ~= nil and target.index == here:GetIndex())
  if mayFound and not IsProtected(state, here) and Safe(here, player)
    and UnitManager.CanStartOperation(unit, UnitOperationTypes.FOUND_CITY) == true then
    return RequestCivilian(ctx, state, unit, "FOUND_CITY", here)
  end
  if target and target.step then
    reservations[target.index] = unit:GetID()
    settlementTargets[unit:GetID()] = target.index
    return RequestCivilian(ctx, state, unit, "MOVE_TO", target.step)
  end
  Reason("settler:"..unit:GetID(), "移民等待已探明的安全城址或路线")
  return false
end

local function ProcessBuilder(ctx, player, state, unit)
  local here = Map.GetPlotByIndex(unit:GetPlotId())
  if here:GetOwner() == ctx.player and not IsProtected(state, here) and Safe(here, player) then
    if here:IsImprovementPillaged() and UnitManager.CanStartOperation(unit, UnitOperationTypes.REPAIR) then
      return RequestCivilian(ctx, state, unit, "REPAIR", here)
    end
    local best
    for row in GameInfo.Improvements() do
      if here:GetImprovementType() == -1 then
        local params = {[UnitOperationTypes.PARAM_X]=unit:GetX(), [UnitOperationTypes.PARAM_Y]=unit:GetY(),
          [UnitOperationTypes.PARAM_IMPROVEMENT_TYPE]=row.Hash}
        if UnitManager.CanStartOperation(unit, UnitOperationTypes.BUILD_IMPROVEMENT, nil, params) == true
          and (best == nil or row.Index < best.Index) then best=row end
      end
    end
    if best then return RequestCivilian(ctx, state, unit, "BUILD_IMPROVEMENT", here, best.Hash) end
  end
  local targets = {}
  for _, city in player:GetCities():Members() do
    local ai = city:GetCityAI()
    if ai then
      for _, rec in pairs(ai:GetImprovementRecommendationsForBuilder(unit:GetComponentID()) or {}) do
        local plot = Map.GetPlotByIndex(rec.ImprovementLocation)
        if plot and plot:GetOwner() == ctx.player and not IsProtected(state, plot) then
          local step=PathStep(unit, plot, player, state)
          if step then targets[#targets+1]={plot=plot,step=step,index=plot:GetIndex(),distance=Map.GetPlotDistance(unit:GetX(),unit:GetY(),plot:GetX(),plot:GetY())} end
        end
      end
    end
  end
  table.sort(targets,function(a,b) if a.distance~=b.distance then return a.distance<b.distance end return a.index<b.index end)
  if targets[1] then return RequestCivilian(ctx,state,unit,"MOVE_TO",targets[1].step) end
  return false
end

local function Military(row) return (row.Combat or 0) > 0 or (row.RangedCombat or 0) > 0 or row.FormationClass == "FORMATION_CLASS_SUPPORT" end

local function Economy(player)
  local s = {cities=player:GetCities():GetCount(), army=0, builders=0, settlers=0,
    queuedArmy=0, queuedBuilders=0, queuedSettlers=0, reservedSettlers=0, committedMaintenance=0,
    gold=player:GetTreasury():GetGoldBalance(), netGold=player:GetTreasury():GetGoldYield()-player:GetTreasury():GetTotalMaintenance()}
  for _, unit in player:GetUnits():Members() do
    local row=GameInfo.Units[unit:GetUnitType()]
    if row.UnitType=="UNIT_BUILDER" then s.builders=s.builders+1
    elseif row.UnitType=="UNIT_SETTLER" then s.settlers=s.settlers+1
    elseif Military(row) then s.army=s.army+1 end
  end
  for _, city in player:GetCities():Members() do
    local q=city:GetBuildQueue()
    for i=0,q:GetSize()-1 do
      local entry=q:GetAt(i)
      local row=entry and entry.UnitType and GameInfo.Units[entry.UnitType]
      if row then
        s.committedMaintenance=s.committedMaintenance+(row.Maintenance or 0)
        if row.UnitType=="UNIT_BUILDER" then s.queuedBuilders=s.queuedBuilders+1
        elseif row.UnitType=="UNIT_SETTLER" then s.queuedSettlers=s.queuedSettlers+1
        elseif Military(row) then s.queuedArmy=s.queuedArmy+1 end
      end
    end
  end
  return s
end

local buildingPriority = {BUILDING_GRANARY=110,BUILDING_MONUMENT=100,BUILDING_WATER_MILL=95,
  BUILDING_WORKSHOP=90,BUILDING_MARKET=85,BUILDING_LIBRARY=80,BUILDING_BARRACKS=75,BUILDING_LIGHTHOUSE=85}
local districtPriority = {DISTRICT_INDUSTRIAL_ZONE=72,DISTRICT_COMMERCIAL_HUB=70,DISTRICT_HARBOR=70,
  DISTRICT_CAMPUS=68,DISTRICT_ENCAMPMENT=65,DISTRICT_AQUEDUCT=60,DISTRICT_NEIGHBORHOOD=55}

local function BuildParams(candidate)
  local params = {[CityOperationTypes.PARAM_INSERT_MODE]=CityOperationTypes.VALUE_APPEND}
  local keys = {building=CityOperationTypes.PARAM_BUILDING_TYPE,district=CityOperationTypes.PARAM_DISTRICT_TYPE,
    unit=CityOperationTypes.PARAM_UNIT_TYPE,project=CityOperationTypes.PARAM_PROJECT_TYPE}
  local key=keys[candidate.kind]
  if key==nil then return nil end
  params[key]=candidate.hash
  if candidate.placement then params[CityOperationTypes.PARAM_X]=candidate.placement.x; params[CityOperationTypes.PARAM_Y]=candidate.placement.y end
  return params
end

local function ProcessCity(ctx, player, state, city)
  local q=city:GetBuildQueue()
  if CityPaused(state,city) or q:GetSize() ~= 0 or q:GetCurrentProductionTypeHash() ~= 0 or pendingCities[city:GetID()] then return false end
  if cityEvaluated[city:GetID()]==turn then return false end
  cityEvaluated[city:GetID()]=turn
  local candidates, checked = {}, 0
  local function Add(kind,row,score,repair,placement)
    if checked >= C.candidatesPerCity then return end
    checked=checked+1
    -- Both CanProduce modes are required by the shipped ProductionPanel.
    -- Exclusion checks alone can say true for a building behind an unknown tech.
    if q:CanProduce(row.Hash,true) ~= true or q:CanProduce(row.Hash,false,true) ~= true then return end
    local c={kind=kind,hash=row.Hash,index=checked,type=row.BuildingType or row.DistrictType or row.UnitType or row.ProjectType,
      score=score,repair=repair,placement=placement}
    local params=BuildParams(c)
    if params and CityManager.CanStartOperation(city,CityOperationTypes.BUILD,params,true)==true then c.legal=true; candidates[#candidates+1]=c end
  end
  local treasury=player:GetTreasury()
  local netGold=treasury:GetGoldYield()-treasury:GetTotalMaintenance()
  for row in GameInfo.Buildings() do
    local repair=city:GetBuildings():IsPillaged(row.Index)
    if not row.IsWonder and (not row.RequiresPlacement or repair) and (not row.MustPurchase or repair)
      and ((row.Maintenance or 0)==0 or netGold-(row.Maintenance or 0)>=C.netGoldMin or repair) then
      Add("building",row,buildingPriority[row.BuildingType] or 40,repair)
    end
  end
  local plots={}
  for _,index in pairs(Map.GetCityPlots():GetPurchasedPlots(city) or {}) do plots[#plots+1]=index end
  table.sort(plots)
  for row in GameInfo.Districts() do
    if row.DistrictType~="DISTRICT_CITY_CENTER" and q:CanProduce(row.Hash,true) then
      if q:HasBeenPlaced(row.Hash) then Add("district",row,districtPriority[row.DistrictType] or 35,true)
      else
        for _, index in ipairs(plots) do
          local plot=Map.GetPlotByIndex(index)
          if plot and plot:GetOwner()==ctx.player and ClearPlot(plot,state,player)
            and plot:CanHaveDistrict(row.Index,ctx.player,city:GetID()) then
            Add("district",row,districtPriority[row.DistrictType] or 35,false,{x=plot:GetX(),y=plot:GetY()})
          end
        end
      end
    end
  end
  local economy=Economy(player)
  economy.cityPopulation=city:GetPopulation()
  economy.hasSafeSite=#SettlementSites(player,state,nil)>0
  for row in GameInfo.Units() do
    local role=row.UnitType=="UNIT_BUILDER" and "builder" or (row.UnitType=="UNIT_SETTLER" and "settler" or (Military(row) and "military" or nil))
    if role then
      economy.maintenance=row.Maintenance or 0
      economy.resourceAffordable=q:CanProduce(row.Hash,false,true)==true
      if BaiqiPlanner.AllowRecruit(role,economy,C) then
        local priority=role=="settler" and 105 or (role=="builder" and 95 or 55)
        Add("unit",row,priority,false)
      end
    end
  end
  for row in GameInfo.Projects() do Add("project",row,1,false) end
  local choice=BaiqiPlanner.Choose({paused=false,queueEmpty=true},candidates)
  if choice == nil then Reason("city:"..city:GetID(),"城市等待合法生产或预算"); return false end
  -- All state and legality are checked again at the write boundary.
  local freshCtx, freshPlayer, freshState=PlayerContext()
  if not BaiqiPolicy.Context(freshCtx) or CityPaused(freshState,city) or city:GetOwner()~=freshCtx.player
    or q:GetSize()~=0 or q:GetCurrentProductionTypeHash()~=0 then return false end
  local params=BuildParams(choice)
  if q:CanProduce(choice.hash,true)~=true or q:CanProduce(choice.hash,false,true)~=true
    or CityManager.CanStartOperation(city,CityOperationTypes.BUILD,params,true)~=true then return false end
  local id=NextRequest("city:"..city:GetID())
  if id==nil then return false end
  pendingCities[city:GetID()]={id=id,hash=choice.hash}
  Log("request","id="..id.."|source=BACKGROUND|city="..city:GetID().."|type="..choice.type)
  CityManager.RequestOperation(city,CityOperationTypes.BUILD,params)
  return true
end

local function ReadBack(player)
  for unitID, pending in pairs(pendingUnits) do
    local unit=player:GetUnits():FindID(unitID)
    if unit==nil or unit:GetOwner()~=contextID or unit:GetPlotId()~=pending.from or unit:GetMovesRemaining()~=pending.moves then
      Log("observed","id="..pending.id.."|unit="..unitID.."|kind="..pending.kind)
      pendingUnits[unitID]=nil
    end
  end
  for cityID,pending in pairs(pendingCities) do
    local city=player:GetCities():FindID(cityID)
    if city==nil then pendingCities[cityID]=nil
    elseif city:GetBuildQueue():GetCurrentProductionTypeHash()~=0 then
      Log("queue_observed","id="..pending.id.."|city="..cityID.."|hash="..city:GetBuildQueue():GetCurrentProductionTypeHash())
      pendingCities[cityID]=nil
    end
  end
end

local function Tick()
  if stopped or running then return end
  local ctx,player,state=PlayerContext()
  if ctx==nil then return end
  contextID=ctx.player
  if not SettingsAcknowledged(state) or not BaiqiPolicy.Context(ctx) then return end
  visibility=PlayersVisibility[ctx.player]
  if visibility==nil then return end
  local current=Game.GetCurrentGameTurn()
  if current~=turn then
    turn=current; requestCount=0; attempts={}; reservations={}; lastReasons={}; cityEvaluated={}; unitEvaluated={}
  end
  ReadBack(player)
  for _,city in player:GetCities():Members() do
    if ProcessCity(ctx,player,state,city) then status="已安排生产；军队等待你的命令"; return end
  end
  for _,unit in player:GetUnits():Members() do
    local snapshot=UnitSnapshot(unit,state)
    local unitKey=unit:GetID()..":"..unit:GetPlotId()..":"..tostring(unit:GetMovesRemaining())
    if not unitEvaluated[unitKey] and pendingUnits[unit:GetID()]==nil and BaiqiPolicy.CanCivilian(ctx,snapshot) then
      unitEvaluated[unitKey]=true
      if snapshot.type=="UNIT_SETTLER" then
        if ProcessSettler(ctx,player,state,unit) then status="已提交移民操作，等待实际结果"; return end
      elseif snapshot.type=="UNIT_BUILDER" then
        if ProcessBuilder(ctx,player,state,unit) then status="已提交建造者操作，等待实际结果"; return end
      end
    end
  end
end

function BaiqiController.RunNow()
  local ok,err=pcall(Tick)
  if not ok then stopped=true; status="托管因脚本错误停止，请查看 Lua.log"; Log("error",tostring(err)) end
end

function BaiqiController.Update(delta)
  elapsed=elapsed+delta
  if elapsed>=C.interval then elapsed=0; BaiqiController.RunNow() end
end

function BaiqiController.GetStatus()
  local ctx,player,state=PlayerContext()
  if ctx==nil then return status end
  if state.enabled~=true then return "内政托管已关闭" end
  if stopped then return status end
  local text=status
  local city=UI.GetHeadSelectedCity()
  local unit=UI.GetHeadSelectedUnit()
  if city and city:GetOwner()==ctx.player then text=text.."[NEWLINE]所选城市："..(CityPaused(state,city) and "手动" or "托管") end
  if unit and unit:GetOwner()==ctx.player then text=text.."[NEWLINE]所选单位："..(state.units[tostring(unit:GetID())] and "手动" or "文职按资格托管，军队由你指挥") end
  return text
end

local function OnUnitOperation(playerID,unitID,operation)
  if playerID~=Game.GetLocalPlayer() then return end
  local ctx,player,state=PlayerContext()
  if ctx==nil then return end
  local unit=player:GetUnits():FindID(unitID)
  if unit==nil then return end
  local row=GameInfo.Units[unit:GetUnitType()]
  if row==nil or (row.UnitType~="UNIT_SETTLER" and row.UnitType~="UNIT_BUILDER") then return end
  local pending=pendingUnits[unitID]
  if pending and pending.operation==operation then return end
  if state.units[tostring(unitID)]~=true then SaveSetting("unit",unitID,true); Log("manual_takeover","unit="..unitID) end
end

Events.UnitOperationStarted.Add(OnUnitOperation)
local function OnCityCompleted(playerID,cityID)
  if playerID==Game.GetLocalPlayer() then cityEvaluated[cityID]=nil end
end
Events.CityProductionCompleted.Add(OnCityCompleted)
function BaiqiController.Shutdown()
  stopped=true
  Events.UnitOperationStarted.Remove(OnUnitOperation)
  Events.CityProductionCompleted.Remove(OnCityCompleted)
end
print("BAIQI|ui_controller_loaded|version=1")
