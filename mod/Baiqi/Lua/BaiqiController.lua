include("BaiqiConfig")
include("BaiqiPolicy")
include("BaiqiPlanner")

BaiqiController = {}
local C = BaiqiConfig
local elapsed, turn, requestCount, serial = 0, -1, 0, 0
local attempts, pendingUnits, pendingCities, reservations = {}, {}, {}, {}
local cityEvaluated, unitEvaluated, settlementTargets = {}, {}, {}
local stopped, running = false, false
local status = "内政托管开启；军队等待你的命令"
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
  if id == nil or id < 0 or GameConfiguration.IsAnyMultiplayer()
    or (GameConfiguration.IsHotseat and GameConfiguration.IsHotseat()) then return nil end
  local player, config = Players[id], PlayerConfigurations[id]
  if player == nil or config == nil or config:GetLeaderTypeName() ~= C.leader or not config:IsHuman() then return nil end
  return {player=id, localPlayer=id, isBaiqi=true, activeTurn=player:IsTurnActive(), enabled=true}, player, {}
end

function BaiqiController.IsAvailable() return PlayerContext() ~= nil end

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
  return Revealed(plot) and not plot:IsCity()
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

-- Match shipped WorldInput: use one coordinate-derived plot for planning,
-- legality, packets and observations. Never mix independent position getters.
local function UnitPlot(unit)
  local x,y=unit:GetX(),unit:GetY()
  if not BaiqiPolicy.Number(x) or not BaiqiPolicy.Number(y) or x<0 or y<0
    or x%1~=0 or y%1~=0 then return nil end
  local plot=Map.GetPlot(x,y)
  if plot and plot:GetX()==x and plot:GetY()==y then return plot end
end

local function UnitIndex(unit)
  local plot=UnitPlot(unit)
  return plot and plot:GetIndex()
end

local function UnitKey(unit)
  return unit:GetID()..":"..tostring(UnitIndex(unit))..":"..tostring(unit:GetMovesRemaining())
end

local function UnitSnapshot(unit, state)
  local def = GameInfo.Units[unit:GetUnitType()]
  return {id=unit:GetID(), owner=unit:GetOwner(), type=def and def.UnitType,
    paused=false,
    formationCount=unit.GetFormationUnitCount and unit:GetFormationUnitCount() or nil,
    tradeIdle=def and def.UnitType=="UNIT_TRADER" and UnitManager.GetActivityType~=nil
      and UnitManager.GetActivityType(unit)==ActivityTypes.ACTIVITY_AWAKE,
    moves=unit:GetMovesRemaining(), plot=UnitIndex(unit)}
end

local function TradeParams(ctx,player,unit,plot)
  if UnitManager.GetActivityType(unit)~=ActivityTypes.ACTIVITY_AWAKE then return nil end
  local trade=player:GetTrade()
  local reserved=0
  for _,p in pairs(pendingUnits) do if p.kind=="MAKE_TRADE_ROUTE" then reserved=reserved+1 end end
  if trade:GetNumOutgoingRoutes()+reserved>=trade:GetOutgoingRouteCapacity() then return nil end
  local origin=Cities.GetCityInPlot(unit:GetX(),unit:GetY())
  local dest=plot and Cities.GetCityInPlot(plot:GetX(),plot:GetY())
  if not origin or not dest or origin:GetOwner()~=ctx.player or dest:GetOwner()~=ctx.player
    or origin:GetID()==dest:GetID() then return nil end
  local path,entrances,exits=Game.GetTradeManager():GetTradeRoutePath(ctx.player,origin:GetID(),ctx.player,dest:GetID())
  if type(path)~="table" or next(path)==nil then return nil end
  local length=0
  for _,index in pairs(path) do
    local p=Map.GetPlotByIndex(index)
    if not Safe(p,player) or (p:GetOwner()~=-1 and p:GetOwner()~=ctx.player) then return nil end
    length=length+1
  end
  for _,portals in pairs({entrances or {},exits or {}}) do
    for _,index in pairs(portals) do
      if index>=0 and not Safe(Map.GetPlotByIndex(index),player) then return nil end
    end
  end
  local params={[UnitOperationTypes.PARAM_X0]=dest:GetX(),[UnitOperationTypes.PARAM_Y0]=dest:GetY(),
    [UnitOperationTypes.PARAM_X1]=unit:GetX(),[UnitOperationTypes.PARAM_Y1]=unit:GetY()}
  if UnitManager.CanStartOperation(unit,UnitOperationTypes.MAKE_TRADE_ROUTE,nil,params)~=true then return nil end
  return params,origin,dest,length
end

local function RequestCivilian(ctx, state, unit, operation, plot, improvement)
  -- Re-read ownership and active player at the write boundary. No takeover flags.
  local freshCtx, freshPlayer, freshState = PlayerContext()
  ctx, state = freshCtx, freshState
  if ctx == nil then return false, "context_changed" end
  local here=UnitPlot(unit)
  if not here then return false,"position_unavailable" end
  local allowed, reason = BaiqiPolicy.CanCivilian(ctx, UnitSnapshot(unit, state))
  local def = GameInfo.Units[unit:GetUnitType()]
  if not allowed or not BaiqiPolicy.ActionAllowed(def.UnitType, operation) then return false, reason end
  if operation~="SKIP_TURN" and not Safe(plot, Players[ctx.player]) then return false, "unsafe" end
  local params,origin,dest = {}
  local action = UnitOperationTypes[operation]
  if operation=="SKIP_TURN" and action==nil then
    local row=GameInfo.UnitOperations and GameInfo.UnitOperations.UNITOPERATION_SKIP_TURN
    action=row and row.Hash
  end
  if action == nil then return false, "operation_unavailable" end
  if operation=="MAKE_TRADE_ROUTE" then
    params,origin,dest=TradeParams(ctx,freshPlayer,unit,plot)
    if not params then return false,"no_safe_domestic_route" end
  elseif operation == "MOVE_TO" then
    if Map.GetPlotDistance(here:GetX(), here:GetY(), plot:GetX(), plot:GetY()) ~= 1 then return false, "not_adjacent" end
    if plot:GetOwner() ~= -1 and plot:GetOwner() ~= ctx.player then return false, "foreign_border" end
    if visibility:IsVisible(plot:GetX(),plot:GetY()) then
      for _,other in pairs(Units.GetUnitsInPlot(plot) or {}) do
        local row=GameInfo.Units[other:GetUnitType()]
        if other:GetOwner()==ctx.player and other:GetID()~=unit:GetID() and row
          and (row.UnitType=="UNIT_SETTLER" or row.UnitType=="UNIT_BUILDER") then
          return false,"civilian_target_occupied"
        end
      end
    end
    params[UnitOperationTypes.PARAM_X], params[UnitOperationTypes.PARAM_Y] = plot:GetX(), plot:GetY()
  else
    if plot:GetIndex() ~= here:GetIndex() then return false, "not_current_plot" end
    if operation == "BUILD_IMPROVEMENT" then
      if improvement == nil or plot:GetOwner() ~= ctx.player then return false, "invalid_improvement" end
      params[UnitOperationTypes.PARAM_X], params[UnitOperationTypes.PARAM_Y] = here:GetX(), here:GetY()
      params[UnitOperationTypes.PARAM_IMPROVEMENT_TYPE] = improvement
    elseif operation == "REPAIR" and plot:GetOwner() ~= ctx.player then return false, "foreign_repair" end
  end
  if UnitManager.CanStartOperation(unit, action, nil, params) ~= true then return false, "engine_rejected" end
  if UnitIndex(unit)~=here:GetIndex() then return false,"position_changed" end
  local key = "unit:"..unit:GetID()..":"..here:GetIndex()..":"..operation..":"..plot:GetIndex()..":"..tostring(improvement)
  local id = NextRequest(key)
  if id == nil or pendingUnits[unit:GetID()] ~= nil then return false, "already_pending_or_budget" end
  pendingUnits[unit:GetID()] = {id=id, operation=action, plot=plot:GetIndex(), from=here:GetIndex(), kind=operation, moves=unit:GetMovesRemaining(),elapsed=0}
  if origin then pendingUnits[unit:GetID()].origin=origin:GetID();pendingUnits[unit:GetID()].destination=dest:GetID() end
  Log("request", "id="..id.."|source=BACKGROUND|unit="..unit:GetID().."|operation="..operation.."|plot="..plot:GetIndex().."|from="..here:GetIndex())
  UnitManager.RequestOperation(unit, action, params)
  return true, "submitted"
end

local function PathStep(unit, target, player, state)
  if not Revealed(target) or not Safe(target, player) then return nil end
  local start=UnitIndex(unit)
  if start==nil then return nil end
  local path = UnitManager.GetMoveToPathEx(unit, target:GetIndex())
  if type(path) ~= "table" or type(path.plots) ~= "table" or #path.plots < 2 or #path.plots > C.pathLimit then return nil end
  if path.plots[1] ~= start or path.plots[#path.plots] ~= target:GetIndex() or UnitIndex(unit)~=start then return nil end
  for _, index in ipairs(path.plots) do
    local p = Map.GetPlotByIndex(index)
    if p == nil or not Revealed(p) or not Safe(p, player)
      or (p:GetOwner() ~= -1 and p:GetOwner() ~= contextID) then return nil end
  end
  return Map.GetPlotByIndex(path.plots[2])
end

local function DistrictPersonData(unit)
  local def=GameInfo.Units[unit:GetUnitType()]
  local classType=def and BaiqiPolicy.DistrictGreatPersonClass(def.UnitType)
  if not classType then return nil end
  local gp=unit:GetGreatPerson()
  if not gp or not BaiqiPolicy.Number(gp:GetActionCharges()) or gp:GetActionCharges()<=0 then return nil end
  local info=GameInfo.GreatPersonIndividuals[gp:GetIndividual()]
  local class=GameInfo.GreatPersonClasses[gp:GetClass()]
  local district=info and info.ActionRequiresCompletedDistrictType and GameInfo.Districts[info.ActionRequiresCompletedDistrictType]
  if not district or not class or class.GreatPersonClassType~=classType or info.GreatPersonClassType~=classType
    or info.ActionRequiresSuzerainTerritory==true or info.ActionRequiresSuzerainTerritory==1
    or info.ActionRequiresSuzerainTerritory=="True" or info.ActionRequiresSuzerainTerritory=="true" then return nil end
  return gp,info,district,class,def
end

local function RequestDistrictPerson(unit)
  local ctx,player,state=PlayerContext()
  if not BaiqiPolicy.CanCivilian(ctx,UnitSnapshot(unit,state))
    or not BaiqiPolicy.ActionAllowed(GameInfo.Units[unit:GetUnitType()].UnitType,"ACTIVATE_GREAT_PERSON") then return false end
  local gp,info,required,class,def=DistrictPersonData(unit)
  local here=UnitPlot(unit)
  local command=GameInfo.UnitCommands and GameInfo.UnitCommands.UNITCOMMAND_ACTIVATE_GREAT_PERSON
  local unitID,individual,charges=unit:GetID(),info and info.Index,gp and gp:GetActionCharges()
  if not gp or not command or not here or here:GetOwner()~=ctx.player or not Safe(here,player)
    or pendingUnits[unit:GetID()] or UnitManager.CanStartCommand(unit,command.Hash,false,true)~=true then return false end
  local freshCtx=PlayerContext()
  local freshGP,freshInfo,_,freshClass,freshDef=DistrictPersonData(unit)
  if not BaiqiPolicy.Context(freshCtx) or freshCtx.player~=ctx.player or not BaiqiPolicy.MatchesID(unit,unitID) or unit:GetOwner()~=freshCtx.player
    or not freshGP or freshInfo.Index~=individual or freshClass.Index~=class.Index or freshDef.UnitType~=def.UnitType
    or freshGP:GetActionCharges()~=charges or UnitIndex(unit)~=here:GetIndex() or here:GetOwner()~=freshCtx.player then return false end
  local id=NextRequest("district_person:"..unitID..":"..individual..":"..charges)
  if not id then return false end
  pendingUnits[unitID]={id=id,kind="ACTIVATE_GREAT_PERSON",command=command.Hash,
    from=here:GetIndex(),moves=unit:GetMovesRemaining(),charges=charges,
    individual=individual,class=class.Index,unitType=def.UnitType,elapsed=0}
  Log("request","id="..id.."|source=BACKGROUND|unit="..unitID.."|command=ACTIVATE_GREAT_PERSON|charges="..charges.."|class="..class.GreatPersonClassType)
  UnitManager.RequestCommand(unit,command.Hash)
  return true
end

local function ProcessDistrictPerson(ctx,player,state,unit)
  local gp,info,required=DistrictPersonData(unit)
  if not gp then
    Reason("district_person:"..unit:GetID(),"文职伟人等待当前支持的区域激活条件")
    return false
  end
  if RequestDistrictPerson(unit) then return true end
  local targets={}
  for _,city in player:GetCities():Members() do
    if city:GetDistricts():HasDistrict(required.Index,true) then
      for _,district in city:GetDistricts():Members() do
        if district:GetType()==required.Index then
          local plot=Map.GetPlot(district:GetX(),district:GetY())
          if plot and plot:GetOwner()==ctx.player then
            local step=PathStep(unit,plot,player,state)
            if step then targets[#targets+1]={plot=plot,step=step,index=plot:GetIndex(),
              distance=Map.GetPlotDistance(unit:GetX(),unit:GetY(),plot:GetX(),plot:GetY())} end
          end
        end
      end
    end
  end
  table.sort(targets,function(a,b) if a.distance~=b.distance then return a.distance<b.distance end return a.index<b.index end)
  if targets[1] then return RequestCivilian(ctx,state,unit,"MOVE_TO",targets[1].step) end
  Reason("district_person:"..unit:GetID(),"文职伟人等待已建成的安全区域与原生激活资格")
  return false
end

local function CreativeData(unit)
  local def=GameInfo.Units[unit:GetUnitType()]
  local expected=def and BaiqiPolicy.CreativeGreatPersonClass(def.UnitType)
  local gp=expected and unit:GetGreatPerson()
  local individual=gp and GameInfo.GreatPersonIndividuals[gp:GetIndividual()]
  local class=gp and GameInfo.GreatPersonClasses[gp:GetClass()]
  -- Native writers have zero action charges even while creation is legal.
  if individual and class and individual.GreatPersonClassType==expected and class.GreatPersonClassType==expected then
    return gp,individual,class,def
  end
end

local function CreativeSites(ctx,player,individual)
  local objects,known,sites={},{},{}
  for work in GameInfo.GreatWorks() do
    if work.GreatPersonIndividualType==individual.GreatPersonIndividualType then objects[work.GreatWorkObjectType]=true end
  end
  for _,city in player:GetCities():Members() do
    if city:GetOwner()==ctx.player then
      local buildings=city:GetBuildings()
      for building in GameInfo.Buildings() do
        if buildings:HasBuilding(building.Index) then
          local empty=false
          local count=buildings:GetNumGreatWorkSlots(building.Index)
          if BaiqiPolicy.Number(count) and count>=0 and count%1==0 then
            for slot=0,count-1 do
              local index=buildings:GetGreatWorkInSlot(building.Index,slot)
              if BaiqiPolicy.Number(index) and index>=0 then known[index]=true
              elseif index==-1 then
                local kind=GameInfo.GreatWorkSlotTypes[buildings:GetGreatWorkSlotType(building.Index,slot)]
                if kind then
                  for compatible in GameInfo.GreatWork_ValidSubTypes() do
                    if compatible.GreatWorkSlotType==kind.GreatWorkSlotType and objects[compatible.GreatWorkObjectType] then empty=true;break end
                  end
                end
              end
            end
          end
          local required=building.PrereqDistrict and GameInfo.Districts[building.PrereqDistrict]
          if empty and required and not building.RequiresPlacement and not buildings:IsPillaged(building.Index)
            and city:GetDistricts():HasDistrict(required.Index,true) then
            for _,district in city:GetDistricts():Members() do
              if district:GetType()==required.Index then
                local plot=Map.GetPlot(district:GetX(),district:GetY())
                if plot and plot:GetOwner()==ctx.player and Safe(plot,player) then
                  sites[#sites+1]={plot=plot,city=city:GetID(),building=building.Index}
                end
              end
            end
          end
        end
      end
    end
  end
  return sites,known
end

local function ProcessCreative(ctx,player,state,unit)
  local gp,individual,class,def=CreativeData(unit)
  if not gp then return false end
  -- One creation in flight prevents separate creators competing for a last slot.
  for _,pending in pairs(pendingUnits) do
    if pending.kind=="CREATE_GREAT_WORK" then Reason("creative_pending","创作等待上一项原生结果");return false end
  end
  local sites,known=CreativeSites(ctx,player,individual)
  local here=UnitPlot(unit)
  local current=false
  for _,site in ipairs(sites) do if here and site.plot:GetIndex()==here:GetIndex() then current=true;break end end
  local command=GameInfo.UnitCommands.UNITCOMMAND_ACTIVATE_GREAT_PERSON
  local unitID=unit:GetID()
  if current and command and here:GetOwner()==ctx.player and Safe(here,player)
    and UnitManager.CanStartCommand(unit,command.Hash,false,true)==true then
    local freshCtx=PlayerContext()
    local freshGP,freshIndividual,freshClass,freshDef=CreativeData(unit)
    if not BaiqiPolicy.Context(freshCtx) or freshCtx.player~=ctx.player or not BaiqiPolicy.MatchesID(unit,unitID)
      or unit:GetOwner()~=ctx.player or not freshGP or freshIndividual.Index~=individual.Index
      or freshClass.Index~=class.Index or freshDef.UnitType~=def.UnitType or UnitIndex(unit)~=here:GetIndex()
      or here:GetOwner()~=ctx.player then return false end
    local id=NextRequest("creative:"..unitID..":"..individual.Index)
    if not id then return false end
    pendingUnits[unitID]={id=id,kind="CREATE_GREAT_WORK",individual=individual.Index,
      individualType=individual.GreatPersonIndividualType,class=class.Index,unitType=def.UnitType,
      knownWorks=known,elapsed=0}
    Log("request","id="..id.."|source=BACKGROUND|unit="..unitID.."|command=CREATE_GREAT_WORK|individual="..individual.Index)
    UnitManager.RequestCommand(unit,command.Hash)
    return true
  end
  local paths={}
  for _,site in ipairs(sites) do
    local step=PathStep(unit,site.plot,player,state)
    if step then paths[#paths+1]={step=step,index=site.plot:GetIndex(),
      distance=Map.GetPlotDistance(unit:GetX(),unit:GetY(),site.plot:GetX(),site.plot:GetY())} end
  end
  table.sort(paths,function(a,b) if a.distance~=b.distance then return a.distance<b.distance end return a.index<b.index end)
  if paths[1] then return RequestCivilian(ctx,state,unit,"MOVE_TO",paths[1].step) end
  Reason("creative:"..unitID,"创作等待安全且有匹配空槽的自有建筑")
  return false
end

local function CreatedWorkObserved(player,pending)
  local event=pending.createdEvent
  if not event or pending.knownWorks[event.work] then return false end
  local city=Cities.GetCityInPlot(event.x,event.y)
  if not city or city:GetOwner()~=contextID then return false end
  local buildings=city:GetBuildings()
  if not buildings:HasBuilding(event.building) then return false end
  local count=buildings:GetNumGreatWorkSlots(event.building)
  if not BaiqiPolicy.Number(count) or count<0 or count%1~=0 then return false end
  for slot=0,count-1 do
    if buildings:GetGreatWorkInSlot(event.building,slot)==event.work then
      local work=GameInfo.GreatWorks[buildings:GetGreatWorkTypeFromIndex(event.work)]
      return work~=nil and work.GreatPersonIndividualType==pending.individualType
    end
  end
  return false
end

local function SettlementSites(player, state, unit)
  local result = {}
  local ai = player:GetGrandStrategicAI()
  if ai == nil then return result end
  for rank, recommendation in pairs(ai:GetSettlementRecommendations(12) or {}) do
    local plot = Map.GetPlotByIndex(recommendation.SettlingLocation)
    if plot and Revealed(plot) and not plot:IsWater() and not plot:IsImpassable() and not plot:IsCity()
      and plot:GetFeatureType() == -1
      and (plot:GetOwner() == -1 or plot:GetOwner() == contextID) and Safe(plot, player) then
      -- Recommendations are hints. FOUND_CITY legality is checked at the destination.
      local distantEnough = true
      for _, owner in pairs(PlayerManager.GetAliveIDs()) do
        for _, city in Players[owner]:GetCities():Members() do
          if Revealed(Map.GetPlot(city:GetX(),city:GetY())) and Map.GetPlotDistance(plot:GetX(),plot:GetY(),city:GetX(),city:GetY()) <= 3 then distantEnough=false end
        end
      end
      local step = unit and PathStep(unit, plot, player, state) or nil
      if distantEnough and (unit == nil or step ~= nil or UnitIndex(unit) == plot:GetIndex()) then
        result[#result+1] = {index=plot:GetIndex(), score=100-(tonumber(rank) or 0), legal=true, revealed=true, safe=true,
          protected=false, plot=plot, step=step}
      end
    end
  end
  return result
end

local function ProcessSettler(ctx, player, state, unit)
  local here = UnitPlot(unit)
  if here==nil then return false end -- Consumed/removed units may remain in a transient collection snapshot.
  local target = BaiqiPlanner.Site(SettlementSites(player, state, unit), reservations, unit:GetID())
  local mayFound = player:GetCities():GetCount() == 0
    or settlementTargets[unit:GetID()] == here:GetIndex()
    or (target ~= nil and target.index == here:GetIndex())
  if mayFound and Safe(here, player)
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
  local here = UnitPlot(unit)
  if here==nil then return false end
  if here:GetOwner() == ctx.player and Safe(here, player) then
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
        if plot and plot:GetOwner() == ctx.player then
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

local function ProcessTrader(ctx,player,state,unit)
  local best,bestLength
  for _,city in player:GetCities():Members() do
    local plot=Map.GetPlot(city:GetX(),city:GetY())
    local params,origin,dest,length=TradeParams(ctx,player,unit,plot)
    if params and (not best or length<bestLength or (length==bestLength and city:GetID()<best:GetID())) then
      best,bestLength=city,length
    end
  end
  if best then return RequestCivilian(ctx,state,unit,"MAKE_TRADE_ROUTE",Map.GetPlot(best:GetX(),best:GetY())) end
  Reason("trader:"..unit:GetID(),"商人等待有容量、已探明且安全的国内商路")
  return false
end

local function CoreIdle()
  return UI.IsGameCoreBusy and not UI.IsGameCoreBusy()
    and UI.IsProcessingMessages and not UI.IsProcessingMessages()
end

local function QueueHeadSignature(q)
  if not q.GetAt or q:GetSize()==0 then return nil end
  local e=q:GetAt(0)
  if type(e)~="table" then return nil end
  local p=e.Location or {}
  return table.concat({tostring(e.Directive),tostring(e.BuildingType),tostring(e.DistrictType),
    tostring(e.UnitType),tostring(e.ProjectType),tostring(p.x),tostring(p.y),tostring(e.Modifiers)},":"),e
end

local function CompletedIdleHead(city,q)
  if q:GetCurrentProductionTypeHash()~=0 then return nil end
  local signature,e=QueueHeadSignature(q)
  if not e then return nil end
  local row,progress,cost
  if e.BuildingType~=nil then
    row=GameInfo.Buildings[e.BuildingType]
    local buildings=city:GetBuildings()
    if not row or not buildings.HasBuilding or buildings:HasBuilding(row.Index)~=true
      or buildings:IsPillaged(row.Index)~=false then return nil end
    progress,cost=q:GetBuildingProgress(row.Index),q:GetBuildingCost(row.Index)
  elseif e.DistrictType~=nil then
    row=GameInfo.Districts[e.DistrictType]
    local districts=city:GetDistricts()
    if not row or row.DistrictType=="DISTRICT_CITY_CENTER" or districts:HasDistrict(row.Index,true)~=true
      or districts:IsPillaged(row.Index)~=false then return nil end
    progress,cost=q:GetDistrictProgress(row.Index),q:GetDistrictCost(row.Index)
  else return nil end -- Units/projects cannot be proved complete by an asset flag.
  if not BaiqiPolicy.Number(progress) or not BaiqiPolicy.Number(cost) or cost<0 or progress<cost then return nil end
  return signature,row
end

local function Economy(player)
  local s = {cities=player:GetCities():GetCount(), army=0, builders=0, settlers=0,
    militaryRoles={recon=0,frontline=0,ranged=0,siege=0,support=0,naval=0,air=0},
    traders=0,queuedTraders=0,tradeCapacity=player.GetTrade and player:GetTrade():GetOutgoingRouteCapacity() or 0,
    queuedArmy=0, queuedBuilders=0, queuedSettlers=0, reservedSettlers=0, committedMaintenance=0,
    gold=player:GetTreasury():GetGoldBalance(), netGold=player:GetTreasury():GetGoldYield()-player:GetTreasury():GetTotalMaintenance()}
  local function CountMilitary(row)
    local role=BaiqiPlanner.MilitaryRole(row)
    if role then s.militaryRoles[role]=s.militaryRoles[role]+1 end
  end
  for _, unit in player:GetUnits():Members() do
    local row=GameInfo.Units[unit:GetUnitType()]
    if row.UnitType=="UNIT_BUILDER" then s.builders=s.builders+1
    elseif row.UnitType=="UNIT_SETTLER" then s.settlers=s.settlers+1
    elseif row.UnitType=="UNIT_TRADER" then s.traders=s.traders+1
    elseif Military(row) then s.army=s.army+1;CountMilitary(row) end
  end
  local function Commitment(row,kind)
    if not row then return end
    s.committedMaintenance=s.committedMaintenance+(row.Maintenance or 0)
    if kind=="unit" then
      if row.UnitType=="UNIT_BUILDER" then s.queuedBuilders=s.queuedBuilders+1
      elseif row.UnitType=="UNIT_SETTLER" then s.queuedSettlers=s.queuedSettlers+1
      elseif row.UnitType=="UNIT_TRADER" then s.queuedTraders=s.queuedTraders+1
      elseif Military(row) then s.queuedArmy=s.queuedArmy+1;CountMilitary(row) end
    end
  end
  for _, city in player:GetCities():Members() do
    local q=city:GetBuildQueue()
    local completedHead=CompletedIdleHead(city,q)
    for i=0,q:GetSize()-1 do
      local entry=q:GetAt(i)
      local row=entry and entry.UnitType and GameInfo.Units[entry.UnitType]
      if i==0 and completedHead then -- Already owned asset; no new commitment.
      elseif row then Commitment(row,"unit")
      elseif entry and entry.BuildingType then Commitment(GameInfo.Buildings[entry.BuildingType],"building")
      elseif entry and entry.DistrictType then Commitment(GameInfo.Districts[entry.DistrictType],"district") end
    end
    -- Reserve new work while either no entry exists or only the replaced,
    -- completed head is visible. Count a real new queue entry only once.
    local pending=pendingCities[city:GetID()]
    if pending and q:GetCurrentProductionTypeHash()==0 and (q:GetSize()==0
      or (pending.replacesHead and QueueHeadSignature(q)==pending.replacesHead)) then
      local tables={unit=GameInfo.Units,building=GameInfo.Buildings,district=GameInfo.Districts,project=GameInfo.Projects}
      local rows=tables[pending.kind]
      Commitment(rows and rows[pending.hash],pending.kind)
    end
  end
  return s
end

local buildingPriority = {BUILDING_GRANARY=110,BUILDING_MONUMENT=100,BUILDING_WATER_MILL=95,
  BUILDING_WORKSHOP=90,BUILDING_MARKET=85,BUILDING_LIBRARY=80,BUILDING_BARRACKS=75,BUILDING_LIGHTHOUSE=85}
local districtPriority = {DISTRICT_INDUSTRIAL_ZONE=72,DISTRICT_COMMERCIAL_HUB=70,DISTRICT_HARBOR=70,
  DISTRICT_CAMPUS=68,DISTRICT_ENCAMPMENT=65,DISTRICT_AQUEDUCT=60,DISTRICT_NEIGHBORHOOD=55}

local function BuildParams(candidate,completedHead)
  local params = {[CityOperationTypes.PARAM_INSERT_MODE]=completedHead and CityOperationTypes.VALUE_REPLACE_AT or CityOperationTypes.VALUE_APPEND}
  if completedHead then params[CityOperationTypes.PARAM_QUEUE_DESTINATION_LOCATION]=0 end
  local keys = {building=CityOperationTypes.PARAM_BUILDING_TYPE,district=CityOperationTypes.PARAM_DISTRICT_TYPE,
    unit=CityOperationTypes.PARAM_UNIT_TYPE,project=CityOperationTypes.PARAM_PROJECT_TYPE}
  local key=keys[candidate.kind]
  if key==nil then return nil end
  params[key]=candidate.hash
  if candidate.placement then params[CityOperationTypes.PARAM_X]=candidate.placement.x; params[CityOperationTypes.PARAM_Y]=candidate.placement.y end
  return params
end

local function CityRequestKey(city,candidate)
  local p=candidate.placement
  return "city:"..city:GetID()..":"..candidate.kind..":"..tostring(candidate.hash)
    ..":"..(p and (p.x..":"..p.y) or "current")
end

local function QueueReady(city,q,completedHead)
  if completedHead then
    return q:GetSize()==1 and CoreIdle() and CompletedIdleHead(city,q)==completedHead
  end
  return q:GetSize()==0 and q:GetCurrentProductionTypeHash()==0
end

local function ProcessCity(ctx, player, state, city)
  local q=city:GetBuildQueue()
  local cityID=city:GetID()
  local completedHead
  if q:GetSize()==1 and CoreIdle() and CityOperationTypes.VALUE_REPLACE_AT~=nil
    and CityOperationTypes.PARAM_QUEUE_DESTINATION_LOCATION~=nil then
    completedHead=CompletedIdleHead(city,q)
  end
  if not QueueReady(city,q,completedHead) or pendingCities[cityID] then return false end
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
    if attempts[CityRequestKey(city,c)] then return end
    local params=BuildParams(c,completedHead)
    if params and CityManager.CanStartOperation(city,CityOperationTypes.BUILD,params,true)==true then c.legal=true; candidates[#candidates+1]=c end
  end
  local treasury=player:GetTreasury()
  local netGold=treasury:GetGoldYield()-treasury:GetTotalMaintenance()
  local economy=Economy(player)
  for row in GameInfo.Buildings() do
    local repair=city:GetBuildings():IsPillaged(row.Index)
    if not row.IsWonder and (not row.RequiresPlacement or repair) and (not row.MustPurchase or repair)
      and ((row.Maintenance or 0)==0 or netGold-economy.committedMaintenance-(row.Maintenance or 0)>=C.netGoldMin or repair) then
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
  economy.cityPopulation=city:GetPopulation()
  economy.hasSafeSite=#SettlementSites(player,state,nil)>0
  for row in GameInfo.Units() do
    local role=row.UnitType=="UNIT_BUILDER" and "builder" or (row.UnitType=="UNIT_SETTLER" and "settler"
      or (row.UnitType=="UNIT_TRADER" and "trader" or (Military(row) and "military" or nil)))
    if role then
      economy.maintenance=row.Maintenance or 0
      economy.resourceAffordable=q:CanProduce(row.Hash,false,true)==true
      if BaiqiPlanner.AllowRecruit(role,economy,C) then
        local priority=role=="settler" and 105 or (role=="builder" and 95 or (role=="trader" and 75 or 55))
        if role=="military" then priority=BaiqiPlanner.MilitaryScore(row,economy,C) end
        if priority then Add("unit",row,priority,false) end
      end
    end
  end
  for row in GameInfo.Projects() do
    Add("project",row,row.ProjectType=="PROJECT_BAIQI_STANDBY" and -1000 or 1,false)
  end
  local choice=BaiqiPlanner.Choose({paused=false,queueEmpty=true},candidates)
  if choice == nil then Reason("city:"..city:GetID(),"城市等待合法生产或预算"); return false end
  -- All state and legality are checked again at the write boundary.
  local freshCtx, freshPlayer, freshState=PlayerContext()
  if not BaiqiPolicy.Context(freshCtx) or not BaiqiPolicy.MatchesID(city,cityID) or city:GetOwner()~=freshCtx.player
    or not QueueReady(city,q,completedHead) then return false end
  local params=BuildParams(choice,completedHead)
  if q:CanProduce(choice.hash,true)~=true or q:CanProduce(choice.hash,false,true)~=true
    or CityManager.CanStartOperation(city,CityOperationTypes.BUILD,params,true)~=true then return false end
  local latest=PlayerContext()
  if not BaiqiPolicy.Context(latest) or latest.player~=freshCtx.player or not BaiqiPolicy.MatchesID(city,cityID)
    or city:GetOwner()~=latest.player or not QueueReady(city,q,completedHead) then return false end
  local id=NextRequest(CityRequestKey(city,choice))
  if id==nil then return false end
  pendingCities[city:GetID()]={id=id,hash=choice.hash,kind=choice.kind,elapsed=0,replacesHead=completedHead}
  Log("request","id="..id.."|source=BACKGROUND|city="..city:GetID().."|type="..choice.type..(completedHead and "|insert=replace_completed" or ""))
  CityManager.RequestOperation(city,CityOperationTypes.BUILD,params)
  return true
end

local function ReadBack(player)
  for unitID, pending in pairs(pendingUnits) do
    local unit=player:GetUnits():FindID(unitID)
    if not BaiqiPolicy.MatchesID(unit,unitID) then unit=nil end
    if pending.kind=="CREATE_GREAT_WORK" then
      if CreatedWorkObserved(player,pending) then
        Log("observed","id="..pending.id.."|unit="..unitID.."|kind=CREATE_GREAT_WORK|work="..pending.createdEvent.work.."|proof=native_event_and_owned_slot")
        pendingUnits[unitID]=nil
        if unit then unitEvaluated[UnitKey(unit)]=nil end
      elseif (pending.elapsed or 0)>=C.productionObservationSeconds and not pending.unresolvedLogged then
        Log("great_work_request_unresolved","id="..pending.id.."|unit="..unitID.."|awaiting_native_event_and_owned_slot=true")
        pending.unresolvedLogged=true
      end
    elseif pending.kind=="ACTIVATE_GREAT_PERSON" then
      local def=unit and GameInfo.Units[unit:GetUnitType()]
      local gp=unit and unit:GetOwner()==contextID and def and def.UnitType==pending.unitType and unit:GetGreatPerson()
      local individual=gp and GameInfo.GreatPersonIndividuals[gp:GetIndividual()]
      local class=gp and GameInfo.GreatPersonClasses[gp:GetClass()]
      if not individual or individual.Index~=pending.individual or not class or class.Index~=pending.class
        or individual.GreatPersonClassType~=BaiqiPolicy.DistrictGreatPersonClass(pending.unitType) then gp=nil end
      if pending.nativeActivated then
        Log("observed","id="..pending.id.."|unit="..unitID.."|kind=ACTIVATE_GREAT_PERSON|proof=native_activation_event")
        pendingUnits[unitID]=nil
      elseif not gp then
        -- Consumed units can disappear before UnitGreatPersonActivated arrives.
        -- Keep the exact request identity; absence alone proves no outcome.
        if not pending.unavailableLogged then
          Log("great_person_request_unavailable","id="..pending.id.."|unit="..unitID.."|awaiting_native_activation_event=true")
          pending.unavailableLogged=true
        end
      elseif gp:GetActionCharges()<pending.charges then
        Log("observed","id="..pending.id.."|unit="..unitID.."|kind=ACTIVATE_GREAT_PERSON|charges="..gp:GetActionCharges())
        pendingUnits[unitID]=nil
        unitEvaluated[UnitKey(unit)]=nil
      elseif (pending.elapsed or 0)>=C.interval*2 and unit:IsReadyToMove()
        and UI.IsGameCoreBusy and not UI.IsGameCoreBusy() and UI.IsProcessingMessages and not UI.IsProcessingMessages() then
        Log("unit_request_not_observed","id="..pending.id.."|unit="..unitID.."|reason=native_idle_unchanged_great_person_charges")
        pendingUnits[unitID]=nil
        unitEvaluated[UnitKey(unit)]=nil
      end
    elseif pending.kind=="MAKE_TRADE_ROUTE" then
      local origin=player:GetCities():FindID(pending.origin)
      if not BaiqiPolicy.MatchesID(origin,pending.origin) or origin:GetOwner()~=contextID then origin=nil end
      local observed=false
      for _,route in ipairs(origin and origin:GetTrade():GetOutgoingRoutes() or {}) do
        if route.TraderUnitID==unitID and route.DestinationCityPlayer==contextID
          and route.DestinationCityID==pending.destination then observed=true;break end
      end
      if observed then
        Log("observed","id="..pending.id.."|unit="..unitID.."|kind=MAKE_TRADE_ROUTE|destination="..pending.destination)
        pendingUnits[unitID]=nil
      elseif unit==nil or unit:GetOwner()~=contextID then
        Log("unit_request_not_observed","id="..pending.id.."|unit="..unitID.."|reason=trader_unavailable")
        pendingUnits[unitID]=nil
      elseif (pending.elapsed or 0)>=C.interval*2 and UnitManager.GetActivityType(unit)==ActivityTypes.ACTIVITY_AWAKE
        and UI.IsGameCoreBusy and not UI.IsGameCoreBusy() and UI.IsProcessingMessages and not UI.IsProcessingMessages() then
        Log("unit_request_not_observed","id="..pending.id.."|unit="..unitID.."|reason=native_idle_without_trade_route")
        pendingUnits[unitID]=nil
        unitEvaluated[UnitKey(unit)]=nil
      end
    elseif unit==nil or unit:GetOwner()~=contextID then
      Log("unit_request_not_observed","id="..pending.id.."|unit="..unitID.."|reason=unit_unavailable")
      pendingUnits[unitID]=nil
    elseif (UnitIndex(unit)~=nil and UnitIndex(unit)~=pending.from) or unit:GetMovesRemaining()~=pending.moves then
      Log("observed","id="..pending.id.."|unit="..unitID.."|kind="..pending.kind)
      pendingUnits[unitID]=nil
    elseif pending.kind=="MOVE_TO" and (pending.elapsed or 0)>=C.interval*2
      and UnitIndex(unit)==pending.from
      and unit.IsReadyToMove and unit:IsReadyToMove()
      and UnitManager.GetQueuedDestination and UnitManager.GetQueuedDestination(unit)==nil
      and UI.IsGameCoreBusy and not UI.IsGameCoreBusy()
      and UI.IsProcessingMessages and not UI.IsProcessingMessages() then
      Log("unit_request_not_observed","id="..pending.id.."|unit="..unitID.."|reason=native_idle_without_route")
      pendingUnits[unitID]=nil
      unitEvaluated[unitID..":"..pending.from..":"..tostring(pending.moves)]=nil
      -- Keep attempts: the same move is not repeated this turn. The normal
      -- civilian fallback may wait; a later turn replans from actual state.
    end
  end
  for cityID,pending in pairs(pendingCities) do
    local city=player:GetCities():FindID(cityID)
    if not BaiqiPolicy.MatchesID(city,cityID) or city:GetOwner()~=contextID then
      Log("queue_request_not_observed","id="..pending.id.."|city="..cityID.."|reason=city_unavailable")
      pendingCities[cityID]=nil
    else
      local q=city:GetBuildQueue()
      local hash=q:GetCurrentProductionTypeHash()
      local matched=hash==pending.hash
      for i=0,q:GetSize()-1 do
        local entry=q:GetAt(i)
        local row=entry and ((entry.UnitType and GameInfo.Units[entry.UnitType])
          or (entry.BuildingType and GameInfo.Buildings[entry.BuildingType])
          or (entry.DistrictType and GameInfo.Districts[entry.DistrictType])
          or (entry.ProjectType and GameInfo.Projects[entry.ProjectType]))
        if row and row.Hash==pending.hash then matched=true;break end
      end
      if matched then
        Log("queue_observed","id="..pending.id.."|city="..cityID.."|hash="..pending.hash)
        pendingCities[cityID]=nil
      elseif pending.replacesHead then
        -- A missing replacement is unknown. A late operation could overwrite
        -- alternate work, so retain the request and never infer failure.
        if (pending.elapsed or 0)>=C.productionObservationSeconds and CoreIdle() and not pending.unresolvedLogged then
          Log("queue_replacement_unresolved","id="..pending.id.."|city="..cityID.."|actual_hash="..hash)
          pending.unresolvedLogged=true
        end
      elseif hash~=0 then
        Log("queue_request_superseded","id="..pending.id.."|city="..cityID.."|actual_hash="..hash)
        pendingCities[cityID]=nil
      elseif q:GetSize()==0 and (pending.elapsed or 0)>=C.productionObservationSeconds
        and UI.IsGameCoreBusy and not UI.IsGameCoreBusy() and UI.IsProcessingMessages and not UI.IsProcessingMessages() then
        Log("queue_request_not_observed","id="..pending.id.."|city="..cityID.."|reason=native_idle_empty_queue")
        pendingCities[cityID]=nil
        cityEvaluated[cityID]=nil
        -- Attempts remain keyed by candidate. A different normal legal item may
        -- fill the empty queue this turn; this candidate is never replayed.
      end
    end
  end
end

local function Tick()
  if stopped then return end
  local ctx,player,state=PlayerContext()
  if ctx==nil then return end
  contextID=ctx.player
  if not BaiqiPolicy.Context(ctx) then return end
  visibility=PlayersVisibility[ctx.player]
  if visibility==nil then return end
  local current=Game.GetCurrentGameTurn()
  if current~=turn then
    turn=current; requestCount=0; attempts={}; reservations={}; lastReasons={}; cityEvaluated={}; unitEvaluated={}
    -- SKIP_TURN can leave movement points unchanged. Its intent expires with the
    -- turn; retaining that pending slot would strand the civilian indefinitely.
    for id,pending in pairs(pendingUnits) do
      if pending.kind=="SKIP_TURN" then pendingUnits[id]=nil end
    end
  end
  ReadBack(player)
  for _,city in player:GetCities():Members() do
    if ProcessCity(ctx,player,state,city) then status="已安排生产；军队等待你的命令"; return end
  end
  for _,unit in player:GetUnits():Members() do
    local snapshot=UnitSnapshot(unit,state)
    local unitKey=UnitKey(unit)
    if snapshot.plot~=nil and not unitEvaluated[unitKey] and pendingUnits[unit:GetID()]==nil and BaiqiPolicy.CanCivilian(ctx,snapshot) then
      unitEvaluated[unitKey]=true
      if snapshot.type=="UNIT_SETTLER" then
        if ProcessSettler(ctx,player,state,unit) then status="已提交移民操作，等待实际结果"; return end
      elseif snapshot.type=="UNIT_BUILDER" then
        if ProcessBuilder(ctx,player,state,unit) then status="已提交建造者操作，等待实际结果"; return end
      elseif snapshot.type=="UNIT_TRADER" then
        if ProcessTrader(ctx,player,state,unit) then status="已提交国内商路，等待实际结果";return end
      elseif BaiqiPolicy.DistrictGreatPersonClass(snapshot.type) then
        if ProcessDistrictPerson(ctx,player,state,unit) then status="已提交文职伟人内政任务，等待实际结果";return end
      elseif BaiqiPolicy.CreativeGreatPersonClass(snapshot.type) then
        if ProcessCreative(ctx,player,state,unit) then status="已提交自动创作，等待实际作品";return end
      end
      local here=UnitPlot(unit)
      if here and RequestCivilian(ctx,state,unit,"SKIP_TURN",here) then
        status="文职单位本回合等待安全任务；军队由你指挥";return
      end
    end
  end
end

function BaiqiController.RunNow()
  if running or stopped then return end
  running=true
  local ok,err=pcall(Tick)
  running=false
  if not ok then stopped=true; status="托管因脚本错误停止，请查看 Lua.log"; Log("error",tostring(err)) end
end

function BaiqiController.Update(delta)
  for _,pending in pairs(pendingUnits) do pending.elapsed=(pending.elapsed or 0)+delta end
  for _,pending in pairs(pendingCities) do pending.elapsed=(pending.elapsed or 0)+delta end
  elapsed=elapsed+delta
  if elapsed>=C.interval then elapsed=0; BaiqiController.RunNow() end
end

function BaiqiController.GetStatus() return status end

local function OnCityCompleted(playerID,cityID)
  if playerID==Game.GetLocalPlayer() then cityEvaluated[cityID]=nil end
end
Events.CityProductionCompleted.Add(OnCityCompleted)
local function OnGreatPersonActivated(playerID,unitID,classID,individualID)
  local ctx=PlayerContext()
  local pending=pendingUnits[unitID]
  local class=GameInfo.GreatPersonClasses and GameInfo.GreatPersonClasses[classID]
  local individual=GameInfo.GreatPersonIndividuals and GameInfo.GreatPersonIndividuals[individualID]
  if ctx and ctx.player==playerID and class and individual and pending and pending.kind=="ACTIVATE_GREAT_PERSON"
    and class.Index==pending.class and individual.Index==pending.individual
    and individual.GreatPersonClassType==BaiqiPolicy.DistrictGreatPersonClass(pending.unitType) then
    pending.nativeActivated=true
  end
end
if Events.UnitGreatPersonActivated then Events.UnitGreatPersonActivated.Add(OnGreatPersonActivated) end
local function OnGreatWorkCreated(playerID,creatorID,x,y,buildingID,workIndex)
  local ctx=PlayerContext()
  local pending=pendingUnits[creatorID]
  local building=BaiqiPolicy.Number(buildingID) and GameInfo.Buildings[buildingID]
  if ctx and ctx.player==playerID and pending and pending.kind=="CREATE_GREAT_WORK"
    and BaiqiPolicy.Number(x) and BaiqiPolicy.Number(y) and x>=0 and y>=0 and x%1==0 and y%1==0
    and BaiqiPolicy.Number(workIndex) and workIndex>=0 and workIndex%1==0
    and building then
    pending.createdEvent={x=x,y=y,building=building.Index,work=workIndex}
  end
end
if Events.GreatWorkCreated then Events.GreatWorkCreated.Add(OnGreatWorkCreated) end
function BaiqiController.Shutdown()
  stopped=true
  Events.CityProductionCompleted.Remove(OnCityCompleted)
  if Events.UnitGreatPersonActivated then Events.UnitGreatPersonActivated.Remove(OnGreatPersonActivated) end
  if Events.GreatWorkCreated then Events.GreatWorkCreated.Remove(OnGreatWorkCreated) end
end
print("BAIQI|ui_controller_loaded|version=2|mandatory_admin=true")
