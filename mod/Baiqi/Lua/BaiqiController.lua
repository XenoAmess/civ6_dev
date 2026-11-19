include("BaiqiConfig")
include("BaiqiPolicy")
include("BaiqiSettlementWarning")
include("BaiqiPlanner")
include("BaiqiHeritageCandidates")
include("BaiqiHeritageActions")
include("BaiqiNaturalistPurchase")
include("BaiqiMissionaryPurchase")
include("BaiqiMissionaryPurchaseDemand")
include("BaiqiMissionaryPurchaseSubmit")
include("BaiqiArchaeologyHome")
include("BaiqiPendingArtifact")
include("BaiqiSettlementJournal")
include("BaiqiFlood")

BaiqiController = {}
local C = BaiqiConfig
local elapsed, turn, requestCount, serial = 0, -1, 0, 0
local attempts, pendingUnits, pendingCities, reservations = {}, {}, {}, {}
local submittedUnits = {}
local cityEvaluated, unitEvaluated, settlementTargets = {}, {}, {}
local cityCursor=0
local planningStarted,builderResumeStreak=nil,0
local builderSearches={}
local builderRejectedGoals={}
local settlerSearches={}
local districtPersonPlans = {}
local districtRoute = {}
local missionaryPlans = {}
local missionaryPurchase={doneTurn=-1,streak=0}
local naturalistSearches = {}
local archaeologySearches = {}
local ArchaeologyHeld
local ProphetHeld
local pendingPurchase,purchaseSearch=nil,nil
local NaturalistPurchaseHeld
local purchaseDoneTurn,purchaseResumeStreak=-1,0
local stopped, running = false, false
local turnGuard
local status = "内政托管开启；军队等待你的命令"
local contextID, visibility
local lastReasons = {}
local settlementLoadKind
local settlementCache={ready=false,records={},plots={},unresolved=0}

local function Log(kind, details)
  print("BAIQI|"..kind.."|turn="..tostring(Game.GetCurrentGameTurn()).."|"..(details or ""))
end

local function Reason(key, text)
  status = text
  if lastReasons[key] ~= text then Log("wait", "key="..key.."|reason="..text); lastReasons[key] = text end
end

local function CoreIdle()
  if turnGuard then
    local ok,allowed=pcall(turnGuard)
    if not ok or allowed~=true then return false end
  end
  return type(UI.IsGameCoreBusy)=="function" and UI.IsGameCoreBusy()==false
    and type(UI.IsProcessingMessages)=="function" and UI.IsProcessingMessages()==false
end

-- The invisible executor supplies the native local-turn acknowledgement.
function BaiqiController.SetTurnGuard(guard)
  turnGuard=type(guard)=="function" and guard or function() return false end
end

function BaiqiController.SetSettlementLoadKind(value)
  if type(value)=="boolean" then settlementLoadKind=value end
end

local function PlayerContext()
  local id = Game.GetLocalPlayer()
  if id == nil or id < 0 or GameConfiguration.IsAnyMultiplayer()
    or (GameConfiguration.IsHotseat and GameConfiguration.IsHotseat()) then return nil end
  local player, config = Players[id], PlayerConfigurations[id]
  if player == nil or config == nil or config:GetLeaderTypeName() ~= C.leader or not config:IsHuman() then return nil end
  local active=player:IsTurnActive()==true and Game.IsAllowStrategicCommands~=nil
    and Game.IsAllowStrategicCommands(id)==true
  return {player=id, localPlayer=id, isBaiqi=true, activeTurn=active, enabled=true}, player, {}
end

function BaiqiController.IsAvailable()
  local ctx=PlayerContext()
  return ctx~=nil and ctx.activeTurn==true and CoreIdle()
end

-- Internal invalidation only: retain pending requests, attempts and turn budget.
function BaiqiController.RefreshProduction() cityEvaluated={} end

local function Revealed(plot)
  return plot ~= nil and visibility ~= nil and visibility:IsRevealed(plot:GetX(), plot:GetY()) == true
end

-- Default native plot queries omit the religious layer. Never query spy/trade
-- layers or hidden plots, and do not interpret unavailable layer data as empty.
local function GetVisibleUnits(plot)
  if not Revealed(plot) or not visibility:IsVisible(plot:GetX(),plot:GetY()) then return nil end
  if not Units or type(Units.GetUnitsInPlot)~="function"
    or type(Units.GetUnitsInPlotLayerID)~="function"
    or not MapLayers or type(MapLayers.RELIGIOUS)~="number" then return nil end
  local primary=Units.GetUnitsInPlot(plot)
  local religious=Units.GetUnitsInPlotLayerID(plot,MapLayers.RELIGIOUS)
  if type(primary)~="table" or type(religious)~="table" then return nil end
  local result={}
  for _,unit in pairs(primary) do result[#result+1]=unit end
  for _,unit in pairs(religious) do result[#result+1]=unit end
  return result,primary,religious
end

local function EmptyVisiblePlot(plot)
  local units=GetVisibleUnits(plot)
  return units~=nil and next(units)==nil
end

-- Immutable native topology only; no visibility, threats or native objects.
-- A changed binding invalidates every center, not just the first one revisited.
local neighborhoodCache,neighborhoodCount,settlementWorldEpoch={},0,0
local neighborhoodXY,neighborhoodByIndex
local function ClearNeighborhoods()
  neighborhoodCache,neighborhoodCount={},0
  settlementWorldEpoch=settlementWorldEpoch+1
  for _,plan in pairs(districtPersonPlans) do plan.route=nil end
  districtRoute.used=false
  -- A new world may reuse native bindings. Only a fresh live Commit ACK can
  -- create an unsent dispatch closure; never carry one through a load event.
  for _,pending in pairs(pendingUnits) do pending.dispatch=nil end
end
local function ForgetNeighborhood(key)
  if key and neighborhoodCache[key] then
    neighborhoodCache[key]=nil;neighborhoodCount=neighborhoodCount-1
  end
end
local function GeometryInteger(value)
  return BaiqiPolicy.Number(value) and value>=0 and value%1==0
end
local function NeighborhoodGeometry(plot,radius)
  local xy=Map and Map.GetPlotXYWithRangeCheck
  local byIndex=Map and Map.GetPlotByIndex
  if xy~=neighborhoodXY or byIndex~=neighborhoodByIndex then
    neighborhoodCache,neighborhoodCount={},0
    neighborhoodXY,neighborhoodByIndex=xy,byIndex
  end
  if type(xy)~="function" or type(byIndex)~="function" or not plot or not GeometryInteger(radius) then return nil end
  local ok,index,x,y=pcall(function() return plot:GetIndex(),plot:GetX(),plot:GetY() end)
  if not ok or not GeometryInteger(index) or not GeometryInteger(x) or not GeometryInteger(y) then return nil end
  local key=index..":"..x..":"..y..":"..radius
  if neighborhoodCache[key] then return neighborhoodCache[key],key end
  local valid,cells=pcall(function()
    local result,seen,anchor={},{},false
    for dx=-radius,radius do
      for dy=-radius,radius do
        local near=xy(x,y,dx,dy,radius)
        if near then
          local i,nx,ny=near:GetIndex(),near:GetX(),near:GetY()
          if not GeometryInteger(i) or not GeometryInteger(nx) or not GeometryInteger(ny) then return nil end
          if dx==0 and dy==0 then
            if i~=index or nx~=x or ny~=y then return nil end
            anchor=true
          end
          if seen[i] then
            if seen[i].x~=nx or seen[i].y~=ny then return nil end
          else
            local cell={index=i,x=nx,y=ny}
            result[#result+1]=cell;seen[i]=cell
          end
        elseif dx==0 and dy==0 then return nil end
      end
    end
    if anchor then return result end
  end)
  if not valid or not cells or Map.GetPlotXYWithRangeCheck~=xy or Map.GetPlotByIndex~=byIndex then return nil end
  -- Count string keys explicitly. Resetting at capacity changes cost, not facts.
  if neighborhoodCount>=256 then neighborhoodCache,neighborhoodCount={},0 end
  neighborhoodCache[key]=cells;neighborhoodCount=neighborhoodCount+1
  return cells,key
end

-- Safety reads only currently visible units. Only one path validation may share
-- known threat booleans. Topology is separate; ordinary/write checks stay fresh.
local function Safe(plot, player, cache)
  if not Revealed(plot) then return false end
  local geometry,key=NeighborhoodGeometry(plot,C.threatRadius)
  if not geometry then return false end
  for _,cell in ipairs(geometry) do
    if visibility:IsVisible(cell.x,cell.y) then
      local safe
      if type(cache)=="table" then safe=cache[cell.index] end
      if type(safe)~="boolean" then
        local ok,near=pcall(Map.GetPlotByIndex,cell.index)
        local matches=false
        if ok and near then
          ok,matches=pcall(function() return near:GetIndex()==cell.index and near:GetX()==cell.x and near:GetY()==cell.y end)
        end
        if not ok or not matches then ForgetNeighborhood(key);return false end
        local units=GetVisibleUnits(near)
        if units==nil then return false end
        safe=true
        for _,other in ipairs(units) do
          if other:GetOwner()~=contextID and player:GetDiplomacy():IsAtWarWith(other:GetOwner()) then safe=false;break end
        end
        if type(cache)=="table" then cache[cell.index]=safe end
      end
      if not safe then return false end
    end
  end
  return true
end

local function ResourceVisible(plot, player)
  local index = plot:GetResourceType()
  local row = index and GameInfo.Resources[index]
  return row ~= nil and player:GetResources():IsResourceVisible(row.Hash) == true
end

-- Gathering Storm builds ski resorts from an adjacent tile with a separate
-- operation. Keep its metadata and target checks outside ordinary local builds.
local function BuilderAdjacentDefinition()
  local ok,result=pcall(function()
    local row=GameInfo.Improvements.IMPROVEMENT_SKI_RESORT
    if type(row)~="table" or row.ImprovementType~="IMPROVEMENT_SKI_RESORT"
      or not GeometryInteger(row.Index) or not BaiqiPolicy.Number(row.Hash) or row.Hash%1~=0 then return nil end
    local op=UnitOperationTypes.BUILD_IMPROVEMENT_ADJACENT
    local x,y,t=UnitOperationTypes.PARAM_X,UnitOperationTypes.PARAM_Y,UnitOperationTypes.PARAM_IMPROVEMENT_TYPE
    if not BaiqiPolicy.Number(op) or op%1~=0 or x==nil or y==nil or t==nil
      or x==y or x==t or y==t then return nil end
    return {index=row.Index,hash=row.Hash,operation=op,xKey=x,yKey=y,typeKey=t}
  end)
  if ok then return result end
end

local function BuilderAdjacentTarget(ctx,player,unit,plot,hash,expected)
  local ok,result=pcall(function()
    local def=BuilderAdjacentDefinition()
    if not def or hash~=def.hash or not plot then return nil end
    if expected and (def.index~=expected.metadataIndex or def.hash~=expected.hash
      or def.operation~=expected.operation or def.xKey~=expected.xKey
      or def.yKey~=expected.yKey or def.typeKey~=expected.typeKey) then return nil end
    local index,x,y=plot:GetIndex(),plot:GetX(),plot:GetY()
    if not GeometryInteger(index) or not GeometryInteger(x) or not GeometryInteger(y) then return nil end
    if expected and (index~=expected.index or x~=expected.x or y~=expected.y) then return nil end
    local current=Map.GetPlotByIndex(index)
    if not current or current:GetIndex()~=index or current:GetX()~=x or current:GetY()~=y
      or current:GetOwner()~=ctx.player or current:GetImprovementType()~=-1 or current:GetDistrictType()~=-1
      or not Revealed(current) or visibility:IsVisible(x,y)~=true
      or Map.GetPlotDistance(unit:GetX(),unit:GetY(),x,y)~=1 or not Safe(current,player) then return nil end
    return {plot=current,index=index,x=x,y=y,hash=def.hash,metadataIndex=def.index,
      operation=def.operation,xKey=def.xKey,yKey=def.yKey,typeKey=def.typeKey}
  end)
  if ok then return result end
end

local function FeatureAllowedForDistrict(districtRow, featureIndex, city)
  -- Optional metadata and growth ports may throw; decline this placement only.
  local ok,allowed=pcall(function()
    if not BaiqiPolicy.Number(featureIndex) or featureIndex<0 or featureIndex%1~=0 then return false end
    if type(districtRow)~="table" and type(districtRow)~="userdata" then return false end
    if not BaiqiPolicy.Number(districtRow.Index) or districtRow.Index<0 or districtRow.Index%1~=0 then return false end
    if type(GameInfo.Features)~="table" and type(GameInfo.Features)~="userdata" then return false end
    local row=GameInfo.Features[featureIndex]
    if (type(row)~="table" and type(row)~="userdata") or row.Index~=featureIndex then return false end
    if districtRow.DistrictType=="DISTRICT_DAM" then
      local allowed={FEATURE_FLOODPLAINS=true,FEATURE_FLOODPLAINS_GRASSLAND=true,
        FEATURE_FLOODPLAINS_PLAINS=true}
      return type(row.FeatureType)=="string" and allowed[row.FeatureType]==true
    end
    if districtRow.DistrictType=="DISTRICT_NEIGHBORHOOD" and city then
      local ok, housing, population = pcall(function()
        return city:GetGrowth():GetHousing(), city:GetPopulation()
      end)
      if not ok then return false end
      return BaiqiPlanner.NeighborhoodFeatureAllowed(row.FeatureType, row.Removable, row.NaturalWonder, housing, population)
    end
    return false
  end)
  return ok and allowed==true
end

local function ClearPlot(plot, state, player, districtRow, city)
  if not (Revealed(plot) and not plot:IsCity()
    and not plot:IsNaturalWonder() and not plot:IsNationalPark()
    and plot:GetDistrictType() == -1 and not ResourceVisible(plot, player)) then return false end
  local feature=plot:GetFeatureType()
  if feature~=-1 and not FeatureAllowedForDistrict(districtRow,feature,city) then return false end
  local improvement=plot:GetImprovementType()
  if improvement == -1 then return true end
  if not BaiqiPolicy.Number(improvement) or improvement<0 or improvement%1~=0 then return false end
  if not GameInfo.Improvements then return false end
  local row=GameInfo.Improvements[improvement]
  -- A legal district may replace ordinary economic work. Military and unknown
  -- improvements remain protected; no manual reservation or removal is added.
  local ordinary={IMPROVEMENT_FARM=true,IMPROVEMENT_MINE=true,IMPROVEMENT_QUARRY=true,
    IMPROVEMENT_PLANTATION=true,IMPROVEMENT_PASTURE=true,IMPROVEMENT_CAMP=true,
    IMPROVEMENT_LUMBER_MILL=true}
  return row~=nil and ordinary[row.ImprovementType]==true
end

-- A new district consumes the tile's worked yield. Keep the native work
-- snapshot local to this evaluation and read it again before submitting.
local function DistrictFoodAllows(city, plot, snapshot)
  local ok, allowed = pcall(function()
    local kind=YieldTypes.FOOD
    if not GeometryInteger(kind) then return false end
    local food=plot:GetYield(kind)
    if not BaiqiPolicy.Number(food) or food<0 or food>1000000 then return false end
    if food==0 then return true end
    local index=plot:GetIndex()
    if not GeometryInteger(index) or index>2147483647 then return false end
    if not snapshot.read then
      snapshot.read=true
      local surplus=city:GetGrowth():GetFoodSurplus()
      if not BaiqiPolicy.Number(surplus) or math.abs(surplus)>1000000 then return false end
      local manage,key=CityCommandTypes.MANAGE,CityCommandTypes.PARAM_MANAGE_CITIZEN
      local plotsKey,citizensKey=CityCommandResults.PLOTS,CityCommandResults.CITIZENS
      if manage==nil or key==nil or plotsKey==nil or citizensKey==nil or plotsKey==citizensKey then return false end
      local param=UI.GetInterfaceModeParameter(key)
      if param~=nil and type(param)~="boolean" and type(param)~="string" and not BaiqiPolicy.Number(param) then return false end
      local args={};if param~=nil then args[key]=param end
      local result=CityManager.GetCommandTargets(city,manage,args)
      local plots,counts=result and result[plotsKey],result and result[citizensKey]
      if type(plots)~="table" or type(counts)~="table" then return false end
      local work,n={},0
      for slot,id in pairs(plots) do
        n=n+1;local count=counts[slot]
        if n>128 or not GeometryInteger(id) or id>2147483647 or work[id]~=nil
          or not BaiqiPolicy.Number(count) or count%1~=0 or count< -1 or count>256 then return false end
        work[id]=count
      end
      snapshot.work,snapshot.surplus=work,surplus
    end
    local count=snapshot.work and snapshot.work[index]
    -- An absent or unknown work row is different from an explicit zero.
    -- ClearPlot already excludes districts; their multi-worker counts cannot
    -- qualify a regular placement tile.
    return count==0 or (count==1 and snapshot.surplus>=food)
  end)
  return ok and allowed==true
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

-- Provisional route facts rank alternatives; they never authorize a command.
-- Call again for the chosen route and validate every plot at the write boundary.
local function TradeEndpoints(ctx,player,unit,plot)
  if UnitManager.GetActivityType(unit)~=ActivityTypes.ACTIVITY_AWAKE then return nil end
  local trade=player:GetTrade()
  local reserved=0
  for _,p in pairs(pendingUnits) do if p.kind=="MAKE_TRADE_ROUTE" then reserved=reserved+1 end end
  if trade:GetNumOutgoingRoutes()+reserved>=trade:GetOutgoingRouteCapacity() then return nil end
  local origin=Cities.GetCityInPlot(unit:GetX(),unit:GetY())
  local dest=plot and Cities.GetCityInPlot(plot:GetX(),plot:GetY())
  if not origin or not dest or origin:GetOwner()~=ctx.player or dest:GetOwner()~=ctx.player
    or origin:GetID()==dest:GetID() then return nil end
  return origin,dest
end

local function TradePath(ctx,player,unit,plot)
  local origin,dest=TradeEndpoints(ctx,player,unit,plot)
  if not origin then return nil end
  local path,entrances,exits=Game.GetTradeManager():GetTradeRoutePath(ctx.player,origin:GetID(),ctx.player,dest:GetID())
  if type(path)~="table" or next(path)==nil then return nil end
  local length=0
  for _ in pairs(path) do length=length+1 end
  return {origin=origin,dest=dest,path=path,entrances=entrances,exits=exits,length=length}
end

local function TradeParams(ctx,player,unit,plot)
  if not Revealed(plot) then return nil end
  local origin,dest=TradeEndpoints(ctx,player,unit,plot)
  if not origin then return nil end
  local originID,destID=origin:GetID(),dest:GetID()
  local params={[UnitOperationTypes.PARAM_X0]=dest:GetX(),[UnitOperationTypes.PARAM_Y0]=dest:GetY(),
    [UnitOperationTypes.PARAM_X1]=unit:GetX(),[UnitOperationTypes.PARAM_Y1]=unit:GetY()}
  if UnitManager.CanStartOperation(unit,UnitOperationTypes.MAKE_TRADE_ROUTE,nil,params)~=true then return nil end
  -- Re-read endpoints, idle/capacity and the actual native path after the last
  -- qualification query. Earlier provisional paths never authorize this write.
  local route=TradePath(ctx,player,unit,plot)
  if not route or route.origin:GetID()~=originID or route.dest:GetID()~=destID
    or route.dest:GetX()~=params[UnitOperationTypes.PARAM_X0] or route.dest:GetY()~=params[UnitOperationTypes.PARAM_Y0]
    or unit:GetX()~=params[UnitOperationTypes.PARAM_X1] or unit:GetY()~=params[UnitOperationTypes.PARAM_Y1] then return nil end
  local cache={}
  -- A native path may omit an endpoint; always validate the destination itself.
  if not Safe(plot,player,cache) then return nil end
  for _,index in pairs(route.path) do
    local p=Map.GetPlotByIndex(index)
    if not Safe(p,player,cache) or (p:GetOwner()~=-1 and p:GetOwner()~=ctx.player) then return nil end
  end
  for _,portals in pairs({route.entrances or {},route.exits or {}}) do
    for _,index in pairs(portals) do
      if index>=0 and not Safe(Map.GetPlotByIndex(index),player,cache) then return nil end
    end
  end
  return params,route.origin,route.dest,route.length
end

local function CivilianMoveTarget(here, plot, unit, playerID)
  if Map.GetPlotDistance(here:GetX(), here:GetY(), plot:GetX(), plot:GetY()) ~= 1 then return false, "not_adjacent" end
  if plot:GetOwner() ~= -1 and plot:GetOwner() ~= playerID then return false, "foreign_border" end
  if visibility:IsVisible(plot:GetX(),plot:GetY()) then
    local units,primary = GetVisibleUnits(plot)
    if units == nil then return false, "unit_query_unavailable" end
    local mover=GameInfo.Units[unit:GetUnitType()]
    -- A one-step primary civilian order must end on an available stack slot.
    -- Religious units live on a different map layer despite their formation
    -- metadata. Preserve the existing conservative naturalist checks below.
    if mover and mover.UnitType~="UNIT_MISSIONARY" and BaiqiPolicy.CivilianType(mover.UnitType) then
      for _,other in pairs(primary) do
        local row=GameInfo.Units[other:GetUnitType()]
        if not row then return false,"unit_query_unavailable"end
        if other:GetOwner()~=playerID then return false,"foreign_unit"end
        if other:GetOwner()==playerID and other:GetID()~=unit:GetID() and row
          and(row.FormationClass=="FORMATION_CLASS_CIVILIAN"
            or(row.FormationClass==nil and BaiqiPolicy.CivilianType(row.UnitType)))then
          return false,"civilian_target_occupied"
        end
      end
    end
    for _,other in ipairs(units) do
      local row=GameInfo.Units[other:GetUnitType()]
      if other:GetOwner()==playerID and other:GetID()~=unit:GetID()
        and mover and mover.UnitType=="UNIT_NATURALIST" and not row then
        return false,"unit_query_unavailable"
      end
      if other:GetOwner()==playerID and other:GetID()~=unit:GetID() and row
        and (row.UnitType=="UNIT_SETTLER" or row.UnitType=="UNIT_BUILDER"
          or (mover and mover.UnitType=="UNIT_NATURALIST" and row.FormationClass=="FORMATION_CLASS_CIVILIAN")) then
        return false,"civilian_target_occupied"
      end
    end
  end
  return true
end

-- Query only this recorded, currently visible site. Nil city lookup is useful
-- only alongside a typed native IsCity=false witness, never as a failed read.
local function FoundingSite(index,x,y)
  if not BaiqiPolicy.Number(index) or index<0 or index%1~=0 then return nil end
  local plot=Map.GetPlotByIndex(index)
  if not plot or plot:GetIndex()~=index or plot:GetX()~=x or plot:GetY()~=y
    or not Revealed(plot) or not visibility or type(visibility.IsVisible)~="function"
    or visibility:IsVisible(x,y)~=true or not CityManager
    or type(CityManager.GetCityAt)~="function" then return nil end
  local isCity=plot:IsCity()
  if type(isCity)~="boolean" then return nil end
  return plot,CityManager.GetCityAt(x,y),isCity
end

local function FoundCityObserved(player,pending,lookup)
  local w=pending.founding
  if not w or w.empty~=true or w.player~=contextID or w.unitType~="UNIT_SETTLER"
    or pending.kind~="FOUND_CITY" or pending.operation~=UnitOperationTypes.FOUND_CITY
    or pending.plot~=w.index or pending.from~=w.index or lookup~=nil then return nil end
  -- A full-ID alias is not absence. Also corroborate a nil lookup against the
  -- owned collection; missing/error metadata or an overlarge snapshot waits.
  local count=0
  for _,unit in player:GetUnits():Members() do
    count=count+1
    if count>512 then return nil end
    local id=unit:GetID()
    if not BaiqiPolicy.Number(id) or id<0 or id%1~=0 or id==w.unitID then return nil end
  end
  local plot,city,isCity=FoundingSite(w.index,w.x,w.y)
  if not plot or isCity~=true or not city or w.conflictingCity then return nil end
  if city:GetOwner()~=w.player then w.conflictingCity=true;return nil end
  local id=city:GetID()
  if not BaiqiPolicy.Number(id) or id<0 or id%1~=0 or id>2147483647
    or city:GetX()~=w.x or city:GetY()~=w.y or plot:GetOwner()~=w.player then return nil end
  local own=player:GetCities():FindID(id)
  if not BaiqiPolicy.MatchesID(own,id) or own:GetOwner()~=w.player
    or own:GetX()~=w.x or own:GetY()~=w.y then return nil end
  return id
end

local function SettlementBridge(method,...)
  local b=type(ExposedMembers)=="table" and ExposedMembers.BaiqiSettlementIntentBridge
  if type(b)~="table" or b.version~=1 or b.marker~="baiqi-settlement-intent-v1"
    or type(b[method])~="function" then return "UNAVAILABLE",nil,"bridge" end
  local ok,a,c,d=pcall(b[method],...)
  if ok then return a,c,d end
  return "UNAVAILABLE",nil,"bridge_error"
end

local function SettlerGoalBridge(method,...)
  local b=type(ExposedMembers)=="table"and ExposedMembers.BaiqiSettlerGoalsBridge
  if type(b)~="table"or getmetatable(b)~=nil or b.version~=1 or b.marker~="baiqi-settler-goals-v1"
    or type(b[method])~="function"then return "UNAVAILABLE",nil,"bridge" end
  local ok,s,g,why=pcall(b[method],...)
  if ok then return s,g,why end
  return "UNAVAILABLE",nil,"bridge_error"
end

local function SettlerGoalProposal(goal,id)
  if type(goal)~="table"or getmetatable(goal)~=nil or not BaiqiSettlementJournal.UnitKey(id)
    or goal.unitID~=id or goal.unitType~="UNIT_SETTLER"then return false end
  local allowed={unitID=true,unitType=true,plot=true,x=true,y=true};local n=0
  for k in pairs(goal)do n=n+1;if n>5 or not allowed[k]then return false end end
  if n~=5 then return false end
  for _,k in ipairs({"plot","x","y"})do
    if not BaiqiSettlementJournal.Integer(goal[k],2147483647)then return false end
  end
  local plot=Map.GetPlotByIndex(goal.plot)
  return plot~=nil and plot:GetIndex()==goal.plot and plot:GetX()==goal.x and plot:GetY()==goal.y and Revealed(plot)
end

local function SettlementRecord(op,playerID,unitID)
  local J=BaiqiSettlementJournal
  if type(J)~="table" or type(op)~="table" or getmetatable(op)~=nil or op.unitID~=unitID
    or J.UnitKey(unitID)==nil then return nil end
  local bank=J.New(playerID)
  if not bank then return nil end
  bank.serial=op.sequence;bank.operations[J.UnitKey(unitID)]=op
  local copy=J.Clone(bank,playerID)
  return copy and copy.operations[J.UnitKey(unitID)]
end

local function RefreshSettlement(playerID)
  local method=settlementCache.ready and "Snapshot" or "Initialize"
  local s,bank=SettlementBridge(method,playerID,settlementLoadKind)
  local J=BaiqiSettlementJournal
  if s~="READY" or type(J)~="table" or not J.Validate(bank,playerID) then
    settlementCache.ready=false;return
  end
  settlementCache.snapshot=J.Clone(bank,playerID)
  settlementCache.records=settlementCache.snapshot.operations;settlementCache.ready=true
  -- Restore intents even when the original actor is absent from the live list.
  -- A different pending operation is never overwritten by a restored record.
  local heldPlots,unresolved={},0
  for _,op in pairs(settlementCache.records) do
    if op.stage=="ARMED" or op.stage=="LEGACY_UNKNOWN" then unresolved=unresolved+1 end
    if op.stage=="ARMED" then heldPlots[op.plot]=true end
    if (op.stage=="ARMED" or op.stage=="LEGACY_UNKNOWN") and pendingUnits[op.unitID]==nil then
      pendingUnits[op.unitID]={id=op.requestID,kind="FOUND_CITY",operation=UnitOperationTypes.FOUND_CITY,
        plot=op.plot,from=op.plot,elapsed=0,persistent=true,token=op.token,restored=true}
      Log("settler_intent_restored","unit="..op.unitID.."|token="..op.token.."|stage="..op.stage)
    end
  end
  settlementCache.plots,settlementCache.unresolved=heldPlots,unresolved
end

local function SettlementHeld(unit)
  if not settlementCache.ready then return true end
  local key=BaiqiSettlementJournal.UnitKey(unit:GetID())
  local op=key and settlementCache.records[key]
  return op~=nil and op.stage~="PREPARED"
end

-- A retained actor still counts as live; this check never orders it.
-- One separate production slot can keep expansion moving; it is not a finding
-- that the old request failed. A second unresolved record closes the allowance.
function settlementCache.IsRetained(player,unit)
  local ok,held=pcall(function()
    if C.maxSettlers~=1 or settlementLoadKind~=true or not settlementCache.ready
      or settlementCache.unresolved~=1 or player~=Players[contextID] then return false end
    local J=BaiqiSettlementJournal
    local id=unit:GetID()
    if not J.Integer(id,2147483647) then return false end
    local key=J.UnitKey(id)
    local op=key and SettlementRecord(settlementCache.records[key],contextID,id)
    local current=Game.GetCurrentGameTurn()
    if not op or op.stage~="ARMED" or op.conflictingCity~=false
      or not J.Integer(current,2147483647) or op.turn>=current then return false end
    local pending=pendingUnits[id]
    if not pending or pending.kind~="FOUND_CITY" or pending.persistent~=true
      or pending.restored~=true or pending.token~=op.token
      or pending.id~=op.requestID or pending.plot~=op.plot then return false end
    local function Same(actor)
      if not BaiqiPolicy.MatchesID(actor,id) or actor:GetOwner()~=contextID then return false end
      local row=GameInfo.Units[actor:GetUnitType()]
      return row and row.UnitType=="UNIT_SETTLER" and actor:IsDead()==false
        and actor:IsDelayedDeath()==false and actor:GetDamage()==0
        and actor:GetFormationUnitCount()==1 and actor:GetMovesRemaining()>0
        and actor:GetX()==op.x and actor:GetY()==op.y
        and actor:HasPendingOperations()==false
        and type(UnitManager.GetQueuedDestination)=="function"
        and UnitManager.GetQueuedDestination(actor)==nil
    end
    if not Same(unit) or not Same(player:GetUnits():FindID(id)) then return false end
    -- Snapshot is read-only. A new/changed journal closes this proposal before
    -- production dispatch, even when the turn's cached counter still says one.
    local s,bank=SettlementBridge("Snapshot",contextID)
    if s~="READY" or not J.Equal(bank,settlementCache.snapshot,contextID) then return false end
    local unresolved=0
    for _,record in pairs(bank.operations) do
      if record.stage=="ARMED" or record.stage=="LEGACY_UNKNOWN" then
        unresolved=unresolved+1
        if unresolved>1 then return false end
      end
    end
    return unresolved==1
  end)
  return ok and held==true
end

-- A bounded known-border heuristic, not a native loyalty prediction. A lack of
-- currently visible foreign cities says nothing about cities hidden by fog.
local function ExpansionStable(player,playerID)
  local ok,stage,reason=pcall(function()
    if not GeometryInteger(playerID) or playerID>2147483647 or playerID~=contextID
      or not player then return "UNKNOWN","unknown_player" end
    local ruleset=GameConfiguration.GetValue("RULESET")
    if ruleset=="RULESET_STANDARD" then
      return BaiqiPolicy.ExpansionStability({loyaltyRules=false})
    end
    if ruleset~="RULESET_EXPANSION_1" and ruleset~="RULESET_EXPANSION_2" then return "UNKNOWN","unknown_ruleset" end
    local own=player:GetCities();local expected=own:GetCount()
    if not GeometryInteger(expected) or expected>128 then return "UNKNOWN","unknown_cities" end
    local snapshot={loyaltyRules=true,cities={}}
    for _,city in own:Members() do
      if #snapshot.cities>=128 or city:GetOwner()~=playerID then return "UNKNOWN","unknown_cities" end
      local id=city:GetID()
      if not GeometryInteger(id) or id>2147483647 then return "UNKNOWN","unknown_city" end
      local current=own:FindID(id)
      if not BaiqiPolicy.MatchesID(current,id) or current:GetOwner()~=playerID then return "UNKNOWN","unknown_city" end
      local identity=city:GetCulturalIdentity()
      snapshot.cities[#snapshot.cities+1]={id=id,loyalty=identity:GetLoyalty(),rate=identity:GetLoyaltyPerTurn()}
    end
    if #snapshot.cities~=expected or own:GetCount()~=expected or GameConfiguration.GetValue("RULESET")~=ruleset then
      return "UNKNOWN","cities_or_ruleset_changed"
    end
    return BaiqiPolicy.ExpansionStability(snapshot)
  end)
  if not ok then return nil,"loyalty_information_unavailable" end
  if stage=="CLEAR" then return true,reason end
  if stage=="HOLD" then return false,reason end
  return nil,reason
end
local function KnownExpansionSupport(plot,player,playerID)
  local ok,result,reason=pcall(function()
    local function Integer(n)return GeometryInteger(n) and n<=2147483647 end
    if not Integer(playerID) or playerID~=contextID or not plot or not Revealed(plot) then return nil,"unknown_site" end
    local index,x,y=plot:GetIndex(),plot:GetX(),plot:GetY()
    if not Integer(index) or not Integer(x) or not Integer(y) then return nil,"unknown_site" end
    local own=player:GetCities();local expected=own:GetCount()
    if not Integer(expected) or expected>128 then return nil,"unknown_cities" end
    local count,nearest,owned=0,nil,{}
    for _,city in own:Members() do
      count=count+1;if count>128 then return nil,"unknown_cities" end
      local id,cx,cy=city:GetID(),city:GetX(),city:GetY()
      if not Integer(id) or owned[id] or city:GetOwner()~=playerID
        or not Integer(cx) or not Integer(cy) then return nil,"unknown_cities" end
      local current=own:FindID(id)
      if not BaiqiPolicy.MatchesID(current,id) or current:GetOwner()~=playerID
        or current:GetX()~=cx or current:GetY()~=cy then return nil,"unknown_cities" end
      local distance=Map.GetPlotDistance(x,y,cx,cy)
      if not Integer(distance) then return nil,"unknown_distance" end
      if distance<=3 then return false,"city_too_close" end
      if not nearest or distance<nearest then nearest=distance end
      owned[id]={x=cx,y=cy}
    end
    if count~=expected or own:GetCount()~=expected then return nil,"unknown_cities" end
    if expected==0 then return true,"first_city" end
    if not nearest then return nil,"unknown_cities" end
    local warningModule=BaiqiSettlementWarning
    if type(warningModule)~="table" or type(warningModule.Read)~="function" then
      return nil,"loyalty_warning_unavailable"
    end
    local warningStage=warningModule.Read(
      {GameConfiguration=GameConfiguration,Map=Map,PlayersVisibility=PlayersVisibility},playerID,index)
    if warningStage=="KNOWN_NEGATIVE" then return false,"native_negative_loyalty_warning" end
    local stable,why=ExpansionStable(player,playerID)
    if stable~=true then return stable,why end
    local radius=nearest<=9 and nearest or 9
    if radius<1 or radius>9 or radius%1~=0 then return nil,"unknown_geometry" end
    local maxCells=1+3*radius*(radius+1)
    local cells=NeighborhoodGeometry(plot,radius)
    if not cells or #cells>maxCells then return nil,"unknown_geometry" end
    local seen={}
    for _,cell in ipairs(cells) do
      local revealed=visibility:IsRevealed(cell.x,cell.y)
      if type(revealed)~="boolean" then return nil,"unknown_visibility" end
      local visible=false
      if revealed then
        visible=visibility:IsVisible(cell.x,cell.y)
        if type(visible)~="boolean" then return nil,"unknown_visibility" end
      end
      if revealed and visible then
        -- Topology is scalar cached geometry. Resolve live plots only for the
        -- currently public cells whose city information this check consumes.
        local near=Map.GetPlotByIndex(cell.index)
        if not near or near:GetIndex()~=cell.index or near:GetX()~=cell.x or near:GetY()~=cell.y then return nil,"unknown_geometry" end
        local flag=near:IsCity()
        if type(flag)~="boolean" then return nil,"unknown_city" end
        if flag then
          local city=CityManager.GetCityAt(cell.x,cell.y)
          if not city then return nil,"unknown_city" end
          local id,owner=city:GetID(),city:GetOwner()
          if not Integer(id) or not Integer(owner) or owner~=near:GetOwner()
            or city:GetX()~=cell.x or city:GetY()~=cell.y then return nil,"unknown_city" end
          local key=owner..":"..id
          if seen[key] and seen[key]~=cell.index then return nil,"unknown_city" end
          seen[key]=cell.index
          local distance=Map.GetPlotDistance(x,y,cell.x,cell.y)
          if not Integer(distance) or distance>radius then return nil,"unknown_geometry" end
          if distance<=3 then return false,"city_too_close" end
          if owner==playerID then
            local c=owned[id]
            if not c or c.x~=cell.x or c.y~=cell.y then return nil,"unknown_cities" end
          elseif nearest<=9 and distance<=nearest then
            return false,"foreign_city_within_nearest_owned"
          elseif nearest>9 then return false,"foreign_border_without_owned_support" end
        end
      end
    end
    return true,"known_border_checked"
  end)
  if not ok then return nil,"native_information_unavailable" end
  return result,reason
end

-- Preserve native settler and builder queues, including after a UI reload.
-- A missing getter or unknown return shape never authorizes a replacement order.
local function SettlerQueueIdle(unit,unitType)
  if unitType~="UNIT_SETTLER" and unitType~="UNIT_BUILDER" then return true end
  local f=UnitManager and UnitManager.GetQueuedDestination
  if type(f)~="function"then return false end
  local function Empty(ok,...)
    return ok and select("#",...)<=1 and (...)==nil
  end
  return Empty(pcall(f,unit))
end

local function RequestCivilian(ctx, state, unit, operation, plot, improvement, prewrite)
  -- Re-read ownership and active player at the write boundary. No takeover flags.
  local freshCtx, freshPlayer, freshState = PlayerContext()
  ctx, state = freshCtx, freshState
  if ctx == nil or not CoreIdle() then return false, "context_changed_or_core_busy" end
  if prewrite~=nil and(operation~="MOVE_TO"or type(prewrite)~="function")then return false,"invalid_move_guard"end
  local here=UnitPlot(unit)
  if not here then return false,"position_unavailable" end
  local allowed, reason = BaiqiPolicy.CanCivilian(ctx, UnitSnapshot(unit, state))
  local def = GameInfo.Units[unit:GetUnitType()]
  if not allowed or not BaiqiPolicy.ActionAllowed(def.UnitType, operation) then return false, reason end
  local unitID,unitType=unit:GetID(),def.UnitType
  if unitType=="UNIT_SETTLER" and SettlementHeld(unit) then return false,"settlement_receipt_pending" end
  if not SettlerQueueIdle(unit,unitType)then return false,"native_queue_pending_or_unknown" end
  if unitType=="UNIT_NATURALIST" and operation=="MOVE_TO" and NaturalistPurchaseHeld() then return false,"purchase_receipt_pending" end
  if unitType=="UNIT_MISSIONARY" and missionaryPurchase.Held() then return false,"purchase_receipt_pending" end
  if unitType=="UNIT_ARCHAEOLOGIST" and operation=="MOVE_TO" and ArchaeologyHeld(unit) then return false,"archaeology_receipt_pending" end
  if unitType=="UNIT_GREAT_PROPHET" and operation=="MOVE_TO" and ProphetHeld(unit) then return false,"prophet_receipt_pending" end
  if operation=="MOVE_TO" or operation=="MAKE_TRADE_ROUTE" then
    -- Full safety follows qualification for these operations. Preserve the
    -- cheap explored-target gate before any native qualification query.
    if not Revealed(plot) then return false,"unsafe" end
  elseif operation~="SKIP_TURN" and not Safe(plot, Players[ctx.player]) then return false, "unsafe" end
  local params,origin,dest = {}
  local adjacent
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
    local legal,why=CivilianMoveTarget(here,plot,unit,ctx.player)
    if not legal then return false,why end
    params[UnitOperationTypes.PARAM_X], params[UnitOperationTypes.PARAM_Y] = plot:GetX(), plot:GetY()
  elseif operation=="BUILD_IMPROVEMENT_ADJACENT" then
    adjacent=BuilderAdjacentTarget(ctx,freshPlayer,unit,plot,improvement)
    if unitType~="UNIT_BUILDER" or not adjacent
      or type(UnitManager.CanStartOperation)~="function" or type(UnitManager.RequestOperation)~="function" then
      return false,"adjacent_improvement_unavailable"
    end
    adjacent.qualifier,adjacent.writer=UnitManager.CanStartOperation,UnitManager.RequestOperation
    params[adjacent.xKey],params[adjacent.yKey],params[adjacent.typeKey]=adjacent.x,adjacent.y,adjacent.hash
  else
    if plot:GetIndex() ~= here:GetIndex() then return false, "not_current_plot" end
    if operation == "BUILD_IMPROVEMENT" then
      if improvement == nil or plot:GetOwner() ~= ctx.player then return false, "invalid_improvement" end
      params[UnitOperationTypes.PARAM_X], params[UnitOperationTypes.PARAM_Y] = here:GetX(), here:GetY()
      params[UnitOperationTypes.PARAM_IMPROVEMENT_TYPE] = improvement
    elseif operation == "REPAIR" and plot:GetOwner() ~= ctx.player then return false, "foreign_repair" end
  end
  -- TradeParams already qualified and then freshly validated this exact route.
  if operation~="MAKE_TRADE_ROUTE" then
    local can
    if adjacent then
      local ok,result=pcall(UnitManager.CanStartOperation,unit,action,nil,params)
      can=ok and result==true
    else can=UnitManager.CanStartOperation(unit,action,nil,params) end
    if can~=true then return false,"engine_rejected" end
  end
  local latest=PlayerContext()
  local actual=GameInfo.Units[unit:GetUnitType()]
  if not latest or not CoreIdle() or latest.player~=ctx.player or not BaiqiPolicy.MatchesID(unit,unitID)
    or not actual or actual.UnitType~=unitType or not BaiqiPolicy.CanCivilian(latest,UnitSnapshot(unit,{})) then
    return false,"unit_or_context_changed"
  end
  if UnitIndex(unit)~=here:GetIndex() then return false,"position_changed" end
  if adjacent then
    local fresh=Players[latest.player]:GetUnits():FindID(unitID)
    if not fresh or not BaiqiPolicy.MatchesID(fresh,unitID)
      or not BaiqiPolicy.CanCivilian(latest,UnitSnapshot(fresh,{})) or UnitIndex(fresh)~=here:GetIndex()
      or UnitManager.CanStartOperation~=adjacent.qualifier or UnitManager.RequestOperation~=adjacent.writer
      or UnitOperationTypes[operation]~=adjacent.operation
      or not BuilderAdjacentTarget(latest,Players[latest.player],fresh,plot,improvement,adjacent) then
      return false,"adjacent_improvement_changed"
    end
    unit=fresh
  end
  if operation=="MOVE_TO" then
    -- Qualification is a native boundary: re-read target facts after it rather
    -- than letting either path memoization or an earlier legal target authorize
    -- a now hidden, hostile, foreign, or newly occupied destination.
    if not Safe(plot,Players[latest.player]) then return false,"unsafe_after_qualification" end
    local legal,why=CivilianMoveTarget(here,plot,unit,latest.player)
    if not legal then return false,why end
    if unitType=="UNIT_SETTLER" and ExpansionStable(Players[latest.player],latest.player)~=true then
      return false,"owned_city_stability_unavailable"
    end
  end
  if unitType=="UNIT_NATURALIST" and operation=="MOVE_TO" and NaturalistPurchaseHeld() then return false,"purchase_receipt_pending" end
  if unitType=="UNIT_MISSIONARY" and missionaryPurchase.Held() then return false,"purchase_receipt_pending" end
  if unitType=="UNIT_ARCHAEOLOGIST" and operation=="MOVE_TO" and ArchaeologyHeld(unit) then return false,"archaeology_receipt_pending" end
  if unitType=="UNIT_GREAT_PROPHET" and operation=="MOVE_TO" and ProphetHeld(unit) then return false,"prophet_receipt_pending" end
  if prewrite~=nil then
    local ok,current=pcall(prewrite)
    if not ok or current~=true then return false,"movement_proposal_changed"end
  end
  local founding
  if operation=="FOUND_CITY" then
    if KnownExpansionSupport(plot,Players[latest.player],latest.player)~=true then return false,"settlement_support_unavailable" end
    -- Native qualification above may run callbacks. Acquire the empty-site
    -- witness afterwards, adjacent to the existing final request boundary.
    local ok,site,city,isCity=pcall(FoundingSite,here:GetIndex(),here:GetX(),here:GetY())
    if not ok or not site or city~=nil or isCity~=false or unitType~="UNIT_SETTLER"
      or (site:GetOwner()~=-1 and site:GetOwner()~=latest.player)
      or not Safe(site,Players[latest.player]) then return false,"founding_site_unavailable" end
    local final,finalPlayer,finalState=PlayerContext()
    local fresh=finalPlayer and finalPlayer:GetUnits():FindID(unitID)
    local row=fresh and GameInfo.Units[fresh:GetUnitType()]
    if not final or not CoreIdle() or final.player~=latest.player
      or not BaiqiPolicy.MatchesID(fresh,unitID) or not row or row.UnitType~=unitType
      or not BaiqiPolicy.CanCivilian(final,UnitSnapshot(fresh,finalState))
      or UnitIndex(fresh)~=site:GetIndex() then return false,"unit_or_context_changed" end
    unit=fresh
    founding={unitID=unitID,unitType=unitType,player=latest.player,index=site:GetIndex(),
      x=site:GetX(),y=site:GetY(),empty=true}
  end
  if not SettlerQueueIdle(unit,unitType)then return false,"native_queue_pending_or_unknown" end
  local key = "unit:"..unit:GetID()..":"..here:GetIndex()..":"..operation..":"..plot:GetIndex()..":"..tostring(improvement)
  local id = NextRequest(key)
  if id == nil or pendingUnits[unit:GetID()] ~= nil then return false, "already_pending_or_budget" end
  local settlementToken,foundingNative
  if founding then
    foundingNative={manager=UnitManager,writer=UnitManager.RequestOperation,
      qualifier=UnitManager.CanStartOperation,bridge=ExposedMembers.BaiqiSettlementIntentBridge,
      epoch=settlementWorldEpoch}
    if type(foundingNative.writer)~="function" then return false,"native_writer_unavailable" end
    local stage,op=SettlementBridge("Prepare",ctx.player,unitID,founding.index,founding.x,founding.y,id)
    op=SettlementRecord(op,ctx.player,unitID)
    if stage~="PREPARED" or not op or op.stage~=stage or op.requestID~=id
      or op.plot~=founding.index or op.x~=founding.x or op.y~=founding.y then return false,"settlement_prepare_unavailable" end
    local granted,token=SettlementBridge("Commit",ctx.player,unitID,op.token,id)
    if granted~=true or token~=op.token then return false,"settlement_commit_unconfirmed" end
    settlementToken=token
  end
  pendingUnits[unitID] = {id=id, operation=action, plot=plot:GetIndex(), from=here:GetIndex(), kind=operation, moves=unit:GetMovesRemaining(),elapsed=0}
  if founding then
    local pending=pendingUnits[unitID]
    pending.founding=founding;pending.persistent=true;pending.token=settlementToken
    local armedTurn,entered,checking,dispatch=turn,false,false,nil
    -- This closure exists only after this call's successful fresh Commit ACK.
    -- It is not serialized, restored from ARMED, or usable in another turn.
    local function Bound()
      return pendingUnits[unitID]==pending and pending.dispatch==dispatch and not entered
        and turn==armedTurn and settlementWorldEpoch==foundingNative.epoch
        and UnitOperationTypes.FOUND_CITY==action and next(params)==nil
        and UnitManager==foundingNative.manager
        and UnitManager.RequestOperation==foundingNative.writer
        and UnitManager.CanStartOperation==foundingNative.qualifier
        and type(ExposedMembers)=="table" and ExposedMembers.BaiqiSettlementIntentBridge==foundingNative.bridge
    end
    local function FinalFoundUnit()
      local c,p,s=PlayerContext()
      if not Bound() or not c or c.player~=ctx.player or armedTurn~=Game.GetCurrentGameTurn()
        or not CoreIdle() then return nil end
      local u=p:GetUnits():FindID(unitID);local row=u and GameInfo.Units[u:GetUnitType()]
      if not BaiqiPolicy.MatchesID(u,unitID) or not row or row.UnitType~="UNIT_SETTLER"
        or not BaiqiPolicy.CanCivilian(c,UnitSnapshot(u,s)) or UnitIndex(u)~=founding.index then return nil end
      return u,p
    end
    local function Qualify()
      if not FinalFoundUnit() then return nil,"armed_final_unit_changed" end
      local stage,bank=SettlementBridge("Snapshot",ctx.player)
      local J=BaiqiSettlementJournal
      local current=stage=="READY" and J.Validate(bank,ctx.player)
        and SettlementRecord(bank.operations[J.UnitKey(unitID)],ctx.player,unitID)
      if not current or current.stage~="ARMED" or current.token~=settlementToken
        or current.requestID~=id or current.turn~=armedTurn or current.plot~=founding.index
        or current.x~=founding.x or current.y~=founding.y or current.empty~=true
        or current.conflictingCity~=false then return nil,"armed_live_intent_changed" end
      local fresh,p=FinalFoundUnit()
      if not fresh or foundingNative.qualifier(fresh,action,nil,params)~=true then return nil,"armed_final_native_unavailable" end
      fresh,p=FinalFoundUnit()
      local ok,site,city,isCity=pcall(FoundingSite,founding.index,founding.x,founding.y)
      if not fresh or not ok or not site or city~=nil or isCity~=false
        or (site:GetOwner()~=-1 and site:GetOwner()~=ctx.player)
        or not Safe(site,p) or KnownExpansionSupport(site,p,ctx.player)~=true then return nil,"armed_final_site_unavailable" end
      fresh=FinalFoundUnit()
      if not fresh or not SettlerQueueIdle(fresh,unitType) then return nil,"native_queue_pending_or_unknown" end
      fresh=FinalFoundUnit()
      if not fresh then return nil,"armed_final_unit_changed" end
      return fresh
    end
    dispatch=function()
      if entered or checking or not Bound() then return false,"armed_live_dispatch_held" end
      checking=true
      local ok,fresh,why=pcall(Qualify)
      checking=false
      if not ok or not fresh or not Bound() then return false,why or "armed_live_qualification_unavailable" end
      -- Consume before entering the writer. False, void and throw are all
      -- unresolved native outcomes, never permission for another dispatch.
      entered=true;pending.dispatch=nil
      Log("request", "id="..id.."|source=BACKGROUND|unit="..unitID.."|operation=FOUND_CITY|plot="..founding.index.."|from="..founding.index)
      local called=pcall(foundingNative.writer,fresh,action,params)
      if not called then Log("settler_request_unresolved","id="..id.."|unit="..unitID.."|native_call_error=true|token="..settlementToken) end
      return true,"submitted"
    end
    pending.dispatch=dispatch
    return dispatch()
  end
  if origin then pendingUnits[unit:GetID()].origin=origin:GetID();pendingUnits[unit:GetID()].destination=dest:GetID() end
  if not SettlerQueueIdle(unit,unitType)then
    -- No native call has occurred here. Only retire this function's unsent,
    -- nonpersistent proposal. FOUND uses its separate live-ACK dispatch path.
    local pending=pendingUnits[unitID]
    if not founding and pending and pending.id==id and pending.persistent~=true then pendingUnits[unitID]=nil end
    return false,"native_queue_pending_or_unknown"
  end
  Log("request", "id="..id.."|source=BACKGROUND|unit="..unit:GetID().."|operation="..operation.."|plot="..plot:GetIndex().."|from="..here:GetIndex())
  UnitManager.RequestOperation(unit, action, params)
  return true, "submitted"
end

-- Waiting does not replay an ability or replace its persistent receipt. The
-- native HOLD activity prevents an entrusted idle unit blocking the next turn.
local function RequestCivilianStandby(unit)
  if not unit or type(unit.GetID)~="function" then return false end
  local unitID=unit:GetID()
  if not BaiqiPolicy.Number(unitID) or unitID<0 or unitID%1~=0 or unitID>2147483647 then return false end
  local pending=pendingUnits[unitID]
  if pending and type(pending.dispatch)=="function" then return false end
  local def=GameInfo.Units[unit:GetUnitType()]
  local unitType=def and def.UnitType
  if not BaiqiPolicy.CivilianType(unitType) then return false end
  local row=GameInfo.UnitOperations and GameInfo.UnitOperations.UNITOPERATION_SKIP_TURN
  local operation=row and row.Hash
  if not BaiqiPolicy.Number(operation) or operation%1~=0 then return false end
  local function Eligible()
    local ctx,player,state=PlayerContext()
    if not ctx or not BaiqiPolicy.Context(ctx) or not CoreIdle()
      or turn~=Game.GetCurrentGameTurn() then return nil end
    local fresh=player:GetUnits():FindID(unitID)
    local actual=fresh and GameInfo.Units[fresh:GetUnitType()]
    if not BaiqiPolicy.MatchesID(fresh,unitID) or fresh:GetOwner()~=ctx.player
      or not actual or actual.UnitType~=unitType
      or not BaiqiPolicy.CanCivilian(ctx,UnitSnapshot(fresh,state))
      or type(fresh.IsReadyToSelect)~="function" or fresh:IsReadyToSelect()~=true
      or type(fresh.IsReadyToMove)~="function" or fresh:IsReadyToMove()~=true
      or type(UnitManager.GetActivityType)~="function" or not ActivityTypes
      or ActivityTypes.ACTIVITY_AWAKE==nil
      or UnitManager.GetActivityType(fresh)~=ActivityTypes.ACTIVITY_AWAKE then return nil end
    if not SettlerQueueIdle(fresh,unitType)then return nil end
    return fresh
  end
  -- Legacy creator receipts remain unknown, even when the native charge counter
  -- is zero (that value also occurs before normal creation). Sleep is waiting,
  -- never proof that an old creation failed or permission to replay it.
  local function LegacyCreativeSleep(unit,unitType,eligible)
    if not BaiqiPolicy.CreativeGreatPersonClass(unitType) then return false,false end
    local manager=UnitManager
    local can,writer,queue,activity=manager.CanStartOperation,manager.RequestOperation,
      manager.GetQueuedDestination,manager.GetActivityType
    local bridge=type(ExposedMembers)=="table" and ExposedMembers.BaiqiCreativeIntentBridge
    local inspect=type(bridge)=="table" and bridge.Inspect
    local row=GameInfo.UnitOperations and GameInfo.UnitOperations.UNITOPERATION_SLEEP
    local operation=row and row.Hash
    if type(can)~="function" or type(writer)~="function" or type(queue)~="function"
      or type(activity)~="function" or not BaiqiPolicy.Number(operation) or operation%1~=0
      or type(inspect)~="function" or bridge.version~=1 or bridge.marker~="baiqi-creative-intent-v1" then return false,false end
    local id,at,playerID=unit:GetID(),turn,contextID
    local function Read(current)
      local ok,value=pcall(function()
        local stage,token=inspect(playerID,id)
        if stage~="LEGACY_UNKNOWN" or type(token)~="string" or token=="" then return nil end
        local gp=type(current.GetGreatPerson)=="function" and current:GetGreatPerson()
        if not gp or type(gp.GetActionCharges)~="function" or gp:GetActionCharges()~=0 then return nil end
        local individual=GameInfo.GreatPersonIndividuals[gp:GetIndividual()]
        local class=GameInfo.GreatPersonClasses[gp:GetClass()]
        local expected=BaiqiPolicy.CreativeGreatPersonClass(unitType)
        local index=UnitIndex(current)
        if not individual or not class or individual.GreatPersonClassType~=expected
          or class.GreatPersonClassType~=expected or not index
          or not BaiqiPolicy.Number(individual.Index) or individual.Index<0 or individual.Index%1~=0
          or not BaiqiPolicy.Number(class.Index) or class.Index<0 or class.Index%1~=0 then return nil end
        return {token=token,individual=individual.Index,class=class.Index,plot=index}
      end)
      return ok and value or nil
    end
    local expected=Read(unit)
    if not expected then return false,false end
    local function Bound()
      return UnitManager==manager and manager.CanStartOperation==can and manager.RequestOperation==writer
        and manager.GetQueuedDestination==queue and manager.GetActivityType==activity
        and type(ExposedMembers)=="table" and ExposedMembers.BaiqiCreativeIntentBridge==bridge
        and bridge.Inspect==inspect and bridge.version==1 and bridge.marker=="baiqi-creative-intent-v1"
        and GameInfo.UnitOperations.UNITOPERATION_SLEEP==row and row.Hash==operation
    end
    local function Empty(ok,...)return ok and select("#",...)<=1 and (...)==nil end
    local function False(ok,...)return ok and select("#",...)==1 and (...)==false end
    local function Idle(current)
      if type(current.HasPendingOperations)~="function" then return false end
      return False(pcall(current.HasPendingOperations,current)) and Empty(pcall(queue,current))
    end
    local function Current()
      if not Bound() or turn~=at or contextID~=playerID or pendingUnits[id]~=nil or pendingPurchase~=nil then return nil end
      local current=eligible()
      local value=current and Read(current)
      if not value or value.token~=expected.token or value.individual~=expected.individual
        or value.class~=expected.class or value.plot~=expected.plot or not Idle(current) then return nil end
      local latest=eligible()
      if not latest or UnitIndex(latest)~=expected.plot or not Idle(latest) or not Bound() or not CoreIdle() then return nil end
      return latest
    end
    local fresh=Current()
    if not fresh then return true,false end
    local legal=can(fresh,operation,nil,{})
    fresh=Current()
    if not fresh then return true,false end
    -- Native rejection keeps the original SKIP path available. Its eligibility
    -- and native permission are queried anew after this helper returns.
    if legal~=true then return false,false end
    if can(fresh,operation,nil,{})~=true then return true,false end
    fresh=Current()
    if not fresh then return true,false end
    local request=NextRequest("standby:"..id..":"..turn)
    if not request then return true,false end
    Log("request","id="..request.."|source=BACKGROUND|unit="..id.."|operation=SLEEP|reason=legacy_creative_standby")
    local ok,err=pcall(writer,fresh,operation,{})
    if not ok then Log("standby_unknown","id="..request.."|unit="..id.."|reason="..tostring(err)) end
    return true,true
  end

  local fresh=Eligible()
  if not fresh then return false end
  if BaiqiPolicy.CreativeGreatPersonClass(unitType) then
    local handled,sent=LegacyCreativeSleep(fresh,unitType,Eligible)
    if handled then return sent end
    fresh=Eligible()
    if not fresh then return false end
  end
  local canSkip=UnitManager.CanStartOperation(fresh,operation,nil,{})
  local operationName="SKIP_TURN"
  if canSkip==true then
    fresh=Eligible()
    if not fresh then return false end
  elseif canSkip==false and unitType=="UNIT_NATURALIST" then
    -- Naturalists can have no park site while native SKIP is unavailable.
    -- Sleep only an idle, uncommitted naturalist; never replace a park,
    -- purchase receipt or a queued operation with a waiting order.
    local sleepRow=GameInfo.UnitOperations.UNITOPERATION_SLEEP
    local sleep=sleepRow and sleepRow.Hash
    local can,writer=UnitManager.CanStartOperation,UnitManager.RequestOperation
    local queued=UnitManager.GetQueuedDestination
    local bridge=type(ExposedMembers)=="table" and ExposedMembers.BaiqiNaturalistIntentBridge
    local inspect=type(bridge)=="table" and bridge.Inspect
    local purchase=type(ExposedMembers)=="table" and ExposedMembers.BaiqiNaturalistPurchaseBridge
    local inspectPurchase=type(purchase)=="table" and purchase.Inspect
    local at,playerID=turn,contextID
    if not BaiqiPolicy.Number(sleep) or sleep%1~=0
      or type(can)~="function" or type(writer)~="function" or type(queued)~="function"
      or type(inspect)~="function" or type(inspectPurchase)~="function" then return false end
    local function Empty(ok,...)
      return ok and select("#",...)<=1 and (...)==nil
    end
    local function NativeIdle(current)
      if type(current.HasPendingOperations)~="function" then return false end
      local ok,pending=pcall(current.HasPendingOperations,current)
      return ok and pending==false and Empty(pcall(queued,current))
    end
    local function SleepEligible()
      local current=Eligible()
      if not current or turn~=at or contextID~=playerID or pendingUnits[unitID]~=nil
        or pendingPurchase~=nil
        or type(ExposedMembers)~="table" or ExposedMembers.BaiqiNaturalistIntentBridge~=bridge
        or bridge.version~=1 or bridge.marker~="baiqi-naturalist-intent-v1" or bridge.Inspect~=inspect
        or ExposedMembers.BaiqiNaturalistPurchaseBridge~=purchase
        or purchase.version~=1 or purchase.marker~="baiqi-naturalist-purchase-v1" or purchase.Inspect~=inspectPurchase
        or UnitManager.CanStartOperation~=can or UnitManager.RequestOperation~=writer
        or UnitManager.GetQueuedDestination~=queued
        or GameInfo.UnitOperations.UNITOPERATION_SLEEP~=sleepRow or sleepRow.Hash~=sleep
        or not NativeIdle(current) then return nil end
      local ok,stage=pcall(inspect,playerID,unitID)
      local purchaseOK,purchaseStage=pcall(inspectPurchase,playerID)
      if not ok or (stage~="OPEN" and stage~="OBSERVED") or not purchaseOK or purchaseStage~="OPEN"
        or not NativeIdle(current) then return nil end
      -- The protected receipt read is not a permission to survive a changed
      -- native context. Keep the final identity/readiness check fresh too.
      if not CoreIdle() or UnitManager.CanStartOperation~=can or UnitManager.RequestOperation~=writer
        or UnitManager.GetQueuedDestination~=queued then return nil end
      local latest=Eligible()
      if not latest or not NativeIdle(latest)
        or pendingUnits[unitID]~=nil or pendingPurchase~=nil
        or ExposedMembers.BaiqiNaturalistIntentBridge~=bridge or bridge.Inspect~=inspect
        or ExposedMembers.BaiqiNaturalistPurchaseBridge~=purchase or purchase.Inspect~=inspectPurchase
        or GameInfo.UnitOperations.UNITOPERATION_SLEEP~=sleepRow or sleepRow.Hash~=sleep
        or not CoreIdle() then return nil end
      return latest
    end
    fresh=SleepEligible()
    if not fresh or can(fresh,sleep,nil,{})~=true then return false end
    fresh=SleepEligible()
    if not fresh or can(fresh,sleep,nil,{})~=true then return false end
    fresh=SleepEligible()
    if not fresh then return false end
    operation,operationName=sleep,"SLEEP"
  else
    return false
  end
  local id=NextRequest("standby:"..unitID..":"..turn)
  if not id then return false end
  Log("request","id="..id.."|source=BACKGROUND|unit="..unitID.."|operation="..operationName.."|reason=entrusted_standby")
  local ok,err=pcall(UnitManager.RequestOperation,fresh,operation,{})
  if not ok then Log("standby_unknown","id="..id.."|unit="..unitID.."|reason="..tostring(err)) end
  return true
end

-- A native route can ignore a friendly civilian's end-of-step stack slot.
-- Keep the same destination: propose at most six visible adjacent alternatives
-- that strictly approach it and adjoin the validated route beyond its blocker.
-- Only the proposed first edge receives native authority; every later hop is
-- planned again. No detour object or cached path authorizes a future command.
local function SettlerOccupiedDetour(unit, target, player, here, path, blockedAt)
  local ctx=PlayerContext()
  local row=unit and GameInfo.Units[unit:GetUnitType()]
  if not ctx or not row or row.UnitType~="UNIT_SETTLER"
    or not BaiqiPolicy.CanCivilian(ctx,UnitSnapshot(unit,{})) then return nil end
  local id,kind,start=unit:GetID(),unit:GetUnitType(),here:GetIndex()
  local goal=target:GetIndex()
  local stamp,epoch=Game.GetCurrentGameTurn(),settlementWorldEpoch
  local distance=Map.GetPlotDistance(here:GetX(),here:GetY(),target:GetX(),target:GetY())
  if not BaiqiPolicy.Number(distance) or distance<=0 then return nil end
  local geometry=NeighborhoodGeometry(here,1)
  if not geometry or #geometry>7 then return nil end
  local function Fresh()
    local latest,p,s=PlayerContext()
    local fresh=p and p:GetUnits():FindID(id)
    return latest and latest.player==ctx.player and CoreIdle()
      and Game.GetCurrentGameTurn()==stamp and settlementWorldEpoch==epoch
      and BaiqiPolicy.MatchesID(fresh,id) and fresh:GetOwner()==ctx.player
      and fresh:GetUnitType()==kind and UnitIndex(fresh)==start
      and BaiqiPolicy.CanCivilian(latest,UnitSnapshot(fresh,s))
  end
  local function Available(plot)
    if not plot or not Revealed(plot) or visibility:IsVisible(plot:GetX(),plot:GetY())~=true
      or (plot:GetOwner()~=-1 and plot:GetOwner()~=ctx.player)
      or not Safe(plot,player) then return false end
    local _,primary=GetVisibleUnits(plot)
    if type(primary)~="table" then return false end
    local n=0
    for _,other in pairs(primary) do
      n=n+1
      if n>64 or not GameInfo.Units[other:GetUnitType()] then return false end
    end
    return CivilianMoveTarget(here,plot,unit,ctx.player)==true
  end
  local choices={}
  for _,cell in ipairs(blockedAt==2 and geometry or {}) do
    local plot=Map.GetPlotByIndex(cell.index)
    if cell.index~=start and plot and plot:GetIndex()==cell.index
      and Map.GetPlotDistance(here:GetX(),here:GetY(),plot:GetX(),plot:GetY())==1
      and Map.GetPlotDistance(plot:GetX(),plot:GetY(),target:GetX(),target:GetY())<distance
      and Available(plot) then
      local join
      for i=3,#path do
        local suffix=Map.GetPlotByIndex(path[i])
        if suffix and Revealed(suffix)
          and Map.GetPlotDistance(plot:GetX(),plot:GetY(),suffix:GetX(),suffix:GetY())<=1 then join=i end
      end
      if join then choices[#choices+1]={index=cell.index,join=join} end
    end
  end
  table.sort(choices,function(a,b)
    if a.join~=b.join then return a.join>b.join end
    return a.index<b.index
  end)
  for _,choice in ipairs(choices) do
    if not Fresh() then return nil end
    local plot=Map.GetPlotByIndex(choice.index)
    if Available(plot) then
      local ok,edge=pcall(UnitManager.GetMoveToPathEx,unit,choice.index)
      if ok and type(edge)=="table" and type(edge.plots)=="table" and #edge.plots==2
        and edge.plots[1]==start and edge.plots[2]==choice.index and Fresh() then
        local params={[UnitOperationTypes.PARAM_X]=plot:GetX(),[UnitOperationTypes.PARAM_Y]=plot:GetY()}
        local qualified,allowed=pcall(UnitManager.CanStartOperation,unit,UnitOperationTypes.MOVE_TO,nil,params)
        if qualified and allowed==true and Fresh() and Available(plot) then
          local cache,valid={},true
          for _,index in ipairs(path) do
            local point=Map.GetPlotByIndex(index)
            if not point or not Revealed(point) or not Safe(point,player,cache)
              or (point:GetOwner()~=-1 and point:GetOwner()~=ctx.player) then valid=false;break end
          end
          if valid and Fresh() then return plot end
        end
      end
    end
  end
  -- A choke point may require first walking away from the destination. Search
  -- only the native route plus a radius-three neighborhood of that blocker.
  -- Anchoring at the blocker keeps the same corridor available after the first
  -- observed step, even when the next native route initially doubles back.
  local anchor=blockedAt and Map.GetPlotByIndex(path[blockedAt])
  local nearby=anchor and NeighborhoodGeometry(anchor,3)
  if not nearby or #nearby>37 or #path>C.pathLimit then return nil end
  local nodes,count={},0
  local function Add(index,x,y)
    local plot=Map.GetPlotByIndex(index)
    if not plot or plot:GetIndex()~=index or(x~=nil and(plot:GetX()~=x or plot:GetY()~=y))then return false end
    if not nodes[index]then
      count=count+1;if count>85 then return false end
      nodes[index]={index=index,x=plot:GetX(),y=plot:GetY()}
    end
    return true
  end
  for _,index in ipairs(path)do if not Add(index)then return nil end end
  for _,cell in ipairs(nearby)do if not Add(cell.index,cell.x,cell.y)then return nil end end
  local function Open(index,cache)
    local cell=nodes[index];local plot=cell and Map.GetPlotByIndex(index)
    if not plot or plot:GetIndex()~=index or plot:GetX()~=cell.x or plot:GetY()~=cell.y
      or not Revealed(plot)or visibility:IsVisible(cell.x,cell.y)~=true
      or(plot:GetOwner()~=-1 and plot:GetOwner()~=ctx.player)or plot:IsImpassable()
      or not Safe(plot,player,cache)then return false end
    local _,primary=GetVisibleUnits(plot)
    if type(primary)~="table"then return false end
    local n=0
    for _,other in pairs(primary)do
      n=n+1;local def=GameInfo.Units[other:GetUnitType()]
      if n>64 or not def then return false end
      if other:GetOwner()==ctx.player and other:GetID()~=id
        and(def.FormationClass=="FORMATION_CLASS_CIVILIAN"or def.UnitType=="UNIT_BUILDER"or def.UnitType=="UNIT_SETTLER")then return false end
    end
    return true
  end
  local pathQuery,qualify=UnitManager.GetMoveToPathEx,UnitManager.CanStartOperation
  local operation,xKey,yKey=UnitOperationTypes.MOVE_TO,UnitOperationTypes.PARAM_X,UnitOperationTypes.PARAM_Y
  local function NativeEdge(index)
    if not Fresh()or UnitManager.GetMoveToPathEx~=pathQuery or UnitManager.CanStartOperation~=qualify
      or UnitOperationTypes.MOVE_TO~=operation or UnitOperationTypes.PARAM_X~=xKey or UnitOperationTypes.PARAM_Y~=yKey then return false end
    local plot=Map.GetPlotByIndex(index)
    if not plot or Map.GetPlotDistance(here:GetX(),here:GetY(),plot:GetX(),plot:GetY())~=1 then return false end
    local ok,edge=pcall(pathQuery,unit,index)
    if not ok or type(edge)~="table"or type(edge.plots)~="table"or #edge.plots~=2
      or edge.plots[1]~=start or edge.plots[2]~=index or not Fresh()then return false end
    local params={[xKey]=plot:GetX(),[yKey]=plot:GetY()}
    local qualified,allowed=pcall(qualify,unit,operation,nil,params)
    return qualified and allowed==true and Fresh()
      and UnitManager.GetMoveToPathEx==pathQuery and UnitManager.CanStartOperation==qualify
      and UnitOperationTypes.MOVE_TO==operation and UnitOperationTypes.PARAM_X==xKey and UnitOperationTypes.PARAM_Y==yKey
  end
  local open,cache={},{}
  for index in pairs(nodes)do open[index]=Open(index,cache)end
  if not open[start]or not open[goal]or not Fresh()then return nil end
  local queue,visited,previous={start},{[start]=true},{}
  local head=1
  while head<=#queue and not visited[goal]do
    local index=queue[head];head=head+1
    local cell=nodes[index];local neighbors={}
    local geometry=NeighborhoodGeometry(Map.GetPlotByIndex(index),1)
    if not geometry or #geometry>7 then return nil end
    for _,nextCell in ipairs(geometry)do
      local nextIndex=nextCell.index
      if open[nextIndex]and not visited[nextIndex]
        and Map.GetPlotDistance(cell.x,cell.y,nextCell.x,nextCell.y)==1 then neighbors[#neighbors+1]=nextIndex end
    end
    table.sort(neighbors)
    for _,nextIndex in ipairs(neighbors)do
      if index~=start or NativeEdge(nextIndex)then
        visited[nextIndex]=true;previous[nextIndex]=index;queue[#queue+1]=nextIndex
        if #queue>85 then return nil end
      else
        -- A rejected native first edge is no certificate for a later geometric
        -- hop to the same node. Exclude that proposal for this fresh search.
        open[nextIndex]=false
      end
    end
  end
  if not visited[goal]then return nil end
  local route,index={},goal
  while index do
    table.insert(route,1,index);if #route>85 then return nil end
    index=previous[index]
  end
  if #route<2 or #route>C.pathLimit or #route>#path+6 or route[1]~=start then return nil end
  local first=nodes[route[2]]
  if Map.GetPlotDistance(first.x,first.y,target:GetX(),target:GetY())>distance+1 then return nil end
  local function Valid()
    if not Fresh()then return false end
    local cache={}
    for i,index in ipairs(route)do
      if not Open(index,cache)then return false end
      local a,b=nodes[route[i-1]],nodes[index]
      if a and Map.GetPlotDistance(a.x,a.y,b.x,b.y)~=1 then return false end
    end
    -- Preserve the existing native-route threat and ownership checks too.
    for _,index in ipairs(path)do
      local plot=Map.GetPlotByIndex(index)
      if not plot or not Revealed(plot)or not Safe(plot,player,cache)
        or(plot:GetOwner()~=-1 and plot:GetOwner()~=ctx.player)then return false end
    end
    return Fresh()
  end
  if Valid()and NativeEdge(first.index)and Valid()and NativeEdge(first.index)and Valid()then
    return Map.GetPlotByIndex(first.index)
  end
  return nil
end

local function PathStep(unit, target, player, state)
  if not Revealed(target) or not Safe(target, player) then return nil end
  local start=UnitIndex(unit)
  if start==nil then return nil end
  local path = UnitManager.GetMoveToPathEx(unit, target:GetIndex())
  if type(path) ~= "table" or type(path.plots) ~= "table" or #path.plots < 2 or #path.plots > C.pathLimit then return nil end
  if path.plots[1] ~= start or path.plots[#path.plots] ~= target:GetIndex() or UnitIndex(unit)~=start then return nil end
  local cache={}
  for _, index in ipairs(path.plots) do
    local p = Map.GetPlotByIndex(index)
    if p == nil or not Revealed(p) or not Safe(p, player, cache)
      or (p:GetOwner() ~= -1 and p:GetOwner() ~= contextID) then return nil end
  end
  local step=Map.GetPlotByIndex(path.plots[2])
  local here=UnitPlot(unit)
  if not step or not here then return nil end
  local row=GameInfo.Units[unit:GetUnitType()]
  if row and (row.UnitType=="UNIT_BUILDER" or row.UnitType=="UNIT_SETTLER") then
    local legal,reason=CivilianMoveTarget(here,step,unit,contextID)
    if not legal then
      if row.UnitType=="UNIT_SETTLER" and reason=="civilian_target_occupied" then
        return SettlerOccupiedDetour(unit,target,player,here,path.plots,2)
      end
      return nil
    end
    if row.UnitType=="UNIT_SETTLER"then
      -- Look only a few native points ahead. Otherwise a fresh native path can
      -- send the settler back to a free tile immediately before the same choke.
      for i=3,math.min(#path.plots,4)do
        local plot=Map.GetPlotByIndex(path.plots[i])
        if plot and visibility:IsVisible(plot:GetX(),plot:GetY())==true then
          local _,primary=GetVisibleUnits(plot)
          if type(primary)~="table"then return nil end
          local n=0
          for _,other in pairs(primary)do
            n=n+1;local def=GameInfo.Units[other:GetUnitType()]
            if n>64 or not def then return nil end
            if other:GetOwner()==contextID and other:GetID()~=unit:GetID()
              and(def.FormationClass=="FORMATION_CLASS_CIVILIAN"or def.UnitType=="UNIT_BUILDER"or def.UnitType=="UNIT_SETTLER")then
              return SettlerOccupiedDetour(unit,target,player,here,path.plots,i)
            end
          end
        end
      end
    end
  end
  return step
end

-- A newly recruited civilian can share its spawn tile with an idle civilian,
-- making native SKIP illegal. Move only that unescorted civilian out of the
-- overlap, after its normal task and wait have both failed. Never roam alone.
local function ClearCivilianOverlap(ctx,player,state,unit,prewrite)
  local here=UnitPlot(unit)
  local def=GameInfo.Units[unit:GetUnitType()]
  if not def or not BaiqiPolicy.ActionAllowed(def.UnitType,"MOVE_TO") or not here
    or here:GetOwner()~=ctx.player or not visibility:IsVisible(here:GetX(),here:GetY())
    or not Safe(here,player) then return false end
  local overlap=false
  local units = GetVisibleUnits(here)
  if units == nil then return false end
  for _,other in ipairs(units) do
    local row=GameInfo.Units[other:GetUnitType()]
    if other:GetID()~=unit:GetID() and other:GetOwner()==ctx.player and row
      and (BaiqiPolicy.CivilianType(row.UnitType) or row.FormationClass=="FORMATION_CLASS_CIVILIAN") then overlap=true;break end
  end
  if not overlap then return false end
  local function FreeSlot(plot)
    local _,primary,religious=GetVisibleUnits(plot)
    if type(primary)~="table"or type(religious)~="table"or next(religious)~=nil then return false end
    local n=0
    for _,other in pairs(primary)do
      n=n+1
      if n>64 or not GameInfo.Units[other:GetUnitType()]or other:GetOwner()~=ctx.player then return false end
    end
    return CivilianMoveTarget(here,plot,unit,ctx.player)==true
  end
  local candidates={}
  for direction=0,5 do
    local plot=Map.GetAdjacentPlot(here:GetX(),here:GetY(),direction)
    if plot and plot:GetOwner()==ctx.player and not plot:IsWater() and not plot:IsImpassable()
      and visibility:IsVisible(plot:GetX(),plot:GetY()) and Safe(plot,player)
      and FreeSlot(plot) then
      local reserved=false
      for _,pending in pairs(pendingUnits) do
        if pending.kind=="MOVE_TO" and pending.plot==plot:GetIndex() then reserved=true;break end
      end
      if not reserved then
        candidates[#candidates+1]=plot
      end
    end
  end
  table.sort(candidates,function(a,b) return a:GetIndex()<b:GetIndex() end)
  for _,plot in ipairs(candidates) do
    local step=PathStep(unit,plot,player,state)
    if step and step:GetIndex()==plot:GetIndex() then
      local index,x,y=plot:GetIndex(),plot:GetX(),plot:GetY()
      local guard=prewrite and function()return prewrite(plot,index,x,y)==true end or nil
      if RequestCivilian(ctx,state,unit,"MOVE_TO",plot,nil,guard) then return true end
    end
  end
  return false
end

-- Only an otherwise idle builder may yield a visible choke on a nonheld
-- settler's existing native route. This does not move or order that settler.
function settlementCache.YieldBuilder(ctx,player,state,unit)
  local def=unit and GameInfo.Units[unit:GetUnitType()]
  if not def or def.UnitType~="UNIT_BUILDER"then return false end
  local id,kind,start,key=unit:GetID(),unit:GetUnitType(),UnitIndex(unit),UnitKey(unit)
  if not start or not BaiqiSettlementJournal.UnitKey(id)then return false end
  local stamp,epoch=Game.GetCurrentGameTurn(),settlementWorldEpoch
  local manager,vis=UnitManager,visibility
  local bindings={path=manager.GetMoveToPathEx,queue=manager.GetQueuedDestination,
    activity=manager.GetActivityType,can=manager.CanStartOperation,writer=manager.RequestOperation,
    plot=Map.GetPlot,byIndex=Map.GetPlotByIndex,primary=Units.GetUnitsInPlot,religious=Units.GetUnitsInPlotLayerID,
    goals=ExposedMembers.BaiqiSettlerGoalsBridge,intents=ExposedMembers.BaiqiSettlementIntentBridge,
    operation=UnitOperationTypes.MOVE_TO}
  local goalRead=type(bindings.goals)=="table"and bindings.goals.Read
  local snapshot=type(bindings.intents)=="table"and bindings.intents.Snapshot
  if type(bindings.path)~="function"or type(bindings.can)~="function"or type(bindings.writer)~="function"
    or type(bindings.queue)~="function"or type(bindings.activity)~="function"
    or type(goalRead)~="function"or type(snapshot)~="function"then return false end
  local function Bound()
    return UnitManager==manager and manager.GetMoveToPathEx==bindings.path
      and manager.GetQueuedDestination==bindings.queue and manager.GetActivityType==bindings.activity
      and manager.CanStartOperation==bindings.can and manager.RequestOperation==bindings.writer
      and Map.GetPlot==bindings.plot and Map.GetPlotByIndex==bindings.byIndex
      and Units.GetUnitsInPlot==bindings.primary and Units.GetUnitsInPlotLayerID==bindings.religious
      and ExposedMembers.BaiqiSettlerGoalsBridge==bindings.goals and bindings.goals.Read==goalRead
      and ExposedMembers.BaiqiSettlementIntentBridge==bindings.intents and bindings.intents.Snapshot==snapshot
      and visibility==vis and PlayersVisibility[ctx.player]==vis and UnitOperationTypes.MOVE_TO==bindings.operation
  end
  local function Empty(...)return select("#",...)<=1 and select(1,...)==nil end
  local function False(...)return select("#",...)==1 and select(1,...)==false end
  local function Idle(u)
    return type(u.HasPendingOperations)=="function"and False(u:HasPendingOperations())
      and type(bindings.queue)=="function"and Empty(bindings.queue(u))
  end
  local function Fresh()
    local ok,u,why=pcall(function()
      local c,p,s=PlayerContext();local u=p and p:GetUnits():FindID(id)
      if not c or c.player~=ctx.player or not CoreIdle()or Game.GetCurrentGameTurn()~=stamp
        or settlementWorldEpoch~=epoch or not Bound()or pendingUnits[id]~=nil
        or not BaiqiPolicy.MatchesID(u,id)or u:GetOwner()~=ctx.player or u:GetUnitType()~=kind
        or UnitIndex(u)~=start or u:GetFormationUnitCount()~=1
        or u:IsDead()~=false or u:IsDelayedDeath()~=false or not Idle(u)then return nil,"hold"end
      if u:GetMovesRemaining()<=0 or type(u.IsReadyToMove)~="function"or u:IsReadyToMove()~=true
        or type(bindings.activity)~="function"or bindings.activity(u)~=ActivityTypes.ACTIVITY_AWAKE
        or not BaiqiPolicy.CanCivilian(c,UnitSnapshot(u,s))then return nil,"done"end
      local here=UnitPlot(u)
      if not here or here:GetOwner()~=ctx.player or not Revealed(here)
        or vis:IsVisible(here:GetX(),here:GetY())~=true or not Safe(here,p)then return nil,"done"end
      return u
    end)
    return ok and u or nil,ok and why or "hold"
  end
  local function Hold()
    unitEvaluated[key]="native_wait"
    local ok,k=pcall(function()
      local p=Players[ctx.player];local u=p and p:GetUnits():FindID(id)
      if BaiqiPolicy.MatchesID(u,id)and u:GetOwner()==ctx.player and u:GetUnitType()==kind then return UnitKey(u)end
    end)
    if ok and k then unitEvaluated[k]="native_wait"end
    Reason("builder_yield:"..id,"建造者等待通行资格重新确认；其他内政继续执行")
    return false
  end
  local fresh,why=Fresh()
  if not fresh then if why=="hold"then return Hold()end;return false end
  local pathQueries=0
  local function Claim(selected)
    local ok,result=pcall(function()
      if not Bound()or not Fresh()then return nil end
      local status,bank=SettlementBridge("Snapshot",ctx.player)
      local J=BaiqiSettlementJournal
      if status~="READY"or not J.Validate(bank,ctx.player)then return nil end
      local candidates,count={},0
      for _,s in player:GetUnits():Members()do
        count=count+1;if count>256 then return nil end
        local row=GameInfo.Units[s:GetUnitType()];if not row then return nil end
        if row.UnitType=="UNIT_SETTLER"and(selected==nil or s:GetID()==selected)then candidates[#candidates+1]=s:GetID()end
      end
      table.sort(candidates)
      for _,sid in ipairs(candidates)do
        local s=player:GetUnits():FindID(sid);local cell=UnitPlot(s)
        if BaiqiPolicy.MatchesID(s,sid)and s:GetOwner()==ctx.player and s:GetFormationUnitCount()==1
          and s:IsDead()==false and s:IsDelayedDeath()==false and Idle(s)and cell
          and pendingUnits[sid]==nil and not SettlementHeld(s)and bank.operations[J.UnitKey(sid)]==nil then
          local gs,goal=SettlerGoalBridge("Read",ctx.player,sid)
          if gs=="READY"and SettlerGoalProposal(goal,sid)then
            -- Two initial proposals, with one reserved query for the selected
            -- settler's fresh native path at the actual write boundary.
            pathQueries=pathQueries+1;if pathQueries>(selected and 3 or 2)then return nil end
            local route=bindings.path(s,goal.plot);local points=route and route.plots
            if type(points)=="table"and #points>=2 and #points<=C.pathLimit
              and points[1]==cell:GetIndex()and points[#points]==goal.plot then
              local seen,cache,valid,blocked,previous={},{},true,false,nil
              local entries=0;for k in pairs(points)do entries=entries+1;if entries>C.pathLimit or not GeometryInteger(k)or k<1 or k>#points then valid=false;break end end
              if entries~=#points then valid=false end
              for i,index in ipairs(points)do
                local p=Map.GetPlotByIndex(index)
                if not GeometryInteger(index)or seen[index]or not p or p:GetIndex()~=index
                  or not Revealed(p)or(p:GetOwner()~=-1 and p:GetOwner()~=ctx.player)
                  or not Safe(p,player,cache)or(previous and Map.GetPlotDistance(previous:GetX(),previous:GetY(),p:GetX(),p:GetY())~=1)then valid=false;break end
                seen[index]=true;previous=p
                if i>=2 and i<=4 and index==start and vis:IsVisible(p:GetX(),p:GetY())==true then blocked=true end
              end
              if valid and blocked then return{settler=sid,from=cell:GetIndex(),goal=goal,plots=seen,bank=bank}end
            end
          end
        end
      end
    end)
    return ok and result or nil
  end
  local claim=Claim();if not claim then return false end
  local function Parking(plot,current)
    local here=UnitPlot(fresh);local index=plot and plot:GetIndex()
    if not here or not plot or current.plots[index]or reservations[index]~=nil
      or plot:GetOwner()~=ctx.player or plot:IsWater()or plot:IsImpassable()or not Revealed(plot)
      or vis:IsVisible(plot:GetX(),plot:GetY())~=true or not Safe(plot,player)
      or Map.GetPlotDistance(here:GetX(),here:GetY(),plot:GetX(),plot:GetY())~=1 then return false end
    for _,op in pairs(current.bank.operations)do if op.stage=="ARMED"and op.plot==index then return false end end
    local count=0;for _,pending in pairs(pendingUnits)do count=count+1;if count>256 then return false end;if pending.kind=="MOVE_TO"and pending.plot==index then return false end end
    local _,primary,religious=GetVisibleUnits(plot)
    if type(primary)~="table"or type(religious)~="table"or next(religious)~=nil then return false end
    count=0;for _,other in pairs(primary)do count=count+1;if count>64 or not GameInfo.Units[other:GetUnitType()]or other:GetOwner()~=ctx.player then return false end end
    return CivilianMoveTarget(here,plot,fresh,ctx.player)==true
  end
  local function Edge(plot)
    local route=bindings.path(fresh,plot:GetIndex());local points=route and route.plots
    if type(points)~="table"or #points~=2 or points[1]~=start or points[2]~=plot:GetIndex()then return false end
    local count=0;for k in pairs(points)do count=count+1;if(k~=1 and k~=2)or count>2 then return false end end
    return count==2
  end
  local choices={};local here=UnitPlot(fresh)
  for direction=0,5 do local p=Map.GetAdjacentPlot(here:GetX(),here:GetY(),direction);if p and Parking(p,claim)then choices[#choices+1]=p:GetIndex()end end
  table.sort(choices)
  for _,index in ipairs(choices)do
    fresh=Fresh();if not fresh then return Hold()end
    local plot=Map.GetPlotByIndex(index)
    if Parking(plot,claim)and Edge(plot)then
      local x,y=plot:GetX(),plot:GetY()
      local function Current()
        fresh=Fresh();if not fresh then return false end
        local current=Claim(claim.settler)
        local p=Map.GetPlotByIndex(index)
        if not current or current.from~=claim.from or current.goal.plot~=claim.goal.plot
          or current.goal.x~=claim.goal.x or current.goal.y~=claim.goal.y
          or not p or p:GetX()~=x or p:GetY()~=y or not Parking(p,current)or not Edge(p)then return false end
        return Fresh()~=nil
      end
      local sent,reason=RequestCivilian(ctx,state,fresh,"MOVE_TO",plot,nil,Current)
      if sent then return true end
      if reason~="engine_rejected"or not Fresh()then return Hold()end
    end
  end
  return false
end

local function DistrictPersonData(unit)
  local def=GameInfo.Units[unit:GetUnitType()]
  local classType=def and BaiqiPolicy.DistrictGreatPersonClass(def.UnitType)
  if not classType then return nil end
  local gp=unit:GetGreatPerson()
  if not gp or not BaiqiPolicy.Number(gp:GetActionCharges()) or gp:GetActionCharges()<=0 then return nil end
  local info=GameInfo.GreatPersonIndividuals[gp:GetIndividual()]
  local class=GameInfo.GreatPersonClasses[gp:GetClass()]
  if not info or not class or class.GreatPersonClassType~=classType or info.GreatPersonClassType~=classType
    or info.ActionRequiresSuzerainTerritory==true or info.ActionRequiresSuzerainTerritory==1
    or info.ActionRequiresSuzerainTerritory=="True" or info.ActionRequiresSuzerainTerritory=="true" then return nil end
  local district
  if info.ActionRequiresCompletedDistrictType~=nil then
    district=GameInfo.Districts[info.ActionRequiresCompletedDistrictType]
    if not district then return nil end
  end
  return gp,info,district,class,def
end

local function GPBridge(method,...)
  local bridge=type(ExposedMembers)=="table" and ExposedMembers.BaiqiGreatPersonIntentBridge
  if type(bridge)~="table" or bridge.version~=1 or bridge.marker~="baiqi-gp-intent-v1"
    or type(bridge[method])~="function" then return nil,nil,"bridge_unavailable" end
  local ok,a,b,c=pcall(bridge[method],...)
  if ok then return a,b,c end
  return nil,nil,"bridge_error"
end
local function DistrictPersonHeld(unit)
  local stage=GPBridge("Inspect",contextID,unit:GetID())
  return stage~="OPEN" and stage~="OBSERVED"
end
local function CreativeBridge(method,...)
  local bridge=type(ExposedMembers)=="table" and ExposedMembers.BaiqiCreativeIntentBridge
  if type(bridge)~="table" or bridge.version~=1 or bridge.marker~="baiqi-creative-intent-v1"
    or type(bridge[method])~="function" then return nil,nil,"bridge_unavailable" end
  local ok,a,b,c=pcall(bridge[method],...)
  if ok then return a,b,c end
  return nil,nil,"bridge_error"
end
local function CreativeHeld(unit)
  local stage=CreativeBridge("Inspect",contextID,unit:GetID())
  return stage~="OPEN" and stage~="OBSERVED"
end

local function ReligiousBridge(method,...)
  local bridge=type(ExposedMembers)=="table" and ExposedMembers.BaiqiReligiousIntentBridge
  if type(bridge)~="table" or bridge.version~=1 or bridge.marker~="baiqi-religious-intent-v1"
    or type(bridge[method])~="function" then return nil,nil,"bridge_unavailable" end
  local ok,a,b,c=pcall(bridge[method],...)
  if ok then return a,b,c end
  return nil,nil,"bridge_error"
end
local function MissionaryHeld(unit)
  local stage=ReligiousBridge("Inspect",contextID,unit:GetID())
  return stage~="OPEN" and stage~="OBSERVED"
end

local function ProphetBridge(method,...)
  local bridge=type(ExposedMembers)=="table" and ExposedMembers.BaiqiProphetIntentBridge
  if type(bridge)~="table" or bridge.version~=1 or bridge.marker~="baiqi-prophet-intent-v1"
    or type(bridge[method])~="function" then return nil,nil,"bridge_unavailable" end
  local ok,a,b,c=pcall(bridge[method],...)
  if ok then return a,b,c end
  return nil,nil,"bridge_error"
end
ProphetHeld=function(unit)
  local stage=ProphetBridge("Inspect",contextID,unit:GetID())
  return stage~="OPEN"
end

local function MissionaryData(unit)
  local def=GameInfo.Units[unit:GetUnitType()]
  if not def or def.UnitType~="UNIT_MISSIONARY" or type(unit.GetReligionType)~="function"
    or type(unit.GetSpreadCharges)~="function" then return nil end
  local religion,charges=unit:GetReligionType(),unit:GetSpreadCharges()
  if not BaiqiPolicy.Number(religion) or religion<0 or religion%1~=0 or religion>2147483647
    or not BaiqiPolicy.Number(charges) or charges<=0 or charges%1~=0 or charges>1000000 then return nil end
  return religion,charges
end

local function MissionaryCity(ctx,player,unit,city)
  if not city or city:GetOwner()~=ctx.player then return nil end
  local found=player:GetCities():FindID(city:GetID())
  if not BaiqiPolicy.MatchesID(found,city:GetID()) or found:GetOwner()~=ctx.player then return nil end
  local religion=MissionaryData(unit)
  local pr,cr=player:GetReligion(),found:GetReligion()
  local plot=Map.GetPlot(found:GetX(),found:GetY())
  if religion==nil or not pr or not cr or not plot or not Safe(plot,player)
    or type(pr.GetReligionTypeCreated)~="function" or type(cr.GetMajorityReligion)~="function"
    or not BaiqiPolicy.MissionaryTarget(ctx.player,pr:GetReligionTypeCreated(),religion,found:GetOwner(),
      cr:GetMajorityReligion(),visibility:IsRevealed(plot:GetX(),plot:GetY()),visibility:IsVisible(plot:GetX(),plot:GetY())) then
    return nil
  end
  return plot
end

local function RequestMissionary(unit,city)
  local ctx,player,state=PlayerContext()
  if not ctx or not unit or not city then return false end
  local religion,charges=MissionaryData(unit)
  local here=UnitPlot(unit)
  if religion==nil or not here or pendingUnits[unit:GetID()] then return false end
  local unitID,cityID,x,y=unit:GetID(),city:GetID(),here:GetX(),here:GetY()
  local operation=GameInfo.UnitOperations and GameInfo.UnitOperations.UNITOPERATION_SPREAD_RELIGION
  if not operation or not BaiqiPolicy.Number(operation.Hash) or operation.Hash%1~=0 then return false end
  local function StillEligible()
    local freshCtx,freshPlayer,freshState=PlayerContext()
    if not freshCtx or not CoreIdle() or freshCtx.player~=ctx.player or missionaryPurchase.Held() then return nil end
    local fresh=freshPlayer:GetUnits():FindID(unitID)
    local target=freshPlayer:GetCities():FindID(cityID)
    if not BaiqiPolicy.MatchesID(fresh,unitID) or fresh:GetOwner()~=ctx.player
      or not BaiqiPolicy.MatchesID(target,cityID) or target:GetOwner()~=ctx.player
      or not BaiqiPolicy.CanCivilian(freshCtx,UnitSnapshot(fresh,freshState))
      or not BaiqiPolicy.ActionAllowed("UNIT_MISSIONARY","SPREAD_RELIGION")
      or fresh:IsReadyToMove()~=true then return nil end
    local currentReligion,currentCharges=MissionaryData(fresh)
    local current=UnitPlot(fresh)
    local targetPlot=MissionaryCity(freshCtx,freshPlayer,fresh,target)
    if currentReligion~=religion or currentCharges~=charges or not current or not targetPlot
      or current:GetX()~=x or current:GetY()~=y or target:GetX()~=x or target:GetY()~=y
      or not Safe(current,freshPlayer) or UnitManager.CanStartOperation(fresh,operation.Hash,nil)~=true then return nil end
    return fresh
  end
  local fresh=StillEligible()
  if not fresh then return false end
  local id=NextRequest("missionary:"..unitID..":"..religion..":"..charges..":"..cityID)
  if not id then return false end
  local granted,token=ReligiousBridge("Prepare",ctx.player,unitID,religion,charges,x,y,cityID)
  if granted~=true or type(token)~="string" then return false end
  pendingUnits[unitID]={id=id,kind="SPREAD_RELIGION",persistent=true,token=token,religion=religion,
    charges=charges,unitType="UNIT_MISSIONARY",cityID=cityID,from=here:GetIndex(),moves=fresh:GetMovesRemaining(),elapsed=0}
  fresh=StillEligible()
  if not fresh then
    Log("missionary_intent_held","id="..id.."|unit="..unitID.."|reason=eligibility_changed_after_intent")
    return true
  end
  Log("request","id="..id.."|source=BACKGROUND|unit="..unitID.."|operation=SPREAD_RELIGION|city="..cityID.."|charges="..charges)
  -- Native row has no target mode: exact own city-center checks above are the
  -- target boundary. Supplying arbitrary x/y does not authorize a native city.
  local ok,err=pcall(UnitManager.RequestOperation,fresh,operation.Hash)
  if not ok then Log("missionary_operation_unknown","id="..id.."|unit="..unitID.."|reason="..tostring(err)) end
  return true
end

local function ProcessMissionary(ctx,player,state,unit)
  if missionaryPurchase.Held() then return false end
  if MissionaryHeld(unit) then
    Reason("missionary:"..unit:GetID(),"传教士等待持久化回执；其他内政继续执行")
    return false
  end
  local religion=MissionaryData(unit)
  local here=UnitPlot(unit)
  if religion==nil or not here then
    Reason("missionary:"..unit:GetID(),"传教士等待合法宗教归属与传播次数")
    return false
  end
  local id=unit:GetID()
  local prior=missionaryPlans[id]
  local city=prior and prior.religion==religion and player:GetCities():FindID(prior.cityID)
  local target=city and BaiqiPolicy.MatchesID(city,prior.cityID) and MissionaryCity(ctx,player,unit,city)
  if not target then
    missionaryPlans[id]=nil
    local candidates={}
    for _,candidate in player:GetCities():Members() do
      local plot=MissionaryCity(ctx,player,unit,candidate)
      if plot then candidates[#candidates+1]={city=candidate,plot=plot,
        distance=Map.GetPlotDistance(here:GetX(),here:GetY(),plot:GetX(),plot:GetY())} end
    end
    table.sort(candidates,function(a,b)
      if a.distance~=b.distance then return a.distance<b.distance end
      return a.city:GetID()<b.city:GetID()
    end)
    for _,candidate in ipairs(candidates) do
      if candidate.plot:GetIndex()==here:GetIndex() or PathStep(unit,candidate.plot,player,state) then
        city,target=candidate.city,candidate.plot
        missionaryPlans[id]={cityID=city:GetID(),religion=religion}
        break
      end
    end
  end
  if not target then
    Reason("missionary:"..id,"传教士等待安全可见、尚需本教的国内城市")
    return false
  end
  if target:GetIndex()==here:GetIndex() then
    if RequestMissionary(unit,city) then missionaryPlans[id]=nil;return true end
  else
    local step=PathStep(unit,target,player,state)
    if step and RequestCivilian(ctx,state,unit,"MOVE_TO",step) then return true end
  end
  Reason("missionary:"..id,"传教士等待安全国内路径或原生传播资格")
  return false
end


-- Shared Core purchase state is authoritative across UI reloads. Unknown
-- permission holds missionaries; it never blocks unrelated city production.
function missionaryPurchase.Bridge(method,...)
  local argc,args=select("#",...),{...}
  local ok,a,b,c=pcall(function()
    local bridge=type(ExposedMembers)=="table"and ExposedMembers.BaiqiMissionaryPurchaseBridge
    if type(bridge)~="table"or bridge.version~=1 or bridge.marker~="baiqi-missionary-purchase-v1"
      or type(bridge[method])~="function"then return "UNAVAILABLE"end
    local unpackArgs=table.unpack or unpack
    return bridge[method](unpackArgs(args,1,argc))
  end)
  if ok then return a,b,c end
  return "UNAVAILABLE"
end
function missionaryPurchase.Held()
  return missionaryPurchase.Bridge("Inspect",contextID)~="OPEN"
end
function missionaryPurchase.SafeCity(pid,city)
  local ctx,player=PlayerContext()
  if not ctx or ctx.player~=pid or not CoreIdle()or not city or city:GetOwner()~=pid then return false end
  local found=player:GetCities():FindID(city:GetID())
  if not BaiqiPolicy.MatchesID(found,city:GetID())or found:GetOwner()~=pid
    or found:GetX()~=city:GetX()or found:GetY()~=city:GetY()then return false end
  local plot=Map.GetPlot(found:GetX(),found:GetY())
  return plot~=nil and plot:GetX()==found:GetX()and plot:GetY()==found:GetY()
    and plot:GetOwner()==pid and Revealed(plot)and visibility:IsVisible(plot:GetX(),plot:GetY())==true
    and Safe(plot,player)==true
end
function missionaryPurchase.Demand(player,pid)
  return type(BaiqiMissionaryPurchaseDemand)=="table"
    and BaiqiMissionaryPurchaseDemand.Read({GameInfo=GameInfo,SafeCity=missionaryPurchase.SafeCity},player,pid)==true
end
function missionaryPurchase.Request(ctx,cityID)
  local pid,at,reserve=ctx.player,turn,C.missionaryFaithReserve
  local native=CityManager.RequestCommand
  local requestID
  if type(native)~="function"or type(BaiqiMissionaryPurchaseSubmit)~="table"then return false end
  local E={GameInfo=GameInfo,MilitaryFormationTypes=MilitaryFormationTypes,CityCommandTypes=CityCommandTypes,
    Quote=BaiqiMissionaryPurchase,Demand=missionaryPurchase.Demand,
    Bridge=function()return type(ExposedMembers)=="table"and ExposedMembers.BaiqiMissionaryPurchaseBridge end}
  E.Current=function(who)
    local fresh,player=PlayerContext()
    local currentWriter=CityManager.RequestCommand
    local currentQualifier=CityManager.CanStartCommand
    if fresh and who==pid and fresh.player==pid and BaiqiPolicy.Context(fresh)and CoreIdle()
      and turn==at and Game.GetCurrentGameTurn()==at and C.missionaryFaithReserve==reserve
      and currentWriter==native and currentQualifier==E.CityManager.CanStartCommand then return player end
  end
  E.CityManager={CanStartCommand=CityManager.CanStartCommand,RequestCommand=function(city,op,params)
    local player=E.Current(pid)
    if not player or not missionaryPurchase.SafeCity(pid,city)then return false end
    requestID=NextRequest("missionary_purchase:"..cityID..":"..at)
    if not requestID then return false end
    Log("request","id="..requestID.."|source=BACKGROUND|city="..cityID.."|operation=PURCHASE|unit=UNIT_MISSIONARY")
    return native(city,op,params)
  end}
  local stage,token,reason=BaiqiMissionaryPurchaseSubmit.Request(E,pid,cityID,reserve)
  if type(token)=="string"and(stage=="ARMED"or stage=="OBSERVED")then
    if stage=="ARMED"then
      missionaryPurchase.pending={id=requestID or token,token=token,cityID=cityID}
      Log("missionary_purchase_held","token="..token.."|reason="..tostring(reason))
    else
      Log("observed","id="..(requestID or token).."|city="..cityID.."|kind=PURCHASE|unit=UNIT_MISSIONARY|proof=core_new_unit_and_exact_faith_debit")
    end
    return true
  end
  return false
end
function missionaryPurchase.Process(ctx,player)
  if missionaryPurchase.pending or(missionaryPurchase.doneTurn==turn and missionaryPurchase.donePlayer==ctx.player)then return false,false end
  local function Done()
    missionaryPurchase.doneTurn=turn;missionaryPurchase.donePlayer=ctx.player;missionaryPurchase.search=nil
  end
  if missionaryPurchase.Held()or not missionaryPurchase.Demand(player,ctx.player)then Done();return false,false end
  local search=missionaryPurchase.search
  if not search or search.turn~=turn or search.player~=ctx.player then
    search={turn=turn,player=ctx.player,failed={}};missionaryPurchase.search=search
  end
  local cities={}
  for _,city in player:GetCities():Members()do
    local id=city:GetID()
    if BaiqiPolicy.Number(id)and id>=0 and id<=2147483647 and id%1==0 and city:GetOwner()==ctx.player
      and not search.failed[id]then cities[#cities+1]={id=id,city=city}end
  end
  table.sort(cities,function(a,b)return a.id<b.id end)
  local choice=cities[1]
  if not choice then Done();return false,false end
  search.failed[choice.id]=true
  if missionaryPurchase.SafeCity(ctx.player,choice.city)and missionaryPurchase.Request(ctx,choice.id)then Done();return true,false end
  if #cities>1 then return false,true end
  Done();return false,false
end

local function NaturalistPurchaseBridge(method,...)
  local function Invoke(...)
    local bridge=type(ExposedMembers)=="table" and ExposedMembers.BaiqiNaturalistPurchaseBridge
    if type(bridge)~="table" or bridge.version~=1 or bridge.marker~="baiqi-naturalist-purchase-v1"
      or type(bridge[method])~="function" then return nil,nil,"bridge_unavailable" end
    return bridge[method](...)
  end
  local ok,a,b,c=pcall(Invoke,...)
  if ok then return a,b,c end
  return nil,nil,"bridge_unavailable"
end

NaturalistPurchaseHeld=function()
  if pendingPurchase~=nil then return true end
  local stage=NaturalistPurchaseBridge("Inspect",contextID)
  return stage=="ARMED"
end

local function NaturalistPurchaseDemand(ctx,player,grantedToken)
  local ok,demand=pcall(function()
    local current,owner=PlayerContext()
    if not ctx or not current or current.player~=ctx.player or not BaiqiPolicy.Context(current)
      or not CoreIdle() then return false end
    local stage,token=NaturalistPurchaseBridge("Inspect",current.player,grantedToken)
    if grantedToken==nil then
      if stage~="OPEN" then return false end
    elseif type(grantedToken)~="string" or stage~="ARMED" or token~=grantedToken then return false end
    local function EmptyStock()
      local count,seen=0,{}
      for _,unit in owner:GetUnits():Members() do
        count=count+1
        if count>4096 then return false end
        local id=unit:GetID()
        if not BaiqiPolicy.Number(id) or id<0 or id>2147483647 or id%1~=0 or seen[id]
          or unit:GetOwner()~=current.player then return false end
        seen[id]=true
        local row=GameInfo.Units[unit:GetUnitType()]
        if not row or type(row.UnitType)~="string" then return false end
        if row.UnitType=="UNIT_NATURALIST" then
          if type(unit.IsDelayedDeath)~="function" then return false end
          local dead=unit:IsDelayedDeath()
          if type(dead)~="boolean" or not dead then return false end
        end
      end
      return true
    end
    if not EmptyStock() then return false end
    local indices,why=BaiqiHeritageCandidates.Collect("UNIT_NATURALIST",current.player,nil,Game,Map,visibility)
    if why~="ok" then return false end
    for _,index in ipairs(indices) do
      local plot=Map.GetPlotByIndex(index)
      if plot and plot:GetIndex()==index and Revealed(plot)
        and visibility:IsVisible(plot:GetX(),plot:GetY())==true and plot:GetOwner()==current.player
        and not plot:IsWater() and not plot:IsImpassable() and plot:IsNationalPark()==false
        and Safe(plot,owner) then return EmptyStock() end
    end
    return false
  end)
  return ok and demand==true
end

local function RequestNaturalistPurchase(city)
  local armedToken
  local function Attempt()
    local ctx,player=PlayerContext()
    if not ctx or not BaiqiPolicy.Context(ctx) or not CoreIdle() or pendingPurchase then return false end
    local reserve=C.naturalistFaithReserve
    if not BaiqiPolicy.Number(reserve) or reserve<0 then return false end
    local pid,at=ctx.player,turn
    local cityID,x,y=city:GetID(),city:GetX(),city:GetY()
    if not NaturalistPurchaseDemand(ctx,player) then return false end
    local quote=BaiqiNaturalistPurchase.Quote(player,pid,city,reserve)
    if not quote or quote.cityID~=cityID or quote.owner~=pid or quote.x~=x or quote.y~=y then return false end
    local function Signature()
      local sig={operation=CityCommandTypes.PURCHASE,unitKey=CityCommandTypes.PARAM_UNIT_TYPE,
        yieldKey=CityCommandTypes.PARAM_YIELD_TYPE,formationKey=CityCommandTypes.PARAM_MILITARY_FORMATION_TYPE,
        writer=CityManager.RequestCommand}
      if type(sig.writer)~="function" then return nil end
      for _,key in ipairs({"operation","unitKey","yieldKey","formationKey"}) do
        local value=sig[key]
        if not BaiqiPolicy.Number(value) or value<-2147483648 or value>4294967295 or value%1~=0 then return nil end
      end
      if sig.unitKey==sig.yieldKey or sig.unitKey==sig.formationKey or sig.yieldKey==sig.formationKey then return nil end
      return sig
    end
    local signature=Signature()
    if not signature then return false end
    local function Guard(token)
      local current,owner=PlayerContext()
      if not current or current.player~=pid or not BaiqiPolicy.Context(current) or not CoreIdle()
        or turn~=at or Game.GetCurrentGameTurn()~=at or C.naturalistFaithReserve~=reserve then return nil end
      if not NaturalistPurchaseDemand(current,owner,token) then return nil end
      local fresh=owner:GetCities():FindID(cityID)
      if not BaiqiPolicy.MatchesID(fresh,cityID) or fresh:GetOwner()~=pid
        or fresh:GetX()~=x or fresh:GetY()~=y then return nil end
      local sig=Signature()
      if not sig then return nil end
      for key,value in pairs(signature) do if sig[key]~=value then return nil end end
      local row=GameInfo.Units.UNIT_NATURALIST
      if not row or row.UnitType~="UNIT_NATURALIST" or row.Hash~=quote.unitHash
        or GameInfo.Yields.YIELD_FAITH.Index~=quote.faithYieldIndex
        or MilitaryFormationTypes.STANDARD_MILITARY_FORMATION~=quote.formationType then return nil end
      if fresh:GetGold():GetPurchaseCost(quote.faithYieldIndex,quote.unitHash,quote.formationType)~=quote.cost
        or owner:GetReligion():GetFaithBalance()~=quote.faithBalance then return nil end
      return fresh
    end
    if not Guard(nil) then return false end
    local id=NextRequest("naturalist_purchase:"..cityID..":"..at)
    if not id then return false end
    local granted,token=NaturalistPurchaseBridge("Prepare",pid,cityID,x,y,quote.unitHash,quote.cost,quote.faithBalance,reserve)
    if granted~=true or type(token)~="string" or #token==0 then return false end
    armedToken=token
    pendingPurchase={id=id,token=token,persistent=true,cityID=cityID,x=x,y=y,unitHash=quote.unitHash,
      cost=quote.cost,faithBefore=quote.faithBalance,turn=at,elapsed=0}
    local after=BaiqiNaturalistPurchase.Quote(player,pid,city,reserve)
    local same=after~=nil
    if same then for key,value in pairs(quote) do if after[key]~=value then same=false end end end
    local fresh=same and Guard(token)
    if not fresh then
      Log("naturalist_purchase_held","id="..id.."|city="..cityID.."|reason=eligibility_changed_after_intent")
      return true
    end
    local params={[signature.unitKey]=quote.unitHash,[signature.yieldKey]=quote.faithYieldIndex,
      [signature.formationKey]=quote.formationType}
    Log("request","id="..id.."|source=BACKGROUND|city="..cityID.."|operation=PURCHASE|unit=UNIT_NATURALIST|cost="..quote.cost)
    local ok=pcall(CityManager.RequestCommand,fresh,signature.operation,params)
    if not ok then Log("naturalist_purchase_unknown","id="..id.."|city="..cityID) end
    return true
  end
  local ok,submitted=pcall(Attempt)
  if ok then return submitted==true end
  if armedToken then Log("naturalist_purchase_held","token="..armedToken.."|reason=read_unavailable_after_intent");return true end
  return false
end

local function ProcessNaturalistPurchase(ctx,player)
  if pendingPurchase or purchaseDoneTurn==turn then return false,false end
  if not NaturalistPurchaseDemand(ctx,player) then purchaseDoneTurn=turn;purchaseSearch=nil;return false,false end
  if not purchaseSearch or purchaseSearch.turn~=turn or purchaseSearch.player~=ctx.player then
    purchaseSearch={turn=turn,player=ctx.player,failed={}}
  end
  local cities={}
  for _,city in player:GetCities():Members() do
    local id=city:GetID()
    if BaiqiPolicy.Number(id) and id>=0 and id<=2147483647 and id%1==0
      and city:GetOwner()==ctx.player and not purchaseSearch.failed[id] then cities[#cities+1]={id=id,city=city} end
  end
  table.sort(cities,function(a,b) return a.id<b.id end)
  local choice=cities[1]
  if not choice then purchaseDoneTurn=turn;purchaseSearch=nil;return false,false end
  purchaseSearch.failed[choice.id]=true
  local plot=Map.GetPlot(choice.city:GetX(),choice.city:GetY())
  if plot and Revealed(plot) and visibility:IsVisible(plot:GetX(),plot:GetY())==true
    and plot:GetOwner()==ctx.player and Safe(plot,player) and RequestNaturalistPurchase(choice.city) then
    purchaseDoneTurn=turn;purchaseSearch=nil;return true,false
  end
  if #cities>1 then return false,true end
  purchaseDoneTurn=turn;purchaseSearch=nil
  return false,false
end

local function NaturalistDetour(ctx, player, unit, target)
  if not ctx or not player or not unit or not target then return nil end
  local here = UnitPlot(unit)
  if not here then return nil end
  local def = GameInfo.Units[unit:GetUnitType()]
  if not def or def.UnitType ~= "UNIT_NATURALIST" then return nil end
  if not BaiqiPolicy.CanCivilian(ctx, UnitSnapshot(unit, {})) then return nil end
  local hereX, hereY = here:GetX(), here:GetY()
  local targetX, targetY = target:GetX(), target:GetY()
  local currentDist = Map.GetPlotDistance(hereX, hereY, targetX, targetY)
  local candidates = {}
  for direction = 0, 5 do
    local plot = Map.GetAdjacentPlot(hereX, hereY, direction)
    if plot then
      if Revealed(plot) and visibility:IsVisible(plot:GetX(), plot:GetY()) == true
        and plot:GetOwner() == ctx.player and not plot:IsWater() and not plot:IsImpassable()
        and Safe(plot, player) then
        local legal, reason = CivilianMoveTarget(here, plot, unit, ctx.player)
        if legal then
          local dist = Map.GetPlotDistance(plot:GetX(), plot:GetY(), targetX, targetY)
          if dist < currentDist then
            local reserved = false
            for _, pending in pairs(pendingUnits) do
              if pending.kind == "MOVE_TO" and pending.plot == plot:GetIndex() then
                reserved = true
                break
              end
            end
            if not reserved then
              candidates[#candidates + 1] = { plot = plot, distance = dist, index = plot:GetIndex() }
            end
          end
        end
      end
    end
  end
  if #candidates == 0 then return nil end
  table.sort(candidates, function(a, b)
    if a.distance ~= b.distance then return a.distance < b.distance end
    return a.index < b.index
  end)
  return candidates[1].plot
end

local function NaturalistBridge(method,...)
  local bridge=type(ExposedMembers)=="table" and ExposedMembers.BaiqiNaturalistIntentBridge
  if type(bridge)~="table" or bridge.version~=1 or bridge.marker~="baiqi-naturalist-intent-v1"
    or type(bridge[method])~="function" then return nil,nil,"bridge_unavailable" end
  local ok,a,b,c=pcall(bridge[method],...)
  if ok then return a,b,c end
  return nil,nil,"bridge_error"
end
local function NaturalistHeld(unit)
  if NaturalistPurchaseHeld() then return true end
  local stage=NaturalistBridge("Inspect",contextID,unit:GetID())
  return stage~="OPEN" and stage~="OBSERVED"
end
local function NaturalistData(unit)
  local def=unit and GameInfo.Units[unit:GetUnitType()]
  if not def or def.UnitType~="UNIT_NATURALIST" or type(unit.GetParkCharges)~="function" then return nil end
  local charges=unit:GetParkCharges()
  if BaiqiPolicy.Number(charges) and charges>=1 and charges<=1000000 and charges%1==0 then return charges end
end
local function NaturalistTarget(ctx,player,unit,plot)
  if not ctx or not player or not unit or not plot or not NaturalistData(unit)
    or not Revealed(plot) or visibility:IsVisible(plot:GetX(),plot:GetY())~=true then return false end
  local indices,why=BaiqiHeritageCandidates.Collect("UNIT_NATURALIST",ctx.player,unit,Game,Map,visibility)
  if why~="ok" then return false end
  for _,index in ipairs(indices) do
    if index==plot:GetIndex() then return plot:GetOwner()==ctx.player and Safe(plot,player) end
  end
  return false
end

local function RequestNaturalist(unit)
  local ctx,player,state=PlayerContext()
  local charges=NaturalistData(unit)
  local here=unit and UnitPlot(unit)
  if not ctx or not charges or not here or pendingUnits[unit:GetID()] then return false end
  local unitID,x,y=unit:GetID(),here:GetX(),here:GetY()
  local action,why=BaiqiHeritageActions.Resolve("UNIT_NATURALIST","DESIGNATE_PARK",GameInfo.UnitOperations)
  if why~="ok" then return false end
  local function Guard()
    local current,owner,snapshot=PlayerContext()
    if not current or not BaiqiPolicy.Context(current) or not CoreIdle() or current.player~=ctx.player
      or NaturalistPurchaseHeld() then return nil end
    local fresh=owner:GetUnits():FindID(unitID)
    if not BaiqiPolicy.MatchesID(fresh,unitID) or fresh:GetOwner()~=ctx.player
      or not BaiqiPolicy.CanCivilian(current,UnitSnapshot(fresh,snapshot))
      or not BaiqiPolicy.ActionAllowed("UNIT_NATURALIST","DESIGNATE_PARK")
      or type(fresh.IsReadyToMove)~="function" or fresh:IsReadyToMove()~=true
      or NaturalistData(fresh)~=charges then return nil end
    local currentPlot=UnitPlot(fresh)
    local currentAction,currentWhy=BaiqiHeritageActions.Resolve("UNIT_NATURALIST","DESIGNATE_PARK",GameInfo.UnitOperations)
    if not currentPlot or currentPlot:GetX()~=x or currentPlot:GetY()~=y
      or currentAction~=action or currentWhy~="ok"
      or not NaturalistTarget(current,owner,fresh,currentPlot) then return nil end
    return fresh
  end
  local function Qualified()
    local fresh=Guard()
    if not fresh or UnitManager.CanStartOperation(fresh,action,nil)~=true then return nil end
    return Guard()
  end
  local fresh=Qualified()
  if not fresh then return false end
  local id=NextRequest("naturalist:"..unitID..":"..charges..":"..x..":"..y)
  if not id then return false end
  local granted,token=NaturalistBridge("Prepare",ctx.player,unitID,charges,x,y)
  if granted~=true or type(token)~="string" then return false end
  pendingUnits[unitID]={id=id,kind="DESIGNATE_PARK",persistent=true,token=token,
    charges=charges,unitType="UNIT_NATURALIST",x=x,y=y,from=here:GetIndex(),moves=fresh:GetMovesRemaining(),elapsed=0}
  fresh=Qualified()
  if not fresh then
    Log("naturalist_intent_held","id="..id.."|unit="..unitID.."|reason=eligibility_changed_after_intent")
    return true
  end
  Log("request","id="..id.."|source=BACKGROUND|unit="..unitID.."|operation=DESIGNATE_PARK|plot="..here:GetIndex())
  local ok,err=pcall(UnitManager.RequestOperation,fresh,action)
  if not ok then Log("naturalist_operation_unknown","id="..id.."|unit="..unitID.."|reason="..tostring(err)) end
  return true
end

local function ProcessNaturalist(ctx,player,state,unit)
  local id=unit:GetID()
  if NaturalistHeld(unit) then
    Reason("naturalist:"..id,"自然学家等待持久化购买或公园回执；其他内政继续执行")
    return false,false
  end
  local charges,here=NaturalistData(unit),UnitPlot(unit)
  if not charges or not here or not BaiqiPolicy.CanCivilian(ctx,UnitSnapshot(unit,state)) then return false,false end
  local indices,why=BaiqiHeritageCandidates.Collect("UNIT_NATURALIST",ctx.player,unit,Game,Map,visibility)
  if why~="ok" then naturalistSearches[id]=nil;return false,false end
  local key=UnitKey(unit)
  local search=naturalistSearches[id]
  if not search or search.key~=key or search.turn~=turn or search.charges~=charges then
    search={key=key,turn=turn,charges=charges,failed={}};naturalistSearches[id]=search
  end
  local candidates={}
  for _,index in ipairs(indices) do
    if not search.failed[index] then
      local plot=Map.GetPlotByIndex(index)
      if plot and plot:GetIndex()==index and Revealed(plot)
        and visibility:IsVisible(plot:GetX(),plot:GetY())==true
        and plot:GetOwner()==ctx.player and Safe(plot,player) then
        candidates[#candidates+1]={index=index,plot=plot,
          distance=Map.GetPlotDistance(here:GetX(),here:GetY(),plot:GetX(),plot:GetY())}
      end
    end
  end
  table.sort(candidates,function(a,b)
    if a.distance~=b.distance then return a.distance<b.distance end
    return a.index<b.index
  end)
  local target=candidates[1]
  if not target then
    naturalistSearches[id]=nil
    Reason("naturalist:"..id,"自然学家等待安全可见、符合原版规则的国内公园地点")
    return false,false
  end
  if target.index==here:GetIndex() then
    if RequestNaturalist(unit) then naturalistSearches[id]=nil;return true,false end
  else
    local step=PathStep(unit,target.plot,player,state)
    if step then
      local legal,reason=CivilianMoveTarget(here,step,unit,ctx.player)
      if not legal then
        step=reason=="civilian_target_occupied" and NaturalistDetour(ctx,player,unit,target.plot) or nil
      end
    end
    if step and RequestCivilian(ctx,state,unit,"MOVE_TO",step) then return true,false end
  end
  search.failed[target.index]=true
  if #candidates>1 then return false,true end
  naturalistSearches[id]=nil
  return false,false
end

-- Archaeology metadata is read in this UI context; Core has no slot/queue API.
local function ArchaeologyBridge(method,...)
  local args={...}
  local ok,a,b,c=pcall(function()
    local bridge=type(ExposedMembers)=="table" and ExposedMembers.BaiqiArchaeologyBridge
    if type(bridge)~="table" or bridge.version~=1 or bridge.marker~="baiqi-archaeology-intent-v1"
      or type(bridge[method])~="function" then return nil,nil,"bridge_unavailable" end
    if method=="Inspect" then return bridge.Inspect(args[1],args[2]) end
    if method=="PrepareExcavation" then return bridge.PrepareExcavation(args[1],args[2],args[3]) end
    if method=="PrepareChoice" then return bridge.PrepareChoice(args[1],args[2],args[3],args[4]) end
    if method=="PreparePendingChoice" then return bridge.PreparePendingChoice(args[1],args[2],args[3],args[4]) end
    return nil,nil,"method_unavailable"
  end)
  if ok then return a,b,c end
  return nil,nil,"bridge_error"
end
local function ArchaeologyPendingRead(ctx,player)
  if type(BaiqiPendingArtifact)~="table" or type(BaiqiPendingArtifact.Read)~="function" then return nil,"unavailable" end
  local ok,descriptor,status=pcall(BaiqiPendingArtifact.Read,ctx.player,player,Game,GameInfo,PlayerConfigurations)
  if ok then return descriptor,status=="pending" and "ok" or status end
  return nil,"unavailable"
end
local function ArchaeologyHomeSnapshot(ctx,player,unitID)
  if type(BaiqiArchaeologyHome)~="table" or type(BaiqiArchaeologyHome.Read)~="function" then return nil end
  local ok,home,status=pcall(BaiqiArchaeologyHome.Read,player,ctx.player,unitID)
  if ok and status=="ok" and home and #home.emptySlots>0 then return home end
end
local function ArchaeologySameHome(a,b)
  if type(a)~="table" or type(b)~="table" then return false end
  for _,key in ipairs({"unitID","unitType","homeCityID","cityX","cityY","buildingIndex","slotCount"}) do
    if a[key]~=b[key] then return false end
  end
  for _,key in ipairs({"emptySlots","workIndices"}) do
    if type(a[key])~="table" or type(b[key])~="table" or #a[key]~=#b[key] then return false end
    for i,value in ipairs(a[key]) do if b[key][i]~=value then return false end end
  end
  return true
end
local function ArchaeologySameDescriptor(a,b)
  if type(a)~="table" or type(b)~="table" then return false end
  for _,key in ipairs({"unitID","unitType","homeCityID","x","y","artifactIndex","artifactType",
    "actingPlayerID","choicePlayerID","targetPlayerID"}) do if a[key]~=b[key] then return false end end
  return true
end
local function ArchaeologyGuard(ctx,unitID,x,y,legacyChoice)
  local ok,unit,home,here=pcall(function()
    local current,player=PlayerContext()
    if not current or not BaiqiPolicy.Context(current) or current.player~=ctx.player or not CoreIdle() then return nil end
    local fresh=player:GetUnits():FindID(unitID)
    local row=fresh and GameInfo.Units[fresh:GetUnitType()]
    if not BaiqiPolicy.MatchesID(fresh,unitID) or fresh:GetOwner()~=ctx.player
      or not row or row.UnitType~="UNIT_ARCHAEOLOGIST" or not BaiqiPolicy.CivilianType(row.UnitType)
      or type(fresh.GetFormationUnitCount)~="function" or fresh:GetFormationUnitCount()~=1 then return nil end
    local plot=UnitPlot(fresh)
    if not plot or plot:GetX()~=x or plot:GetY()~=y or (not legacyChoice and plot:GetOwner()~=ctx.player)
      or not Revealed(plot) or visibility:IsVisible(x,y)~=true
      or (not legacyChoice and not Safe(plot,player)) then return nil end
    local snapshot=ArchaeologyHomeSnapshot(current,player,unitID)
    if snapshot then return fresh,snapshot,plot end
  end)
  if ok then return unit,home,here end
end
ArchaeologyHeld=function(unit)
  local stage=ArchaeologyBridge("Inspect",contextID,unit:GetID())
  return stage~="OPEN" and stage~="OBSERVED"
end

local function RequestArchaeologyExcavation(unit)
  local persisted=false
  local ok,result=pcall(function()
    local ctx,player=PlayerContext()
    local unitID=unit and unit:GetID()
    if not ctx or not BaiqiPolicy.MatchesID(unit,unitID) or pendingUnits[unitID] then return false end
    local here=UnitPlot(unit)
    if not here then return false end
    local x,y,stamp=here:GetX(),here:GetY(),Game.GetCurrentGameTurn()
    local action,why=BaiqiHeritageActions.Resolve("UNIT_ARCHAEOLOGIST","EXCAVATE",GameInfo.UnitOperations)
    local qualify,request=UnitManager.CanStartOperation,UnitManager.RequestOperation
    if why~="ok" or type(qualify)~="function" or type(request)~="function" then return false end
    local home=ArchaeologyHomeSnapshot(ctx,player,unitID)
    local resource=here:GetResourceType()
    local row=GameInfo.Resources[resource]
    if not home or not row or (row.ResourceType~="RESOURCE_ANTIQUITY_SITE" and row.ResourceType~="RESOURCE_SHIPWRECK") then return false end
    local resourceType,phase=row.ResourceType,nil
    local function Guard()
      local fresh,current,plot=ArchaeologyGuard(ctx,unitID,x,y)
      if not fresh or not ArchaeologySameHome(home,current) or Game.GetCurrentGameTurn()~=stamp
        or UnitManager.CanStartOperation~=qualify or UnitManager.RequestOperation~=request
        or not BaiqiPolicy.ActionAllowed("UNIT_ARCHAEOLOGIST","EXCAVATE")
        or not BaiqiPolicy.Number(fresh:GetMovesRemaining()) or fresh:GetMovesRemaining()<=0
        or type(fresh.IsReadyToMove)~="function" or fresh:IsReadyToMove()~=true then return nil end
      local currentAction,currentWhy=BaiqiHeritageActions.Resolve("UNIT_ARCHAEOLOGIST","EXCAVATE",GameInfo.UnitOperations)
      local currentRow=GameInfo.Resources[plot:GetResourceType()]
      if currentAction~=action or currentWhy~="ok" or plot:GetResourceType()~=resource
        or not currentRow or currentRow.ResourceType~=resourceType then return nil end
      local _,status=ArchaeologyPendingRead(ctx,player)
      if status~="none" then return nil end
      local stage,token=ArchaeologyBridge("Inspect",ctx.player,unitID)
      if phase then
        if stage~="EXCAVATE_ARMED" or token~=phase then return nil end
      elseif stage~="OPEN" and stage~="OBSERVED" then return nil end
      local indices,candidateWhy=BaiqiHeritageCandidates.Collect("UNIT_ARCHAEOLOGIST",ctx.player,fresh,Game,Map,visibility)
      if candidateWhy~="ok" then return nil end
      for _,index in ipairs(indices) do if index==plot:GetIndex() then return fresh,plot end end
    end
    local function Qualified()
      local fresh=Guard()
      if not fresh then return nil end
      local eligible,legal=pcall(qualify,fresh,action,nil)
      if not eligible or legal~=true then return nil end
      return Guard()
    end
    local fresh=Qualified()
    if not fresh then return false end
    local id=NextRequest("archaeology:"..unitID..":"..stamp..":"..x..":"..y)
    if not id then return false end
    local granted,token=ArchaeologyBridge("PrepareExcavation",ctx.player,unitID,
      {homeCityID=home.homeCityID,cityX=home.cityX,cityY=home.cityY,buildingIndex=home.buildingIndex,
       x=x,y=y,resourceIndex=resource,resourceType=resourceType,baselineWorkIDs=home.workIndices})
    if granted~=true or type(token)~="string" then return false end
    persisted,phase=true,token
    pendingUnits[unitID]={id=id,kind="EXCAVATE",persistent=true,token=token,unitType="UNIT_ARCHAEOLOGIST",
      homeCityID=home.homeCityID,cityX=home.cityX,cityY=home.cityY,buildingIndex=home.buildingIndex,
      baselineWorkIDs=home.workIndices,x=x,y=y,from=here:GetIndex(),moves=fresh:GetMovesRemaining(),elapsed=0}
    fresh=Qualified()
    if not fresh then Log("archaeology_intent_held","id="..id.."|unit="..unitID.."|reason=eligibility_changed_after_intent");return true end
    Log("request","id="..id.."|source=BACKGROUND|unit="..unitID.."|operation=EXCAVATE")
    local sent,err=pcall(request,fresh,action)
    if not sent then Log("archaeology_operation_unknown","id="..id.."|reason="..tostring(err)) end
    return true
  end)
  if not ok then Log("archaeology_request_unavailable",tostring(result)) end
  return persisted or (ok and result==true)
end

local function RequestArchaeologyChoice(descriptor)
  local persisted=false
  local ok,result=pcall(function()
    local ctx,player=PlayerContext()
    if not ctx or type(descriptor)~="table" then return false end
    local unitID,x,y=descriptor.unitID,descriptor.x,descriptor.y
    local stage,token=ArchaeologyBridge("Inspect",ctx.player,unitID)
    local legacy=stage=="OPEN" and token==nil
    if not legacy and (stage~="EXCAVATE_ARMED" or type(token)~="string") then return false end
    local fresh,home=ArchaeologyGuard(ctx,unitID,x,y,legacy)
    if not fresh or home.homeCityID~=descriptor.homeCityID then return false end
    local pending=pendingUnits[unitID]
    if pending and (legacy or pending.kind~="EXCAVATE" or pending.token~=token) then return false end
    local operation,paramKey=PlayerOperations.CHOOSE_ARTIFACT_PLAYER,PlayerOperations.PARAM_PLAYER_ONE
    local request=UI.RequestPlayerOperation
    local function Signed(value)
      return BaiqiPolicy.Number(value) and value%1==0 and value>=-2147483648 and value<=2147483647
    end
    if not Signed(operation) or not Signed(paramKey) or type(request)~="function" then return false end
    local stamp,phase=Game.GetCurrentGameTurn(),legacy and "OPEN" or "EXCAVATE_ARMED"
    local function Guard()
      local unit,current=ArchaeologyGuard(ctx,unitID,x,y,legacy)
      if not unit or not ArchaeologySameHome(home,current) or Game.GetCurrentGameTurn()~=stamp
        or PlayerOperations.CHOOSE_ARTIFACT_PLAYER~=operation or PlayerOperations.PARAM_PLAYER_ONE~=paramKey
        or UI.RequestPlayerOperation~=request then return nil end
      local actual,status=ArchaeologyPendingRead(ctx,player)
      if status~="ok" or not ArchaeologySameDescriptor(actual,descriptor) then return nil end
      local currentStage,currentToken=ArchaeologyBridge("Inspect",ctx.player,unitID)
      if currentStage==phase and currentToken==token then return unit end
    end
    if not Guard() then return false end
    local id=NextRequest("archaeology_choice:"..unitID..":"..(token or "pending")..":"..descriptor.artifactIndex)
    if not id then return false end
    local granted,prepared
    if legacy then
      granted,prepared=ArchaeologyBridge("PreparePendingChoice",ctx.player,unitID,
        {homeCityID=home.homeCityID,cityX=home.cityX,cityY=home.cityY,buildingIndex=home.buildingIndex,
         x=x,y=y,baselineWorkIDs=home.workIndices},descriptor)
    else granted,prepared=ArchaeologyBridge("PrepareChoice",ctx.player,unitID,token,descriptor) end
    if granted~=true or type(prepared)~="string" or (not legacy and prepared~=token) then return false end
    persisted,phase,token=true,"CHOICE_ARMED",prepared
    pendingUnits[unitID]={id=id,kind="CHOOSE_ARTIFACT_PLAYER",persistent=true,token=token,unitType="UNIT_ARCHAEOLOGIST",
      artifactIndex=descriptor.artifactIndex,choicePlayerID=descriptor.choicePlayerID,homeCityID=home.homeCityID,
      cityX=home.cityX,cityY=home.cityY,buildingIndex=home.buildingIndex,baselineWorkIDs=home.workIndices,x=x,y=y,elapsed=0}
    if not Guard() then Log("archaeology_choice_held","id="..id.."|unit="..unitID);return true end
    Log("request","id="..id.."|source=BACKGROUND|unit="..unitID.."|operation=CHOOSE_ARTIFACT_PLAYER")
    local sent,err=pcall(request,ctx.player,operation,{[paramKey]=descriptor.choicePlayerID})
    if not sent then Log("archaeology_choice_unknown","id="..id.."|reason="..tostring(err)) end
    return true
  end)
  if not ok then Log("archaeology_choice_unavailable",tostring(result)) end
  return persisted or (ok and result==true)
end

local function ProcessArchaeologist(ctx,player,state,unit)
  local id=unit:GetID()
  if ArchaeologyHeld(unit) then Reason("archaeology:"..id,"考古学家等待实际发掘、文物选择或入藏回执");return false,false end
  local home=ArchaeologyHomeSnapshot(ctx,player,id)
  local here=UnitPlot(unit)
  if not home or not here then return false,false end
  local indices,why=BaiqiHeritageCandidates.Collect("UNIT_ARCHAEOLOGIST",ctx.player,unit,Game,Map,visibility)
  if why~="ok" then return false,false end
  local key=UnitKey(unit)
  local search=archaeologySearches[id]
  if not search or search.key~=key or search.turn~=turn then search={key=key,turn=turn,failed={}};archaeologySearches[id]=search end
  local candidates={}
  for _,index in ipairs(indices) do
    if not search.failed[index] then
      local plot=Map.GetPlotByIndex(index)
      if plot and plot:GetOwner()==ctx.player and Safe(plot,player) then
        candidates[#candidates+1]={index=index,plot=plot,distance=Map.GetPlotDistance(here:GetX(),here:GetY(),plot:GetX(),plot:GetY())}
      end
    end
  end
  table.sort(candidates,function(a,b) if a.distance~=b.distance then return a.distance<b.distance end;return a.index<b.index end)
  local target=candidates[1]
  if not target then archaeologySearches[id]=nil;return false,false end
  if target.index==here:GetIndex() then
    if RequestArchaeologyExcavation(unit) then archaeologySearches[id]=nil;return true,false end
  else
    local step=PathStep(unit,target.plot,player,state)
    if step and RequestCivilian(ctx,state,unit,"MOVE_TO",step) then return true,false end
  end
  search.failed[target.index]=true
  if #candidates>1 then return false,true end
  archaeologySearches[id]=nil
  return false,false
end

local function RequestDistrictPerson(unit)
  local ctx,player,state=PlayerContext()
  if not BaiqiPolicy.CanCivilian(ctx,UnitSnapshot(unit,state))
    or not BaiqiPolicy.ActionAllowed(GameInfo.Units[unit:GetUnitType()].UnitType,"ACTIVATE_GREAT_PERSON") then return false end
  local gp,info,required,class,def=DistrictPersonData(unit)
  local here=UnitPlot(unit)
  local command=GameInfo.UnitCommands and GameInfo.UnitCommands.UNITCOMMAND_ACTIVATE_GREAT_PERSON
  local unitID,individual,charges=unit:GetID(),info and info.Index,gp and gp:GetActionCharges()
  if not gp or not command or not BaiqiPolicy.GreatPersonActivationPlot(def.UnitType,info,ctx.player,here,visibility,Map)
    or visibility:IsVisible(here:GetX(),here:GetY())~=true or not Safe(here,player)
    or pendingUnits[unit:GetID()] or UnitManager.CanStartCommand(unit,command.Hash,false,true)~=true then return false end
  local function StillEligible()
  local freshCtx,freshPlayer,freshState=PlayerContext()
  local freshGP,freshInfo,freshRequired,freshClass,freshDef=DistrictPersonData(unit)
  local freshHere=UnitPlot(unit)
  local found=freshPlayer and freshPlayer:GetUnits():FindID(unitID)
  if not CoreIdle() or not BaiqiPolicy.CanCivilian(freshCtx,UnitSnapshot(unit,freshState)) or freshCtx.player~=ctx.player
    or not BaiqiPolicy.MatchesID(found,unitID) or found:GetOwner()~=ctx.player
    or unit:IsReadyToMove()~=true or not BaiqiPolicy.MatchesID(unit,unitID) or unit:GetOwner()~=freshCtx.player
    or not freshGP or freshInfo.Index~=individual or freshClass.Index~=class.Index or freshDef.UnitType~=def.UnitType
    or not BaiqiPolicy.ActionAllowed(freshDef.UnitType,"ACTIVATE_GREAT_PERSON")
    or (required==nil)~=(freshRequired==nil) or (required and freshRequired.Index~=required.Index)
    or freshGP:GetActionCharges()~=charges or not freshHere or freshHere:GetIndex()~=here:GetIndex()
    or not BaiqiPolicy.GreatPersonActivationPlot(freshDef.UnitType,freshInfo,freshCtx.player,freshHere,visibility,Map)
    or visibility:IsVisible(freshHere:GetX(),freshHere:GetY())~=true
    or not Safe(freshHere,freshPlayer) then return false end
  return true
  end
  if not StillEligible() then return false end
  local id=NextRequest("district_person:"..unitID..":"..individual..":"..charges)
  if not id then return false end
  local granted,token=GPBridge("Prepare",ctx.player,unitID,def.UnitType,class.Index,individual,charges,here:GetX(),here:GetY())
  if granted~=true or type(token)~="string" then return false end
  local pending={id=id,kind="ACTIVATE_GREAT_PERSON",command=command.Hash,persistent=true,token=token,
    from=here:GetIndex(),moves=unit:GetMovesRemaining(),charges=charges,
    individual=individual,class=class.Index,unitType=def.UnitType,elapsed=0}
  pendingUnits[unitID]=pending
  -- The Core acknowledgement precedes the native command; UI property views
  -- can still be stale. Recheck every current eligibility boundary afterwards.
  if UnitManager.CanStartCommand(unit,command.Hash,false,true)~=true or not StillEligible() then
    Log("great_person_intent_held","id="..id.."|unit="..unitID.."|reason=eligibility_changed_after_intent")
    return true
  end
  Log("request","id="..id.."|source=BACKGROUND|unit="..unitID.."|command=ACTIVATE_GREAT_PERSON|charges="..charges.."|class="..class.GreatPersonClassType)
  local ok,err=pcall(UnitManager.RequestCommand,unit,command.Hash)
  if not ok then
    Log("great_person_command_unknown","id="..id.."|unit="..unitID.."|reason="..tostring(err))
  end
  return true
end

local function ProcessDistrictPerson(ctx,player,state,unit)
  if DistrictPersonHeld(unit) then
    Reason("district_person:"..unit:GetID(),"文职伟人等待持久化回执；其他内政继续执行")
    return false
  end
  local gp,info,required,class,def=DistrictPersonData(unit)
  if not gp then
    Reason("district_person:"..unit:GetID(),"文职伟人等待当前支持的激活条件")
    return false
  end
  local unitID,charges=unit:GetID(),gp:GetActionCharges()
  if RequestDistrictPerson(unit) then districtPersonPlans[unitID]=nil;return true end
  local border=BaiqiPolicy.UnownedBorderGreatPerson(def.UnitType,info)
  -- Other non-district abilities still need verified current native legality.
  if not required and not border then
    Reason("district_person:"..unit:GetID(),"文职伟人等待当前位置的原生激活条件")
    return false
  end
  local freshCtx,freshPlayer,freshState=PlayerContext()
  local freshGP,freshInfo,freshRequired,freshClass,freshDef=DistrictPersonData(unit)
  local found=freshPlayer and freshPlayer:GetUnits():FindID(unitID)
  if not BaiqiPolicy.CanCivilian(freshCtx,UnitSnapshot(unit,freshState)) or freshCtx.player~=ctx.player
    or not BaiqiPolicy.MatchesID(unit,unitID) or not BaiqiPolicy.MatchesID(found,unitID)
    or found:GetOwner()~=ctx.player or unit:IsReadyToMove()~=true
    or not freshGP or freshInfo.Index~=info.Index or freshClass.Index~=class.Index
    or freshDef.UnitType~=def.UnitType or freshGP:GetActionCharges()~=charges
    or (required==nil)~=(freshRequired==nil) or (required and freshRequired.Index~=required.Index)
    or BaiqiPolicy.UnownedBorderGreatPerson(freshDef.UnitType,freshInfo)~=border or DistrictPersonHeld(unit) then return false end
  local purpose=border and "UNOWNED_BORDER" or required.Index
  local plan=districtPersonPlans[unitID]
  if not plan or plan.owner~=ctx.player or plan.unitType~=def.UnitType or plan.class~=class.Index
    or plan.individual~=info.Index or plan.charges~=gp:GetActionCharges() or plan.required~=purpose then
    if plan then plan.route=nil end
    local count=0;for _ in pairs(districtPersonPlans) do count=count+1 end
    if not plan and count>=256 then return false end
    plan={owner=ctx.player,unitType=def.UnitType,class=class.Index,individual=info.Index,
      charges=gp:GetActionCharges(),required=purpose,blocked={}}
    districtPersonPlans[unitID]=plan
  end
  -- Keep a destination across steps and turns. Only an exhausted search wave
  -- is refreshed on a later turn, so changed conditions can eventually recover.
  if plan.exhaustedTurn and turn>plan.exhaustedTurn then plan.blocked={};plan.exhaustedTurn=nil end
  if plan.routeTurn~=turn then
    for index,reason in pairs(plan.blocked) do if reason=="route" then plan.blocked[index]=nil end end
    plan.routeTurn=turn
  end
  if plan.route then return false,true end
  -- A remembered owned destination is a proposal, freshly checked in its one city.
  if districtRoute.Enabled() and plan.target and plan.targetCity and not plan.blocked[plan.target] then
    local target={index=plan.target,cityID=plan.targetCity}
    local plot=districtRoute.Target(ctx,player,target,required,def,info,border)
    if plot and UnitIndex(unit)~=plan.target then
      target.plot=plot
      local submitted,continuing,handled=districtRoute.Start(ctx,player,state,unit,plan,target,required,info,class,def,border)
      if handled then return submitted,continuing end
      plan.blocked[plan.target]="route";plan.target=nil;plan.targetCity=nil
    elseif not plot then plan.target=nil;plan.targetCity=nil end
  end
  local targets,seen={},{}
  local function AddTarget(plot,cityID)
    if not plot or seen[plot:GetIndex()] or not Revealed(plot) then return end
    if border then
      if not BaiqiPolicy.GreatPersonActivationPlot(def.UnitType,info,ctx.player,plot,visibility,Map) then return end
    elseif plot:GetOwner()~=ctx.player then return end
    local target={plot=plot,index=plot:GetIndex(),cityID=cityID,
      distance=Map.GetPlotDistance(unit:GetX(),unit:GetY(),plot:GetX(),plot:GetY())}
    seen[target.index]=target;targets[#targets+1]=target
  end
  -- Retained border destinations can be checked without rescanning every city
  -- border. Native path and final write guards still run on every movement.
  local pathQueried=false
  if border and plan.target and not plan.blocked[plan.target] then
    AddTarget(Map.GetPlotByIndex(plan.target))
    local target=seen[plan.target]
    if target and UnitIndex(unit)~=plan.target then
      pathQueried=true
      local submitted,continuing,handled=districtRoute.Start(ctx,player,state,unit,plan,target,required,info,class,def,border)
      if handled then return submitted,continuing end
      plan.blocked[plan.target]="route"
    end
    if not target or plan.blocked[plan.target] then plan.target=nil end
  end
  if border then
    if type(Map.GetAdjacentPlot)~="function" then return false end
    local anchors={}
    for _,city in player:GetCities():Members() do
      for _,index in pairs(Map.GetCityPlots():GetPurchasedPlots(city) or {}) do
        if not anchors[index] then
          anchors[index]=true
          local plot=Map.GetPlotByIndex(index)
          if plot and Revealed(plot) and plot:GetOwner()==ctx.player then
            for direction=0,5 do AddTarget(Map.GetAdjacentPlot(plot:GetX(),plot:GetY(),direction)) end
          end
        end
      end
    end
  else
  for _,city in player:GetCities():Members() do
    if city:GetDistricts():HasDistrict(required.Index,true) then
      for _,district in city:GetDistricts():Members() do
        if district:GetType()==required.Index then
          local plot=Map.GetPlot(district:GetX(),district:GetY())
          AddTarget(plot,city:GetID())
        end
      end
    end
  end
  end
  for index in pairs(plan.blocked) do if not seen[index] then plan.blocked[index]=nil end end
  if plan.target and not seen[plan.target] then plan.target=nil end
  local here=UnitPlot(unit)
  local hereIndex=here and here:GetIndex()
  local command=GameInfo.UnitCommands and GameInfo.UnitCommands.UNITCOMMAND_ACTIVATE_GREAT_PERSON
  if here and seen[hereIndex] and BaiqiPolicy.GreatPersonActivationPlot(def.UnitType,info,ctx.player,here,visibility,Map)
    and visibility:IsVisible(here:GetX(),here:GetY())==true and Safe(here,player) and command then
    -- A failed journal/budget request does not mean this city is unsuitable.
    -- Native command legality can only be queried at the actual current tile.
    local legal=UnitManager.CanStartCommand(unit,command.Hash,false,true)
    if legal==true then return false end
    if legal==false then
      plan.blocked[hereIndex]="native"
      if plan.target==hereIndex then plan.target=nil end
    end
  end
  if plan.target and not plan.blocked[plan.target] then
    local target=seen[plan.target]
    if hereIndex==plan.target then return false end
    pathQueried=true
    local submitted,continuing,handled=districtRoute.Start(ctx,player,state,unit,plan,target,required,info,class,def,border)
    if handled then return submitted,continuing end
    plan.blocked[plan.target]="route";plan.target=nil
  end
  table.sort(targets,function(a,b) if a.distance~=b.distance then return a.distance<b.distance end return a.index<b.index end)
  for _,target in ipairs(targets) do
    if target.index~=hereIndex and not plan.blocked[target.index] then
      -- Scalar route failures survive only the existing search wave. Resume
      -- through Tick with fresh identity, formation and target checks; never
      -- issue fallback standby while unexamined destinations remain.
      if pathQueried then return false,true end
      pathQueried=true
      local submitted,continuing,handled=districtRoute.Start(ctx,player,state,unit,plan,target,required,info,class,def,border)
      if handled then return submitted,continuing end
      plan.blocked[target.index]="route"
    end
  end
  plan.exhaustedTurn=turn
  Reason("district_person:"..unit:GetID(),"文职伟人等待已建成的安全区域与原生激活资格")
  return false
end

local function ProphetData(unit)
  local def=GameInfo.Units[unit:GetUnitType()]
  if not def or def.UnitType~="UNIT_GREAT_PROPHET" then return nil end
  local gp=unit:GetGreatPerson()
  local individual=gp and GameInfo.GreatPersonIndividuals[gp:GetIndividual()]
  local class=gp and GameInfo.GreatPersonClasses[gp:GetClass()]
  if individual and class and individual.GreatPersonClassType=="GREAT_PERSON_CLASS_PROPHET"
    and class.GreatPersonClassType=="GREAT_PERSON_CLASS_PROPHET" then return individual,class end
end

local function ProphetQualification(player)
  local religion=player.GetReligion and player:GetReligion()
  if religion and religion.GetReligionTypeCreated and religion.GetNumBeliefsEarned and religion.HasReligiousFoundingUnit
    and religion:GetReligionTypeCreated()==-1 and religion:GetNumBeliefsEarned()==0
    and religion:HasReligiousFoundingUnit()==true then return religion end
end

local function RequestProphet(unit)
  local ctx,player,state=PlayerContext()
  if not BaiqiPolicy.CanCivilian(ctx,UnitSnapshot(unit,state)) then return false end
  local individual,class=ProphetData(unit)
  local religion=ProphetQualification(player)
  local here=UnitPlot(unit)
  local operation=GameInfo.UnitOperations and GameInfo.UnitOperations.UNITOPERATION_FOUND_RELIGION
  local unitID=unit:GetID()
  if not individual or not religion or not here or here:GetOwner()~=ctx.player
    or not Safe(here,player) or not operation or pendingUnits[unitID] then return false end
  for _,pending in pairs(pendingUnits) do if pending.kind=="FOUND_RELIGION" then return false end end
  if UnitManager.CanStartOperation(unit,operation.Hash,nil,{})~=true then return false end
  local freshCtx,freshPlayer,freshState=PlayerContext()
  local actual,actualClass=ProphetData(unit)
  if not freshCtx or freshCtx.player~=ctx.player or not BaiqiPolicy.MatchesID(unit,unitID)
    or not BaiqiPolicy.CanCivilian(freshCtx,UnitSnapshot(unit,freshState)) or not actual
    or actual.Index~=individual.Index or actualClass.Index~=class.Index
    or UnitIndex(unit)~=here:GetIndex() or here:GetOwner()~=freshCtx.player
    or not ProphetQualification(freshPlayer) then return false end
  local id=NextRequest("prophet:"..unitID..":"..individual.Index)
  if not id then return false end
  local granted,token=ProphetBridge("Prepare",ctx.player,unitID,class.Index,individual.Index,here:GetX(),here:GetY(),0)
  if granted~=true or type(token)~="string" then return false,true end
  -- A persisted grant is never replayed if this last UI observation changes.
  local finalCtx,finalPlayer,finalState=PlayerContext()
  local finalUnit=finalPlayer and finalPlayer:GetUnits():FindID(unitID)
  if not finalCtx or finalCtx.player~=ctx.player or not BaiqiPolicy.MatchesID(finalUnit,unitID)
    or finalUnit:GetOwner()~=ctx.player then return false,true end
  local finalIndividual,finalClass=ProphetData(finalUnit)
  if not BaiqiPolicy.CanCivilian(finalCtx,UnitSnapshot(finalUnit,finalState))
    or not finalIndividual or finalIndividual.Index~=individual.Index or finalClass.Index~=class.Index
    or UnitIndex(finalUnit)~=here:GetIndex() or here:GetOwner()~=finalCtx.player
    or not ProphetQualification(finalPlayer)
    or UnitManager.CanStartOperation(finalUnit,operation.Hash,nil,{})~=true then return false,true end
  unit=finalUnit
  pendingUnits[unitID]={id=id,kind="FOUND_RELIGION",from=here:GetIndex(),moves=unit:GetMovesRemaining(),
    individual=individual.Index,class=class.Index,unitType="UNIT_GREAT_PROPHET",earned=0,elapsed=0,
    persistent=true,token=token}
  Log("request","id="..id.."|source=BACKGROUND|unit="..unitID.."|operation=FOUND_RELIGION|individual="..individual.Index)
  UnitManager.RequestOperation(unit,operation.Hash)
  return true
end

local function ProcessProphet(ctx,player,state,unit)
  if ProphetHeld(unit) then
    Reason("prophet:"..unit:GetID(),"先知等待持久化建教回执；其他内政继续执行")
    return false
  end
  if not ProphetData(unit) or not ProphetQualification(player) then return false end
  for _,pending in pairs(pendingUnits) do if pending.kind=="FOUND_RELIGION" then return false end end
  local unitID=unit:GetID()
  local submitted,quarantined=RequestProphet(unit)
  if submitted then return true end
  if quarantined then
    Reason("prophet:"..unitID,"先知等待持久化许可与新鲜身份核对；其他内政继续执行")
    return false,true
  end
  local required=GameInfo.Districts.DISTRICT_HOLY_SITE
  local targets={}
  if required then
    for _,city in player:GetCities():Members() do
      if city:GetDistricts():HasDistrict(required.Index,true) then
        for _,district in city:GetDistricts():Members() do
          if district:GetType()==required.Index and district:IsComplete()==true and district:IsPillaged()==false then
            local plot=Map.GetPlot(district:GetX(),district:GetY())
            if plot and plot:GetOwner()==ctx.player then
              targets[#targets+1]={plot=plot,index=plot:GetIndex(),
                distance=Map.GetPlotDistance(unit:GetX(),unit:GetY(),plot:GetX(),plot:GetY())}
            end
          end
        end
      end
    end
  end
  table.sort(targets,function(a,b) if a.distance~=b.distance then return a.distance<b.distance end return a.index<b.index end)
  -- Distance/index determines the destination; only query paths until it is reachable.
  for _,target in ipairs(targets) do
    local step=PathStep(unit,target.plot,player,state)
    if step then return RequestCivilian(ctx,state,unit,"MOVE_TO",step) end
  end
  Reason("prophet:"..unit:GetID(),"先知等待已建成的安全圣地与原生建教资格")
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
  if CreativeHeld(unit) then
    Reason("creative:"..unit:GetID(),"创作等待持久化回执；其他内政继续执行")
    return false
  end
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
  if current and command and Revealed(here) and visibility:IsVisible(here:GetX(),here:GetY())==true
    and here:GetOwner()==ctx.player and Safe(here,player)
    and UnitManager.CanStartCommand(unit,command.Hash,false,true)==true then
    local latestKnown=known
    local function StillEligible()
      local freshCtx,freshPlayer,freshState=PlayerContext()
      local freshGP,freshIndividual,freshClass,freshDef=CreativeData(unit)
      local freshHere=UnitPlot(unit)
      local found=freshPlayer and freshPlayer:GetUnits():FindID(unitID)
      if not CoreIdle() or not BaiqiPolicy.CanCivilian(freshCtx,UnitSnapshot(unit,freshState)) or freshCtx.player~=ctx.player
        or not BaiqiPolicy.MatchesID(found,unitID) or found:GetOwner()~=ctx.player
        or not BaiqiPolicy.MatchesID(unit,unitID) or unit:GetOwner()~=ctx.player or unit:IsReadyToMove()~=true
        or not freshGP or freshIndividual.Index~=individual.Index or freshClass.Index~=class.Index
        or freshDef.UnitType~=def.UnitType or not freshHere or freshHere:GetIndex()~=here:GetIndex()
        or not Revealed(freshHere) or visibility:IsVisible(freshHere:GetX(),freshHere:GetY())~=true
        or freshHere:GetOwner()~=ctx.player or not Safe(freshHere,freshPlayer) then return false end
      local freshSites,freshKnown=CreativeSites(freshCtx,freshPlayer,freshIndividual)
      for _,site in ipairs(freshSites) do
        if site.plot:GetIndex()==freshHere:GetIndex() then latestKnown=freshKnown;return true end
      end
      return false
    end
    if not StillEligible() then return false end
    local id=NextRequest("creative:"..unitID..":"..individual.Index)
    if not id then return false end
    local granted,token=CreativeBridge("Prepare",ctx.player,unitID,def.UnitType,class.Index,individual.Index,here:GetX(),here:GetY())
    if granted~=true or type(token)~="string" then return false end
    local pending={id=id,kind="CREATE_GREAT_WORK",individual=individual.Index,persistent=true,token=token,
      individualType=individual.GreatPersonIndividualType,class=class.Index,unitType=def.UnitType,
      knownWorks=latestKnown,elapsed=0}
    pendingUnits[unitID]=pending
    if UnitManager.CanStartCommand(unit,command.Hash,false,true)~=true or not StillEligible() then
      Log("creative_intent_held","id="..id.."|unit="..unitID.."|reason=eligibility_changed_after_intent")
      return true
    end
    pending.knownWorks=latestKnown
    Log("request","id="..id.."|source=BACKGROUND|unit="..unitID.."|command=CREATE_GREAT_WORK|individual="..individual.Index)
    local ok,err=pcall(UnitManager.RequestCommand,unit,command.Hash)
    if not ok then Log("creative_command_unknown","id="..id.."|unit="..unitID.."|reason="..tostring(err)) end
    return true
  end
  local paths={}
  for _,site in ipairs(sites) do
    paths[#paths+1]={plot=site.plot,index=site.plot:GetIndex(),
      distance=Map.GetPlotDistance(unit:GetX(),unit:GetY(),site.plot:GetX(),site.plot:GetY())}
  end
  table.sort(paths,function(a,b) if a.distance~=b.distance then return a.distance<b.distance end return a.index<b.index end)
  for _,target in ipairs(paths) do
    local step=PathStep(unit,target.plot,player,state)
    if step then return RequestCivilian(ctx,state,unit,"MOVE_TO",step) end
  end
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

local function SettlementFeatureAllowed(plot)
  local ok,allowed=pcall(function()
    local index=plot:GetFeatureType()
    if index==-1 then return true end
    if not BaiqiPolicy.Number(index) or index<0 or index%1~=0 then return false end
    local row=GameInfo.Features[index]
    return row~=nil and row.Index==index and type(row.FeatureType)=="string" and row.FeatureType~=""
      and row.Settlement==true and row.NaturalWonder==false and row.Impassable==false
  end)
  return ok and allowed==true
end

local function SettlementSites(player, state, firstOnly, excluded, unitID, preferredIndex, oneValidation)
  assert(oneValidation==nil or type(oneValidation)=="boolean","Unknown settlement validation mode")
  assert(oneValidation~=true or(firstOnly==true and type(excluded)=="table"),"Missing settlement continuation state")
  local result,candidates = {},{}
  local ai = player:GetGrandStrategicAI()
  if ai == nil then return result end
  local seen={}
  local function AddCandidate(index,score,preferred)
    local reserved=reservations[index]
    if BaiqiPolicy.Number(index) and index>=0 and index%1==0 and not settlementCache.plots[index]
      and not (excluded and excluded[index])
      and (unitID==nil or reserved==nil or reserved==unitID) then
      local candidate=seen[index]
      if candidate then
        if score>candidate.score then candidate.score=score end
        candidate.preferred=candidate.preferred or preferred
      else
        candidate={index=index,score=score,preferred=preferred}
        seen[index]=candidate;candidates[#candidates+1]=candidate
      end
    end
  end
  -- Native rankings can change while a settler is en route. An existing goal
  -- remains a proposal only: every eligibility, path and dispatch check below
  -- still reads current state. Recruitment never supplies a preferred index.
  if preferredIndex~=nil then AddCandidate(preferredIndex,100,true) end
  local protectedHint=false
  for rank, recommendation in pairs(ai:GetSettlementRecommendations(12) or {}) do
    local index=recommendation.SettlingLocation
    if settlementCache.plots[index] then protectedHint=true end
    AddCandidate(index,100-(tonumber(rank) or 0),false)
  end
  local function CandidateBefore(a,b)
    if a.preferred~=b.preferred then return a.preferred end
    if a.score~=b.score then return a.score>b.score end
    return a.index<b.index
  end
  local fallbackAttempted=false
  local function AddFallback()
    if fallbackAttempted or not protectedHint then return end
    fallbackAttempted=true
    local ok,alternates=pcall(function()
      if not settlementCache.ready or settlementCache.unresolved~=1 then return nil end
      local op
      for _,record in pairs(settlementCache.records) do
        if record.stage=="ARMED" then op=record;break end
      end
      if not op then return nil end
      local actor=player:GetUnits():FindID(op.unitID)
      if not actor or not settlementCache.IsRetained(player,actor) then return nil end
      if visibility:IsRevealed(op.x,op.y)~=true or visibility:IsVisible(op.x,op.y)~=true then return nil end
      local oldPlot=Map.GetPlotByIndex(op.plot)
      if not oldPlot or oldPlot:GetIndex()~=op.plot or oldPlot:GetX()~=op.x or oldPlot:GetY()~=op.y then return nil end
      local cells=NeighborhoodGeometry(oldPlot,2)
      if not cells or #cells>19 then return nil end
      local proposals={}
      for _,cell in ipairs(cells) do
        if visibility:IsRevealed(cell.x,cell.y)==true and visibility:IsVisible(cell.x,cell.y)==true then
          local distance=Map.GetPlotDistance(op.x,op.y,cell.x,cell.y)
          if GeometryInteger(distance) and distance<=2 then
            proposals[#proposals+1]={index=cell.index,score=50-distance}
          end
        end
      end
      return proposals
    end)
    if ok and type(alternates)=="table" then
      local firstNew=#candidates+1
      for _,candidate in ipairs(alternates) do AddCandidate(candidate.index,candidate.score,false) end
      -- Sort only the appended tail: an already-visited native candidate must
      -- never move across the active traversal cursor.
      local tail={}
      for i=firstNew,#candidates do tail[#tail+1]=candidates[i] end
      table.sort(tail,CandidateBefore)
      for i,candidate in ipairs(tail) do candidates[firstNew+i-1]=candidate end
    end
  end
  if #candidates==0 then AddFallback() end
  table.sort(candidates,CandidateBefore)
  for i,candidate in ipairs(candidates) do
    if oneValidation then excluded[candidate.index]=true end
    local supportChecked=false
    local plot=Map.GetPlotByIndex(candidate.index)
    if plot and plot:GetIndex()==candidate.index and Revealed(plot) and not plot:IsWater()
      and not plot:IsImpassable() and not plot:IsCity() and SettlementFeatureAllowed(plot)
      and (plot:GetOwner()==-1 or plot:GetOwner()==contextID) and Safe(plot,player) then
      supportChecked=true
      if KnownExpansionSupport(plot,player,contextID)==true then
        result[#result+1] = {index=candidate.index, score=candidate.score, legal=true, revealed=true, safe=true,
          protected=false, plot=plot}
        if firstOnly then return result,i<#candidates end
      end
    end
    -- Append only after all earlier proposals were actually rejected. The
    -- continuation flag includes newly appended candidates before returning.
    if #result==0 and i==#candidates then AddFallback() end
    if oneValidation and supportChecked then return result,i<#candidates end
  end
  if oneValidation then return result,false end
  return result
end

local function RecruitAllowed(role,economy,player,state)
  -- Query native settlement hints only after every other recruitment gate passes.
  -- No hints are cached; the dispatch boundary repeats this against fresh state.
  economy.hasSafeSite=true
  local allowed=BaiqiPlanner.AllowRecruit(role,economy,C)
  economy.hasSafeSite=role=="settler" and allowed and #SettlementSites(player,state,true)>0 or false
  return allowed and (role~="settler" or economy.hasSafeSite)
end

local function ProcessSettler(ctx, player, state, unit)
  if SettlementHeld(unit) then
    Reason("settler_receipt:"..unit:GetID(),"移民保留未确认建城记录，等待原生命令结果")
    return RequestCivilianStandby(unit)
  end
  local stable=ExpansionStable(player,ctx.player)
  if stable~=true then
    Reason("settler_stability:"..unit:GetID(),stable==false
      and "先等己方城市忠诚恢复，再继续扩张" or "等待己方城市忠诚信息")
    -- Keep the remembered proposal and any native queue. Standby itself
    -- refuses a queued/unknown actor and never cancels an existing order.
    return RequestCivilianStandby(unit)
  end
  local here = UnitPlot(unit)
  if here==nil then return false end -- Consumed/removed units may remain in a transient collection snapshot.
  local id,key=unit:GetID(),UnitKey(unit)
  local goalState,goal=SettlerGoalBridge("Read",ctx.player,id)
  if goalState~="READY"or(goal~=nil and not SettlerGoalProposal(goal,id))then
    Reason("settler_goal:"..id,"移民等待行军计划读取与资格确认")
    return false
  end
  if goal~=nil then settlementTargets[id]=goal.plot end
  local search=settlerSearches[id]
  if not search or search.player~=ctx.player or search.turn~=turn or search.key~=key then
    search={player=ctx.player,turn=turn,key=key,tested={}}
    settlerSearches[id]=search
  end
  local oldTarget=settlementTargets[id]
  local oldPlot
  local function ForgetOld()
    if reservations[oldTarget]==id then reservations[oldTarget]=nil end
    settlementTargets[id]=nil;search.tested[oldTarget]=true
    -- The rejected proposal ID stays tested even when storage is unavailable.
    -- A later Read can restore the proposal, but cannot repeat this cleanup.
    SettlerGoalBridge("Forget",ctx.player,id)
  end
  if oldTarget~=nil and not search.tested[oldTarget] then
    local reserved=reservations[oldTarget]
    if reserved~=nil and reserved~=id then
      search.tested[oldTarget]=true
    else
      oldPlot=Map.GetPlotByIndex(oldTarget)
      if not oldPlot or oldPlot:GetIndex()~=oldTarget or not Revealed(oldPlot)
        or oldPlot:IsWater()or oldPlot:IsImpassable()or oldPlot:IsCity()
        or not SettlementFeatureAllowed(oldPlot)
        or(oldPlot:GetOwner()~=-1 and oldPlot:GetOwner()~=ctx.player) then
        ForgetOld();oldPlot=nil
      elseif KnownExpansionSupport(oldPlot,player,ctx.player)~=true then
        ForgetOld()
        -- Do not add another potentially expensive site scan to this callback.
        return false,true
      end
    end
  end
  local mayFound=player:GetCities():GetCount()==0 or settlementTargets[id]==here:GetIndex()
  if mayFound and KnownExpansionSupport(here,player,ctx.player)==true and Safe(here,player) and UnitManager.CanStartOperation(unit,UnitOperationTypes.FOUND_CITY)==true then
    settlerSearches[id]=nil
    return RequestCivilian(ctx,state,unit,"FOUND_CITY",here)
  end
  if oldPlot and oldTarget~=here:GetIndex() then
    -- A remembered goal already precedes native rankings. Validate its current
    -- route directly; no positive eligibility survives this callback.
    search.tested[oldTarget]=true
    local step=PathStep(unit,oldPlot,player,state)
    if step then
      -- An existing proposal needs a fresh read, not another save/actor scan.
      -- The path and final native command boundary still qualify this move.
      local s,g
      if goal~=nil then s,g=SettlerGoalBridge("Read",ctx.player,id)
      else s,g=SettlerGoalBridge("Remember",ctx.player,id,oldTarget,oldPlot:GetX(),oldPlot:GetY()) end
      if s~="READY"or not SettlerGoalProposal(g,id)or g.plot~=oldTarget
        or g.x~=oldPlot:GetX()or g.y~=oldPlot:GetY()then
        settlerSearches[id]=nil
        Reason("settler_goal:"..id,"移民等待行军计划保存与资格确认")
        return false
      end
      reservations[oldTarget]=id;settlementTargets[id]=oldTarget;settlerSearches[id]=nil
      return RequestCivilian(ctx,state,unit,"MOVE_TO",step)
    end
    -- Alternatives are still unqueried. The existing continuation contract
    -- resumes their fresh native enumeration on the next callback.
    return false,true
  end
  local sites,more=SettlementSites(player,state,true,search.tested,id,settlementTargets[id],true)
  local target=BaiqiPlanner.Site(sites,reservations,unit:GetID())
  if not mayFound and target and target.index==here:GetIndex() and KnownExpansionSupport(here,player,ctx.player)==true and Safe(here, player)
    and UnitManager.CanStartOperation(unit, UnitOperationTypes.FOUND_CITY) == true then
    settlerSearches[id]=nil
    return RequestCivilian(ctx, state, unit, "FOUND_CITY", here)
  end
  if target and target.index~=here:GetIndex() then
    search.tested[target.index]=true
    local step=PathStep(unit,target.plot,player,state)
    if step then
      local s,g=SettlerGoalBridge("Remember",ctx.player,id,target.index,target.plot:GetX(),target.plot:GetY())
      if s~="READY"or not SettlerGoalProposal(g,id)or g.plot~=target.index
        or g.x~=target.plot:GetX()or g.y~=target.plot:GetY()then
        settlerSearches[id]=nil
        Reason("settler_goal:"..id,"移民等待行军计划保存与资格确认")
        return false
      end
      reservations[target.index] = id
      settlementTargets[id] = target.index
      settlerSearches[id]=nil
      return RequestCivilian(ctx, state, unit, "MOVE_TO", step)
    end
  end
  if more==true then return false,true end
  settlerSearches[id]=nil
  Reason("settler:"..unit:GetID(), "移民等待已探明的安全城址或路线")
  return false
end

-- Match shipped UnitPanel's detailed build query. These are proposals only:
-- resolve native indices/hashes to actual rows, then qualify the chosen Hash.
-- Unknown shapes fall back to the original metadata scan, never to empty.
local function BuilderImprovementCandidates(unit, plot)
  if not UnitManager or type(UnitManager.CanStartOperation)~="function"
    or not UnitOperationTypes or UnitOperationTypes.BUILD_IMPROVEMENT==nil
    or UnitOperationTypes.PARAM_X==nil or UnitOperationTypes.PARAM_Y==nil
    or not UnitOperationResults or UnitOperationResults.IMPROVEMENTS==nil
    or not GameInfo or not GameInfo.Improvements then return nil end
  local params={[UnitOperationTypes.PARAM_X]=plot:GetX(),[UnitOperationTypes.PARAM_Y]=plot:GetY()}
  local ok,canStart,results=pcall(UnitManager.CanStartOperation,unit,UnitOperationTypes.BUILD_IMPROVEMENT,nil,params,true)
  if not ok or canStart~=true or type(results)~="table" then return nil end
  local values=results[UnitOperationResults.IMPROVEMENTS]
  if type(values)~="table" then return nil end
  local count,maximum=0,0
  for key in pairs(values) do
    if not BaiqiPolicy.Number(key) or key%1~=0 or key<1 then return nil end
    count=count+1
    if key>maximum then maximum=key end
  end
  if maximum~=count then return nil end
  local rows,seen={},{}
  for i=1,count do
    local value=values[i]
    if not BaiqiPolicy.Number(value) or value%1~=0 then return nil end
    local row=GameInfo.Improvements[value]
    if type(row)~="table" or not BaiqiPolicy.Number(row.Index) or row.Index<0 or row.Index%1~=0
      or not BaiqiPolicy.Number(row.Hash) or row.Hash%1~=0 then return nil end
    if not seen[row.Index] then rows[#rows+1]=row;seen[row.Index]=true end
  end
  table.sort(rows,function(a,b) return a.Index<b.Index end)
  return rows
end

local function BuilderAdjacentCandidates(unit)
  local ctx,player,state=PlayerContext()
  if not ctx or not CoreIdle() or not BaiqiPolicy.CanCivilian(ctx,UnitSnapshot(unit,state)) then return nil end
  local row=GameInfo.Units[unit:GetUnitType()]
  local def=BuilderAdjacentDefinition()
  if not row or row.UnitType~="UNIT_BUILDER" or not def or not UnitManager
    or type(UnitManager.GetOperationTargets)~="function" or type(UnitManager.CanStartOperation)~="function"
    or not UnitOperationResults or UnitOperationResults.PLOTS==nil then return nil end
  local ok,result=pcall(function()
    local targets=UnitManager.GetOperationTargets(unit,def.operation,{[def.typeKey]=def.hash})
    if type(targets)~="table" or type(targets[UnitOperationResults.PLOTS])~="table" then return nil end
    local candidates,seen,n={},{},0
    for _,index in pairs(targets[UnitOperationResults.PLOTS]) do
      n=n+1;if n>128 or not GeometryInteger(index) then return nil end
      if not seen[index] then
        seen[index]=true
        local plot=Map.GetPlotByIndex(index)
        local candidate=BuilderAdjacentTarget(ctx,player,unit,plot,def.hash)
        if candidate then
          local params={[def.xKey]=candidate.x,[def.yKey]=candidate.y,[def.typeKey]=def.hash}
          local called,can=pcall(UnitManager.CanStartOperation,unit,def.operation,nil,params)
          if called and can==true then candidates[#candidates+1]=candidate end
        end
      end
    end
    table.sort(candidates,function(a,b)return a.index<b.index end)
    return candidates
  end)
  if ok then return result end
end

local function PlanningTime()
  if type(Automation)~="table" or type(Automation.GetTime)~="function" then return nil end
  local ok,value=pcall(Automation.GetTime)
  if not ok or not BaiqiPolicy.Number(value) or value<0 then return nil end
  return value
end

local function BuilderBudgetExpired(started,limit)
  if not BaiqiPolicy.Number(started) or started<0 then return false end
  if not BaiqiPolicy.Number(limit) or limit<=0 then return false end
  local current=PlanningTime()
  if current==nil or current<started then return false end
  return current-started>=limit
end

local function PrepareBuilderPathPacket(ctx, player, state, unit, target)
  if not ctx or not player or not unit or not target then return nil end
  local currentCtx,currentPlayer,currentState=PlayerContext()
  if not currentCtx or currentCtx.player~=ctx.player then return nil end
  ctx,player,state=currentCtx,currentPlayer,currentState
  if not CoreIdle() then return nil end
  if not BaiqiPolicy.Context(ctx) then return nil end
  if turn ~= Game.GetCurrentGameTurn() then return nil end
  local unitID = unit:GetID()
  if pendingUnits[unitID] then return nil end
  local def = GameInfo.Units[unit:GetUnitType()]
  if not def or def.UnitType ~= 'UNIT_BUILDER' then return nil end
  local snapshot = UnitSnapshot(unit, state)
  if not BaiqiPolicy.CanCivilian(ctx, snapshot) then return nil end
  local initialKey,expectedTurn=UnitKey(unit),turn
  if not Revealed(target) then return nil end
  if not Safe(target, player) then return nil end
  local targetIndex = target:GetIndex()
  if not BaiqiPolicy.Number(targetIndex) or targetIndex < 0 or targetIndex % 1 ~= 0 then return nil end
  local start = UnitIndex(unit)
  if start == nil then return nil end
  local latest,latestPlayer,latestState=PlayerContext()
  local currentDef=GameInfo.Units[unit:GetUnitType()]
  if not latest or latest.player~=ctx.player or not BaiqiPolicy.Context(latest)
    or not currentDef or currentDef.UnitType~='UNIT_BUILDER'
    or not BaiqiPolicy.CanCivilian(latest,UnitSnapshot(unit,latestState))
    or UnitKey(unit)~=initialKey or pendingUnits[unitID]
    or Game.GetCurrentGameTurn()~=expectedTurn or not CoreIdle() then return nil end
  local ok, path = pcall(UnitManager.GetMoveToPathEx, unit, targetIndex)
  if not ok or type(path) ~= 'table' or type(path.plots) ~= 'table' then return nil end
  local plots = path.plots
  local count = 0
  for _ in pairs(plots) do count = count + 1 end
  if count < 2 or count > C.pathLimit then return nil end
  local copied = {}
  for i = 1, count do
    local index = plots[i]
    if not BaiqiPolicy.Number(index) or index < 0 or index % 1 ~= 0 then return nil end
    copied[i] = index
  end
  if copied[1] ~= start or copied[count] ~= targetIndex then return nil end
  if UnitIndex(unit) ~= start then return nil end
  local freshCtx, freshPlayer, freshState = PlayerContext()
  if not freshCtx or freshCtx.player ~= ctx.player then return nil end
  if not BaiqiPolicy.Context(freshCtx) then return nil end
  local freshUnit = freshPlayer:GetUnits():FindID(unitID)
  if not BaiqiPolicy.MatchesID(freshUnit, unitID) or freshUnit:GetOwner() ~= ctx.player then return nil end
  local freshDef = GameInfo.Units[freshUnit:GetUnitType()]
  if not freshDef or freshDef.UnitType ~= 'UNIT_BUILDER' then return nil end
  local freshSnapshot = UnitSnapshot(freshUnit, freshState)
  if not BaiqiPolicy.CanCivilian(freshCtx, freshSnapshot) then return nil end
  if freshSnapshot.formationCount ~= 1 then return nil end
  if not BaiqiPolicy.Number(freshSnapshot.moves) or freshSnapshot.moves <= 0 then return nil end
  if UnitIndex(freshUnit) ~= start then return nil end
  if UnitKey(unit)~=initialKey or UnitKey(freshUnit)~=initialKey
    or pendingUnits[unitID] or Game.GetCurrentGameTurn()~=expectedTurn
    or turn~=expectedTurn or not CoreIdle() then return nil end
  return {
    version = 1,
    player = ctx.player,
    turn = turn,
    unitID = unitID,
    unitType = 'UNIT_BUILDER',
    key = initialKey,
    targetIndex = targetIndex,
    path = copied
  }
end

local function ValidateBuilderPathPacket(ctx, player, state, unit, packet)
  if not ctx or not player or not unit or type(packet)~='table' then return nil end
  local currentCtx,currentPlayer,currentState=PlayerContext()
  if not currentCtx or currentCtx.player~=ctx.player then return nil end
  ctx,player,state=currentCtx,currentPlayer,currentState
  if not CoreIdle() then return nil end
  if not BaiqiPolicy.Context(ctx) then return nil end
  if turn ~= Game.GetCurrentGameTurn() then return nil end
  if packet.version ~= 1 then return nil end
  if packet.player ~= ctx.player then return nil end
  if packet.turn ~= turn then return nil end
  local unitID = unit:GetID()
  if packet.unitID ~= unitID then return nil end
  if packet.unitType ~= 'UNIT_BUILDER' then return nil end
  if packet.key ~= UnitKey(unit) then return nil end
  if pendingUnits[unitID] then return nil end
  local def = GameInfo.Units[unit:GetUnitType()]
  if not def or def.UnitType ~= 'UNIT_BUILDER' then return nil end
  local snapshot = UnitSnapshot(unit, state)
  if not BaiqiPolicy.CanCivilian(ctx, snapshot) then return nil end
  if snapshot.formationCount ~= 1 then return nil end
  if not BaiqiPolicy.Number(snapshot.moves) or snapshot.moves <= 0 then return nil end
  local start = UnitIndex(unit)
  if start == nil then return nil end
  local path = packet.path
  if type(path) ~= 'table' then return nil end
  local count = 0
  for _ in pairs(path) do count = count + 1 end
  if count < 2 or count > C.pathLimit then return nil end
  local targetIndex = packet.targetIndex
  if not BaiqiPolicy.Number(targetIndex) or targetIndex < 0 or targetIndex % 1 ~= 0 then return nil end
  if path[1] ~= start or path[count] ~= targetIndex then return nil end
  local cache = {}
  for i = 1, count do
    local index = path[i]
    if not BaiqiPolicy.Number(index) or index < 0 or index % 1 ~= 0 then return nil end
    local ok, plot = pcall(Map.GetPlotByIndex, index)
    if not ok or not plot then return nil end
    if not Revealed(plot) then return nil end
    if not Safe(plot, player, cache) then return nil end
    if plot:GetOwner() ~= -1 and plot:GetOwner() ~= ctx.player then return nil end
  end
  local ok,nextPlot=pcall(Map.GetPlotByIndex,path[2])
  if not ok or not nextPlot or nextPlot:GetIndex()~=path[2] then return nil end
  local freshCtx, freshPlayer, freshState = PlayerContext()
  if not freshCtx or freshCtx.player ~= ctx.player then return nil end
  if not BaiqiPolicy.Context(freshCtx) then return nil end
  local freshUnit = freshPlayer:GetUnits():FindID(unitID)
  if not BaiqiPolicy.MatchesID(freshUnit, unitID) or freshUnit:GetOwner() ~= ctx.player then return nil end
  local freshDef = GameInfo.Units[freshUnit:GetUnitType()]
  if not freshDef or freshDef.UnitType ~= 'UNIT_BUILDER' then return nil end
  local freshSnapshot = UnitSnapshot(freshUnit, freshState)
  if not BaiqiPolicy.CanCivilian(freshCtx, freshSnapshot) then return nil end
  if freshSnapshot.formationCount ~= 1 then return nil end
  if not BaiqiPolicy.Number(freshSnapshot.moves) or freshSnapshot.moves <= 0 then return nil end
  if UnitIndex(freshUnit) ~= start then return nil end
  if UnitKey(unit)~=packet.key or UnitKey(freshUnit)~=packet.key
    or pendingUnits[unitID] or Game.GetCurrentGameTurn()~=packet.turn
    or turn~=packet.turn or not CoreIdle() then return nil end
  local here=UnitPlot(freshUnit)
  if not here or not CivilianMoveTarget(here,nextPlot,freshUnit,ctx.player) then return nil end
  return nextPlot
end


-- Scalar route proposals only. The original writer remains the permission boundary.
do
  local function Integer(v)
    return BaiqiPolicy.Number(v) and v>=0 and v<=2147483647 and v%1==0
  end
  local function Empty(ok,...)
    return ok and select("#",...)<=1 and (...)==nil
  end
  local function False(ok,...)
    return ok and select("#",...)==1 and (...)==false
  end
  function districtRoute.Enabled()
    return PlanningTime()~=nil
  end
  function districtRoute.Target(ctx,player,target,required,def,info,border)
    local ok,plot=pcall(function()
      if not target or not Integer(target.index) then return nil end
      local p=Map.GetPlotByIndex(target.index)
      if not p or p:GetIndex()~=target.index or not Revealed(p) then return nil end
      if target.x~=nil and (p:GetX()~=target.x or p:GetY()~=target.y) then return nil end
      if border then
        if BaiqiPolicy.GreatPersonActivationPlot(def.UnitType,info,ctx.player,p,visibility,Map) then return p end
        return nil
      end
      if not required or p:GetOwner()~=ctx.player or not Integer(target.cityID) then return nil end
      local city=player:GetCities():FindID(target.cityID)
      if not BaiqiPolicy.MatchesID(city,target.cityID) or city:GetOwner()~=ctx.player then return nil end
      local districts=city:GetDistricts()
      if districts:HasDistrict(required.Index,true)~=true then return nil end
      local count=0
      for _,district in districts:Members() do
        count=count+1;if count>128 then return nil end
        if district:GetType()==required.Index and district:GetX()==p:GetX() and district:GetY()==p:GetY() then return p end
      end
    end)
    return ok and plot or nil
  end
  function districtRoute.Fresh(job,plan)
    local ok,a,b,c,d,e=pcall(function()
      if type(job)~="table" or job.epoch~=settlementWorldEpoch or job.turn~=turn
        or Game.GetCurrentGameTurn()~=job.turn or districtPersonPlans[job.id]~=plan
        or plan.route~=job or not CoreIdle() then return nil end
      local ctx,player,state=PlayerContext()
      if not ctx or ctx.player~=job.owner or not BaiqiPolicy.Context(ctx) then return nil end
      local unit=player:GetUnits():FindID(job.id)
      if not BaiqiPolicy.MatchesID(unit,job.id) or unit:GetOwner()~=ctx.player
        or pendingUnits[job.id]~=nil or UnitKey(unit)~=job.key
        or not BaiqiPolicy.CanCivilian(ctx,UnitSnapshot(unit,state)) or unit:IsReadyToMove()~=true then return nil end
      local gp,info,required,class,def=DistrictPersonData(unit)
      if not gp or def.UnitType~=job.unitType or class.Index~=job.class
        or info.Index~=job.individual or gp:GetActionCharges()~=job.charges
        or (required and required.Index or nil)~=job.required
        or BaiqiPolicy.UnownedBorderGreatPerson(def.UnitType,info)~=job.border
        or DistrictPersonHeld(unit) then return nil end
      local queued=UnitManager.GetQueuedDestination
      if type(queued)~="function" or not Empty(pcall(queued,unit)) then return nil end
      local pending=unit.HasPendingOperations
      if pending~=nil and (type(pending)~="function" or not False(pcall(pending,unit))) then return nil end
      local target=districtRoute.Target(ctx,player,job,required,def,info,job.border)
      if not target or UnitIndex(unit)==job.index or not CoreIdle()
        or UnitKey(unit)~=job.key or job.epoch~=settlementWorldEpoch then return nil end
      return ctx,player,state,unit,target
    end)
    if ok then return a,b,c,d,e end
  end
  function districtRoute.Start(ctx,player,state,unit,plan,target,required,info,class,def,border)
    if not districtRoute.Enabled() then
      local step=PathStep(unit,target.plot,player,state)
      if step then
        plan.target=target.index;plan.targetCity=target.cityID
        return RequestCivilian(ctx,state,unit,"MOVE_TO",step),false,true
      end
      return false,false,false
    end
    if plan.route then return false,true,true end
    local job={id=unit:GetID(),owner=ctx.player,unitType=def.UnitType,class=class.Index,
      individual=info.Index,charges=unit:GetGreatPerson():GetActionCharges(),
      required=required and required.Index or nil,border=border,epoch=settlementWorldEpoch,
      turn=turn,key=UnitKey(unit),index=target.index,x=target.plot:GetX(),y=target.plot:GetY(),
      cityID=target.cityID,phase="query"}
    if not Integer(job.id) or not Integer(job.owner) or not Integer(job.class)
      or not Integer(job.individual) or not Integer(job.charges) or job.charges<1
      or not Integer(job.turn) or not Integer(job.index) or not Integer(job.x) or not Integer(job.y)
      or (job.required~=nil and not Integer(job.required)) then return false,false,false end
    plan.route=job
    if not districtRoute.Fresh(job,plan) then plan.route=nil;return false,false,false end
    plan.target=job.index;plan.targetCity=job.cityID
    return false,true,true
  end
  function districtRoute.Run(plan)
    local job=plan.route
    local ctx,player,state,unit,target=districtRoute.Fresh(job,plan)
    if not ctx then plan.route=nil;return false,false end
    local function Reject()
      if plan.route==job then plan.route=nil end
      plan.blocked[job.index]="route"
      if plan.target==job.index then plan.target=nil;plan.targetCity=nil end
      return true,false
    end
    if job.phase=="query" then
      local query=UnitManager.GetMoveToPathEx
      if type(query)~="function" then return Reject() end
      local ok,path=pcall(query,unit,job.index)
      if not ok or UnitManager.GetMoveToPathEx~=query or type(path)~="table" or type(path.plots)~="table" then return Reject() end
      local copied,count={},0
      for key in pairs(path.plots) do
        count=count+1
        if count>C.pathLimit or not Integer(key) or key<1 or key>C.pathLimit then return Reject() end
      end
      if count<2 or count>C.pathLimit then return Reject() end
      for i=1,count do
        local index=path.plots[i]
        if not Integer(index) then return Reject() end
        copied[i]=index
      end
      if copied[1]~=UnitIndex(unit) or copied[count]~=job.index or not districtRoute.Fresh(job,plan) then return Reject() end
      job.path=copied;job.phase="validate"
      return true,false
    end
    if job.phase~="validate" or type(job.path)~="table" then return Reject() end
    local count=#job.path
    if count<2 or count>C.pathLimit or job.path[1]~=UnitIndex(unit) or job.path[count]~=job.index then return Reject() end
    local cache,previous={}
    for i=1,count do
      local index=job.path[i]
      if not Integer(index) then return Reject() end
      local plot=Map.GetPlotByIndex(index)
      if not plot or plot:GetIndex()~=index or not Revealed(plot) or not Safe(plot,player,cache)
        or (plot:GetOwner()~=-1 and plot:GetOwner()~=ctx.player)
        or (previous and Map.GetPlotDistance(previous:GetX(),previous:GetY(),plot:GetX(),plot:GetY())~=1) then return Reject() end
      previous=plot
    end
    ctx,player,state,unit,target=districtRoute.Fresh(job,plan)
    if not ctx then return Reject() end
    local step=Map.GetPlotByIndex(job.path[2]);local here=UnitPlot(unit)
    if not step or step:GetIndex()~=job.path[2] or not here
      or Map.GetPlotDistance(here:GetX(),here:GetY(),step:GetX(),step:GetY())~=1 then return Reject() end
    -- No positive route-safety fact survives another callback before this write.
    plan.route=nil;unitEvaluated[job.key]=true
    return true,RequestCivilian(ctx,state,unit,"MOVE_TO",step)
  end
end

local function BuilderTargets(ctx,player,unit)
  local ok,result=pcall(function()
    local targets,seen={},{}
    local def=BuilderAdjacentDefinition()
    local function Add(plot,adjacent)
      if not plot or not Revealed(plot) or plot:GetOwner()~=ctx.player then return end
      local index=plot:GetIndex()
      if not GeometryInteger(index) or seen[index] then return end
      if adjacent and (visibility:IsVisible(plot:GetX(),plot:GetY())~=true
        or plot:IsImpassable() or plot:IsWater() or index==UnitIndex(unit)) then return end
      seen[index]=true
      targets[#targets+1]={plot=plot,index=index,distance=Map.GetPlotDistance(unit:GetX(),unit:GetY(),plot:GetX(),plot:GetY())}
    end
    local cities,total=0,0
    for _,city in player:GetCities():Members() do
      cities=cities+1;if cities>128 then return {} end
      local ai=city:GetCityAI()
      if ai then
        local n=0
        for _,rec in pairs(ai:GetImprovementRecommendationsForBuilder(unit:GetComponentID()) or {}) do
          n=n+1;total=total+1;if n>128 or total>1024 then return {} end
          if type(rec)=="table" and GeometryInteger(rec.ImprovementLocation) then
            local plot=Map.GetPlotByIndex(rec.ImprovementLocation)
            if def and rec.ImprovementHash==def.hash then
              if plot and Revealed(plot) and plot:GetOwner()==ctx.player
                and visibility:IsVisible(plot:GetX(),plot:GetY())==true
                and plot:GetImprovementType()==-1 and plot:GetDistrictType()==-1
                and type(Map.GetAdjacentPlot)=="function"
                and Map.GetPlotDistance(unit:GetX(),unit:GetY(),plot:GetX(),plot:GetY())~=1 then
                for direction=0,5 do Add(Map.GetAdjacentPlot(plot:GetX(),plot:GetY(),direction),true) end
              end
            else Add(plot,false) end
          end
        end
      end
    end
    table.sort(targets,function(a,b) if a.distance~=b.distance then return a.distance<b.distance end return a.index<b.index end)
    return targets
  end)
  return ok and result or {}
end

local function BuilderRouteValid(ctx,state,unit,search)
  local row=unit and GameInfo.Units[unit:GetUnitType()]
  return search and row and row.UnitType=="UNIT_BUILDER" and search.player==ctx.player
    and search.turn==turn and turn==Game.GetCurrentGameTurn()
    and UnitKey(unit)==search.key and not pendingUnits[unit:GetID()]
    and BaiqiPolicy.CanCivilian(ctx,UnitSnapshot(unit,state)) and CoreIdle()
end

-- Failed planning goals are deferred only for this unit's current turn.
-- These scalar indices never authorize a move or cache a safety decision.
local function BuilderGoalRejected(ctx,unit,index)
  local entry=builderRejectedGoals[unit:GetID()]
  return entry~=nil and entry.player==ctx.player and entry.turn==turn
    and entry.goals[index]==true
end

local function RejectBuilderGoal(ctx,state,unit,search,index)
  if not BaiqiPolicy.Number(index) or index<0 or index%1~=0 then return end
  local latest,player,actualState=PlayerContext()
  if not latest or latest.player~=ctx.player then return end
  local id=unit:GetID()
  local fresh=player:GetUnits():FindID(id)
  if not BaiqiPolicy.MatchesID(fresh,id) or fresh:GetOwner()~=latest.player
    or not BuilderRouteValid(latest,actualState,fresh,search) then return end
  local plot=Map.GetPlotByIndex(index)
  if not plot or plot:GetIndex()~=index or not Revealed(plot) or plot:GetOwner()~=latest.player then return end
  local entry=builderRejectedGoals[id]
  if not entry or entry.player~=latest.player or entry.turn~=turn then
    entry={player=latest.player,turn=turn,goals={}};builderRejectedGoals[id]=entry
  end
  -- At most the valid revealed owned map plots per live builder this turn.
  entry.goals[index]=true
end

local function WaitBuilderRoute(ctx,player,state,unit,search)
  builderSearches[unit:GetID()]=nil
  if not BuilderRouteValid(ctx,state,unit,search) then return false,false end
  unitEvaluated[UnitKey(unit)]=true
  if settlementCache.YieldBuilder(ctx,player,state,unit)then return true,false end
  if unitEvaluated[UnitKey(unit)]=="native_wait"then return false,false end
  local here=UnitPlot(unit)
  if here and RequestCivilian(ctx,state,unit,"SKIP_TURN",here) then return true,false end
  if ClearCivilianOverlap(ctx,player,state,unit) then return true,false end
  return false,false
end

local function BuilderRouteTarget(targets,search,ctx,unit)
  for _,target in ipairs(targets) do
    if not BuilderGoalRejected(ctx,unit,target.index)
      and (target.index==search.activeTarget or not search.tested[target.index]) then return target end
  end
end

local function AdvanceBuilderRoute(ctx,player,state,unit,search)
  local id=unit:GetID()
  if not BuilderRouteValid(ctx,state,unit,search) then builderSearches[id]=nil;return false,false end
  if BuilderBudgetExpired(planningStarted,C.builderSliceSeconds) then return false,true end
  if search.phase=="query" then
    local targets=BuilderTargets(ctx,player,unit)
    local target=BuilderRouteTarget(targets,search,ctx,unit)
    if not target then return WaitBuilderRoute(ctx,player,state,unit,search) end
    if search.activeTarget and search.activeTarget~=target.index then search.tested[search.activeTarget]=nil end
    search.activeTarget=target.index
    search.tested[target.index]=true
    search.hasMore=false
    for _,other in ipairs(targets) do if not search.tested[other.index] and not BuilderGoalRejected(ctx,unit,other.index) then search.hasMore=true;break end end
    local packet=PrepareBuilderPathPacket(ctx,player,state,unit,target.plot)
    if not packet then
      RejectBuilderGoal(ctx,state,unit,search,target.index)
      search.activeTarget=nil
      if search.hasMore then return false,true end
      return WaitBuilderRoute(ctx,player,state,unit,search)
    end
    search.packet=packet;search.phase="validate"
    if BuilderBudgetExpired(planningStarted,C.builderSliceSeconds) then return false,true end
  end
  if search.phase=="validate" then
    local step=ValidateBuilderPathPacket(ctx,player,state,unit,search.packet)
    if not step then
      RejectBuilderGoal(ctx,state,unit,search,search.activeTarget)
      search.packet=nil;search.activeTarget=nil;search.phase="query"
      if search.hasMore then return false,true end
      return WaitBuilderRoute(ctx,player,state,unit,search)
    end
    search.nextIndex=step:GetIndex();search.phase="write"
    if BuilderBudgetExpired(planningStarted,C.builderSliceSeconds) then return false,true end
  end
  if search.phase=="write" then
    local target=BuilderRouteTarget(BuilderTargets(ctx,player,unit),search,ctx,unit)
    if not target then return WaitBuilderRoute(ctx,player,state,unit,search) end
    if target.index~=search.activeTarget then
      search.tested[search.activeTarget]=nil;search.activeTarget=target.index
      search.packet=nil;search.phase="query";return false,true
    end
    local packet=search.packet
    local step=Map.GetPlotByIndex(search.nextIndex)
    if not step or not packet or packet.unitID~=id or packet.key~=search.key
      or packet.turn~=turn or packet.player~=ctx.player or not BuilderRouteValid(ctx,state,unit,search) then
      builderSearches[id]=nil;return false,false
    end
    -- The packet is a suggestion. The original writer rechecks current safety,
    -- adjacency, identity and native qualification; a rejected write ends search.
    builderSearches[id]=nil
    unitEvaluated[UnitKey(unit)]=true
    if RequestCivilian(ctx,state,unit,"MOVE_TO",step) then return true,false end
    return WaitBuilderRoute(ctx,player,state,unit,search)
  end
  builderSearches[id]=nil
  return false,false
end

local function ProcessBuilder(ctx, player, state, unit)
  local current=builderSearches[unit:GetID()]
  if current and current.phase then return AdvanceBuilderRoute(ctx,player,state,unit,current) end
  local here = UnitPlot(unit)
  if here==nil then return false end
  if here:GetOwner() == ctx.player and Safe(here, player) then
    if here:IsImprovementPillaged() and UnitManager.CanStartOperation(unit, UnitOperationTypes.REPAIR) then
      return RequestCivilian(ctx, state, unit, "REPAIR", here)
    end
    local adjacent=BuilderAdjacentCandidates(unit)
    if adjacent and adjacent[1] then
      return RequestCivilian(ctx,state,unit,"BUILD_IMPROVEMENT_ADJACENT",adjacent[1].plot,adjacent[1].hash)
    end
    local best
    if here:GetImprovementType() == -1 then
      local candidates=BuilderImprovementCandidates(unit,here)
      if candidates then
        for _,row in ipairs(candidates) do
          local params={[UnitOperationTypes.PARAM_X]=unit:GetX(),[UnitOperationTypes.PARAM_Y]=unit:GetY(),
            [UnitOperationTypes.PARAM_IMPROVEMENT_TYPE]=row.Hash}
          if UnitManager.CanStartOperation(unit,UnitOperationTypes.BUILD_IMPROVEMENT,nil,params)==true then best=row;break end
        end
      else
        for row in GameInfo.Improvements() do
          local params = {[UnitOperationTypes.PARAM_X]=unit:GetX(), [UnitOperationTypes.PARAM_Y]=unit:GetY(),
            [UnitOperationTypes.PARAM_IMPROVEMENT_TYPE]=row.Hash}
          if UnitManager.CanStartOperation(unit, UnitOperationTypes.BUILD_IMPROVEMENT, nil, params) == true
            and (best == nil or row.Index < best.Index) then best=row end
        end
      end
    end
    if best then return RequestCivilian(ctx, state, unit, "BUILD_IMPROVEMENT", here, best.Hash) end
  end
  local targets=BuilderTargets(ctx,player,unit)
  local id,key=unit:GetID(),UnitKey(unit)
  local search=builderSearches[id]
  if not search or search.player~=ctx.player or search.turn~=turn or search.key~=key then
    search={player=ctx.player,turn=turn,key=key,tested={}}
    builderSearches[id]=search
  end
  for i,target in ipairs(targets) do
    if not search.tested[target.index] and not BuilderGoalRejected(ctx,unit,target.index) then
      search.tested[target.index]=true
      if planningStarted~=nil then
        search.activeTarget=target.index;search.phase="query"
        return AdvanceBuilderRoute(ctx,player,state,unit,search)
      end
      local step=PathStep(unit,target.plot,player,state)
      if step then
        builderSearches[id]=nil
        return RequestCivilian(ctx,state,unit,"MOVE_TO",step)
      end
      RejectBuilderGoal(ctx,state,unit,search,target.index)
      -- One candidate (at most one native path) per planner invocation. Keep
      -- only failed target indices; rebuild and rank current hints on resume.
      for j=i+1,#targets do
        if not search.tested[targets[j].index] and not BuilderGoalRejected(ctx,unit,targets[j].index) then return false,true end
      end
      break
    end
  end
  builderSearches[id]=nil
  if settlementCache.YieldBuilder(ctx,player,state,unit)then return true end
  return false
end

local function Military(row) return (row.Combat or 0) > 0 or (row.RangedCombat or 0) > 0 or row.FormationClass == "FORMATION_CLASS_SUPPORT" end

-- This only ranks new domestic routes. The estimate cannot qualify a route
-- or change an active one. Keep the original order if any score is unknown.
local function TradeFoodScores(choices,origin,pid)
  if not origin or #choices<2 or #choices>16 then return nil end
  local ok,scores=pcall(function()
    local growth=origin:GetGrowth()
    local surplus,stock=growth:GetFoodSurplus(),growth:GetFood()
    if not BaiqiPolicy.Number(surplus) or surplus>0 or surplus< -1000000
      or not BaiqiPolicy.Number(stock) or stock<0 or stock>=2 then return nil end
    local food=YieldTypes.FOOD
    if not GeometryInteger(food) or food>=64 then return nil end
    local manager=Game.GetTradeManager()
    local from=origin:GetID()
    local function component(method,to)
      local yields=method(manager,pid,from,pid,to)
      local value=type(yields)=="table" and yields[food+1]
      if BaiqiPolicy.Number(value) and math.abs(value)<=1000000 then return value end
    end
    local values={}
    for _,choice in ipairs(choices) do
      local to=choice.id
      local base=component(manager.CalculateOriginYieldsFromPotentialRoute,to)
      local path=component(manager.CalculateOriginYieldsFromPath,to)
      local modifiers=component(manager.CalculateOriginYieldsFromModifiers,to)
      if base==nil or path==nil or modifiers==nil then return nil end
      values[to]=base+path+modifiers
    end
    return values
  end)
  return ok and scores or nil
end

local function ProcessTrader(ctx,player,state,unit)
  local choices,origin={},nil
  for _,city in player:GetCities():Members() do
    local plot=Map.GetPlot(city:GetX(),city:GetY())
    local route=TradePath(ctx,player,unit,plot)
    if route then
      origin=origin or route.origin
      choices[#choices+1]={id=city:GetID(),x=city:GetX(),y=city:GetY(),length=route.length}
    end
  end
  local food=TradeFoodScores(choices,origin,ctx.player)
  table.sort(choices,function(a,b)
    if food and food[a.id]~=food[b.id] then return food[a.id]>food[b.id] end
    if a.length~=b.length then return a.length<b.length end
    return a.id<b.id
  end)
  for _,choice in ipairs(choices) do
    local plot=Map.GetPlot(choice.x,choice.y)
    local params,origin,dest=TradeParams(ctx,player,unit,plot)
    if params and dest:GetID()==choice.id then
      -- Unsafe/unavailable planning alternatives may fall back. Once a valid
      -- choice reaches the command boundary, a rejected write ends this search.
      return RequestCivilian(ctx,state,unit,"MAKE_TRADE_ROUTE",plot)
    end
  end
  Reason("trader:"..unit:GetID(),"商人等待有容量、已探明且安全的国内商路")
  return false
end

local function QueueHeadSignature(q,index)
  if not q.GetAt or q:GetSize()==0 then return nil end
  local e=q:GetAt(index or 0)
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


-- A flooded prerequisite can strand an unfinished building behind a zero
-- current hash. Preserve that sole entry while prepending ordinary legal work.
-- Unknown or normally active queues never authorize this exception.
local function BlockedIdleHead(city,q)
  local ok,signature,work=pcall(function()
    local function Integer(n,lo)
      return BaiqiPolicy.Number(n) and n%1==0 and n>=lo and n<=2147483647
    end
    local mode=CityOperationTypes.VALUE_PREPEND
    if not Integer(mode,-2147483648) or mode==CityOperationTypes.VALUE_APPEND
      or mode==CityOperationTypes.VALUE_REPLACE_AT or q:GetSize()~=1
      or q:GetCurrentProductionTypeHash()~=0 then return nil end
    local sig,e=QueueHeadSignature(q)

    if e and e.ProjectType~=nil then
      if not Integer(e.ProjectType,0) or e.BuildingType~=nil or e.DistrictType~=nil or e.UnitType~=nil
        or not Integer(e.Directive,0) or not Integer(e.Modifiers,0)
        or (e.Location~=nil and type(e.Location)~="table") then return nil end
      local directive=CityProductionDirectives and CityProductionDirectives.PROJECT
      if not Integer(directive,0) or e.Directive~=directive then return nil end
      local location=e.Location or {}
      if (location.x~=nil and not Integer(location.x,-2147483648))
        or (location.y~=nil and not Integer(location.y,-2147483648)) then return nil end
      local row=GameInfo.Projects[e.ProjectType]
      if not row or row.Index~=e.ProjectType or not Integer(row.Hash,-2147483648) or row.Hash==0
        or type(row.ProjectType)~="string" or row.ProjectType==""
        or type(row.PrereqDistrict)~="string" or row.PrereqDistrict=="" then return nil end
      local district=GameInfo.Districts[row.PrereqDistrict]
      if not district or district.DistrictType~=row.PrereqDistrict or not Integer(district.Index,0)
        or not Integer(district.Hash,-2147483648) or district.Hash==0 then return nil end
      local districts=city:GetDistricts()
      if districts:HasDistrict(district.Index,true)~=true or districts:IsPillaged(district.Index)~=true
        or q:CanProduce(row.Hash,true)~=true or q:CanProduce(row.Hash,false,true)~=false then return nil end
      local progress,cost=q:GetProjectProgress(row.Index),q:GetProjectCost(row.Index)
      if not BaiqiPolicy.Number(progress) or progress<=0 or not BaiqiPolicy.Number(cost)
        or cost<=progress then return nil end
      return sig,{kind="project",projectIndex=row.Index,hash=row.Hash,projectType=row.ProjectType,
        progress=progress,cost=cost,prereqIndex=district.Index,prereqHash=district.Hash,
        prereqType=district.DistrictType}
    end
    if not e or not Integer(e.BuildingType,0) or e.DistrictType~=nil
      or e.UnitType~=nil or e.ProjectType~=nil or not Integer(e.Directive,0)
      or not Integer(e.Modifiers,0) or (e.Location~=nil and type(e.Location)~="table") then return nil end
    local location=e.Location or {}
    if (location.x~=nil and not Integer(location.x,-2147483648))
      or (location.y~=nil and not Integer(location.y,-2147483648)) then return nil end
    local row=GameInfo.Buildings[e.BuildingType]
    if not row or row.Index~=e.BuildingType or not Integer(row.Hash,-2147483648)
      or type(row.PrereqDistrict)~="string" or row.PrereqDistrict=="" then return nil end
    local district=GameInfo.Districts[row.PrereqDistrict]
    if not district or district.DistrictType~=row.PrereqDistrict or not Integer(district.Index,0) then return nil end
    local buildings=city:GetBuildings()
    local owned=buildings:HasBuilding(row.Index)
    if owned==true then
      if row.Hash==0 or type(row.BuildingType)~="string" or row.BuildingType==""
        or not Integer(district.Hash,-2147483648) or district.Hash==0
        or buildings:IsPillaged(row.Index)~=true then return nil end
      local districts=city:GetDistricts()
      if districts:HasDistrict(district.Index,true)~=true or districts:IsPillaged(district.Index)~=true
        or q:CanProduce(row.Hash,true)~=true or q:CanProduce(row.Hash,false,true)~=false then return nil end
      local progress,cost=q:GetBuildingProgress(row.Index),q:GetBuildingCost(row.Index)
      if not BaiqiPolicy.Number(progress) or progress<=0 or not BaiqiPolicy.Number(cost)
        or cost<=progress then return nil end
      return sig,{kind="building_repair",buildingIndex=row.Index,hash=row.Hash,buildingType=row.BuildingType,
        progress=progress,cost=cost,prereqIndex=district.Index,prereqHash=district.Hash,
        prereqType=district.DistrictType}
    end
    if owned~=false then return nil end
    local districts=city:GetDistricts()
    if districts:HasDistrict(district.Index,true)~=true or districts:IsPillaged(district.Index)~=true
      or q:CanProduce(row.Hash,true)~=true or q:CanProduce(row.Hash,false,true)~=false then return nil end
    local progress,cost=q:GetBuildingProgress(row.Index),q:GetBuildingCost(row.Index)
    if not BaiqiPolicy.Number(progress) or progress<0 or not BaiqiPolicy.Number(cost)
      or cost<=progress then return nil end
    return sig,{buildingIndex=row.Index,hash=row.Hash,progress=progress}
  end)
  if ok then return signature,work end
end

local function Economy(player)
  local s = {cities=player:GetCities():GetCount(), army=0, builders=0, settlers=0,
    militaryRoles={recon=0,frontline=0,ranged=0,siege=0,support=0,naval=0,air=0},
    traders=0,queuedTraders=0,tradeCapacity=player.GetTrade and player:GetTrade():GetOutgoingRouteCapacity() or 0,
    queuedArmy=0, queuedBuilders=0, queuedSettlers=0, reservedSettlers=0, retainedSettlers=0, committedMaintenance=0,
    gold=player:GetTreasury():GetGoldBalance(), netGold=player:GetTreasury():GetGoldYield()-player:GetTreasury():GetTotalMaintenance()}
  local function CountMilitary(row)
    local role=BaiqiPlanner.MilitaryRole(row)
    if role then s.militaryRoles[role]=s.militaryRoles[role]+1 end
  end
  for _, unit in player:GetUnits():Members() do
    local row=GameInfo.Units[unit:GetUnitType()]
    if row.UnitType=="UNIT_BUILDER" then s.builders=s.builders+1
    elseif row.UnitType=="UNIT_SETTLER" then
      s.settlers=s.settlers+1
      if settlementCache.IsRetained(player,unit) then s.retainedSettlers=s.retainedSettlers+1 end
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
    local represented={}
    local function Commit(row,kind)
      if not row then return end
      Commitment(row,kind)
      represented[kind..":"..tostring(row.Hash)]=true
    end
    for i=0,q:GetSize()-1 do
      local entry=q:GetAt(i)
      local row=entry and entry.UnitType and GameInfo.Units[entry.UnitType]
      if i==0 and completedHead then -- Already owned asset; no new commitment.
      elseif row then Commit(row,"unit")
      elseif entry and entry.BuildingType then Commit(GameInfo.Buildings[entry.BuildingType],"building")
      elseif entry and entry.DistrictType then Commit(GameInfo.Districts[entry.DistrictType],"district") end
    end
    -- Native current production and queue entries can become visible separately.
    local current=q:GetCurrentProductionTypeHash()
    local active=current~=0 and GameInfo.Units[current]
    if active and not represented["unit:"..tostring(active.Hash)] then Commit(active,"unit") end
    local pending=pendingCities[city:GetID()]
    if pending and not represented[pending.kind..":"..tostring(pending.hash)] then
      local tables={unit=GameInfo.Units,building=GameInfo.Buildings,district=GameInfo.Districts,project=GameInfo.Projects}
      local rows=tables[pending.kind]
      Commit(rows and rows[pending.hash],pending.kind)
    end
    -- An acknowledged request remains a same-turn commitment even if a later
    -- native read briefly shows the old head. Invalidation must not erase it.
    for hash in pairs(submittedUnits[city:GetID()] or {}) do
      if not represented["unit:"..tostring(hash)] then Commit(GameInfo.Units[hash],"unit") end
    end
  end
  return s
end

local buildingPriority = {BUILDING_GRANARY=110,BUILDING_MONUMENT=100,BUILDING_WATER_MILL=95,
  BUILDING_WORKSHOP=90,BUILDING_MARKET=85,BUILDING_LIBRARY=80,BUILDING_BARRACKS=75,BUILDING_LIGHTHOUSE=85,BUILDING_MUSEUM_ARTIFACT=78,BUILDING_SHRINE=91}
local districtPriority = {DISTRICT_INDUSTRIAL_ZONE=72,DISTRICT_COMMERCIAL_HUB=70,DISTRICT_HARBOR=70,
  DISTRICT_CAMPUS=68,DISTRICT_ENCAMPMENT=65,DISTRICT_AQUEDUCT=60,DISTRICT_NEIGHBORHOOD=55}

-- An opportunity to start religious infrastructure is a ranking hint, never a
-- Prophet recruitment/founding permission. Unknown reads keep the normal score.
local function FirstHolySiteWanted(ctx,player)
  local ok,wanted=pcall(function()
    local function Integer(value,max)
      return BaiqiPolicy.Number(value) and value>=0 and value<=max and value%1==0
    end
    local function DenseSize(list,max)
      if type(list)~="table" or getmetatable(list)~=nil then return nil end
      local n,highest=0,0
      for key in pairs(list) do
        n=n+1
        if n>max or not Integer(key,max) or key<1 then return nil end
        highest=math.max(highest,key)
      end
      if n~=highest then return nil end
      return n
    end
    if not BaiqiPolicy.Context(ctx) or Players[ctx.player]~=player
      or Game.GetCurrentGameTurn()~=turn then return false end
    local row=GameInfo.Districts.DISTRICT_HOLY_SITE
    if not row or row.DistrictType~="DISTRICT_HOLY_SITE" or not Integer(row.Index,2147483647)
      or not BaiqiPolicy.Number(row.Hash) or row.Hash%1~=0 then return false end
    local religion=player:GetReligion()
    if religion:GetReligionTypeCreated()~=-1 or religion:GetNumBeliefsEarned()~=0 then return false end
    local held=religion:HasReligiousFoundingUnit()
    if type(held)~="boolean" then return false end
    local cities=player:GetCities()
    local count=cities:GetCount()
    if not Integer(count,256) or count==0 then return false end
    local seen,n={},0
    for _,city in cities:Members() do
      n=n+1
      local id=city:GetID()
      if n>count or not Integer(id,2147483647) or seen[id] or city:GetOwner()~=ctx.player
        or not BaiqiPolicy.MatchesID(cities:FindID(id),id) then return false end
      seen[id]=true
      local q=city:GetBuildQueue()
      local exists=city:GetDistricts():HasDistrict(row.Index,true)
      local placed=q:HasBeenPlaced(row.Hash)
      if type(exists)~="boolean" or type(placed)~="boolean" or exists or placed then return false end
      local current=q:GetCurrentProductionTypeHash()
      if not BaiqiPolicy.Number(current) or current%1~=0 or current==row.Hash then return false end
      local size=q:GetSize()
      if not Integer(size,64) then return false end
      for i=0,size-1 do
        local entry=q:GetAt(i)
        if type(entry)~="table" then return false end
        if entry.DistrictType~=nil then
          local actual=GameInfo.Districts[entry.DistrictType]
          if not actual or actual.DistrictType=="DISTRICT_HOLY_SITE" then return false end
        end
      end
    end
    if n~=count then return false end
    n=0
    for _,pending in pairs(pendingCities) do
      n=n+1
      if n>256 then return false end
      if pending.kind=="district" then
        local actual=GameInfo.Districts[pending.hash]
        if not actual or actual.DistrictType=="DISTRICT_HOLY_SITE" then return false end
      end
    end
    if not held then
      local class=GameInfo.GreatPersonClasses.GREAT_PERSON_CLASS_PROPHET
      if not class or class.GreatPersonClassType~="GREAT_PERSON_CLASS_PROPHET"
        or not Integer(class.Index,2147483647) then return false end
      local timeline=Game.GetGreatPeople():GetTimeline()
      local size=DenseSize(timeline,128)
      if size==nil then return false end
      local unclaimed,individuals=false,{}
      for i=1,size do
        local entry=timeline[i]
        if type(entry)~="table" or getmetatable(entry)~=nil
          or not Integer(entry.Class,2147483647) then return false end
        if entry.Class==class.Index then
          local id=entry.Individual
          local definition=Integer(id,2147483647) and GameInfo.GreatPersonIndividuals[id]
          if not definition or definition.Index~=id or individuals[id]
            or definition.GreatPersonClassType~="GREAT_PERSON_CLASS_PROPHET"
            or (entry.Claimant~=nil and not Integer(entry.Claimant,2147483647)) then return false end
          individuals[id]=true
          if entry.Claimant==nil then unclaimed=true end
        end
      end
      if not unclaimed then return false end
    end
    local fresh,freshPlayer=PlayerContext()
    return BaiqiPolicy.Context(fresh) and fresh.player==ctx.player and freshPlayer==player
      and Game.GetCurrentGameTurn()==turn and CoreIdle()
  end)
  return ok and wanted==true
end

local function BuildParams(candidate,completedHead,blockedHead)
  local params = {[CityOperationTypes.PARAM_INSERT_MODE]=blockedHead and CityOperationTypes.VALUE_PREPEND
    or (completedHead and CityOperationTypes.VALUE_REPLACE_AT or CityOperationTypes.VALUE_APPEND)}
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

local function QueueReady(city,q,completedHead,blockedHead,blockedWork)
  if blockedHead then
    if completedHead then return false end
    local current,work=BlockedIdleHead(city,q)
    if current~=blockedHead or not CoreIdle() then return false end
    if (work and work.kind=="project") or (blockedWork and blockedWork.kind=="project") then
      if not work or not blockedWork or work.kind~="project" or blockedWork.kind~="project" then return false end
      for _,key in ipairs({"projectIndex","hash","projectType","progress","cost","prereqIndex","prereqHash","prereqType"}) do
        if work[key]~=blockedWork[key] then return false end
      end
    elseif (work and work.kind=="building_repair") or (blockedWork and blockedWork.kind=="building_repair") then
      if not work or not blockedWork or work.kind~="building_repair" or blockedWork.kind~="building_repair" then return false end
      for _,key in ipairs({"buildingIndex","hash","buildingType","progress","cost","prereqIndex","prereqHash","prereqType"}) do
        if work[key]~=blockedWork[key] then return false end
      end
    end
    return true
  end
  if completedHead then
    return q:GetSize()==1 and CompletedIdleHead(city,q)==completedHead and CoreIdle()
  end
  return q:GetSize()==0 and q:GetCurrentProductionTypeHash()==0 and CoreIdle()
end

-- Fresh supply eligibility only; actual production is still the city's sole writer.
local function ArchaeologistDemand(ctx,player,city)
  local ok,needed=pcall(function()
    local function Integer(value,max)
      return BaiqiPolicy.Number(value) and value>=0 and value<=max and value%1==0
    end
    if not BaiqiPolicy.Context(ctx) then return false end
    local cityID=city:GetID()
    local owned=player:GetCities():FindID(cityID)
    if not Integer(cityID,2147483647) or not BaiqiPolicy.MatchesID(owned,cityID)
      or city:GetOwner()~=ctx.player or owned:GetOwner()~=ctx.player then return false end
    local row=GameInfo.Buildings.BUILDING_MUSEUM_ARTIFACT
    if not row or row.BuildingType~="BUILDING_MUSEUM_ARTIFACT" or not Integer(row.Index,2147483647) then return false end
    local buildings=owned:GetBuildings()
    if buildings:HasBuilding(row.Index)~=true or buildings:IsPillaged(row.Index)~=false then return false end
    local slots=buildings:GetNumGreatWorkSlots(row.Index)
    if not Integer(slots,64) or slots<1 then return false end
    local empty,works=false,{}
    for slot=0,slots-1 do
      local kind=buildings:GetGreatWorkSlotType(row.Index,slot)
      local definition=Integer(kind,2147483647) and GameInfo.GreatWorkSlotTypes[kind]
      if not definition or definition.GreatWorkSlotType~="GREATWORKSLOT_ARTIFACT" then return false end
      local work=buildings:GetGreatWorkInSlot(row.Index,slot)
      if work==-1 then empty=true
      elseif not Integer(work,2147483647) or works[work] then return false
      else works[work]=true end
    end
    if not empty then return false end
    local unitCount=0
    for _,unit in player:GetUnits():Members() do
      unitCount=unitCount+1
      if unitCount>4096 or not Integer(unit:GetID(),2147483647) or unit:GetOwner()~=ctx.player then return false end
      local definition=GameInfo.Units[unit:GetUnitType()]
      if not definition then return false end
      if definition.UnitType=="UNIT_ARCHAEOLOGIST" then
        local home=unit:GetArchaeologyHomeCity()
        if not Integer(home,2147483647) or home==cityID then return false end
      end
    end
    local q=owned:GetBuildQueue()
    local size=q:GetSize()
    if not Integer(size,64) or q:GetCurrentProductionTypeHash()~=0 then return false end
    for i=0,size-1 do
      local entry=q:GetAt(i)
      if type(entry)~="table" then return false end
      if entry.UnitType~=nil then
        local definition=GameInfo.Units[entry.UnitType]
        if not definition or definition.UnitType=="UNIT_ARCHAEOLOGIST" then return false end
      end
    end
    local pending=pendingCities[cityID]
    if pending and pending.kind=="unit" then
      local definition=GameInfo.Units[pending.hash]
      if not definition or definition.UnitType=="UNIT_ARCHAEOLOGIST" then return false end
    end
    for hash in pairs(submittedUnits[cityID] or {}) do
      local definition=GameInfo.Units[hash]
      if not definition or definition.UnitType=="UNIT_ARCHAEOLOGIST" then return false end
    end
    local checked=0
    for _,ownerCity in player:GetCities():Members() do
      if ownerCity:GetOwner()~=ctx.player then return false end
      local plots=Map.GetCityPlots():GetPurchasedPlots(ownerCity)
      if type(plots)~="table" then return false end
      for _,index in pairs(plots) do
        checked=checked+1
        if checked>512 or not Integer(index,2147483647) then return false end
        local plot=Map.GetPlotByIndex(index)
        if not plot or plot:GetIndex()~=index then return false end
        if Revealed(plot) and visibility:IsVisible(plot:GetX(),plot:GetY())==true and plot:GetOwner()==ctx.player then
          local resource=plot:GetResourceType()
          if resource~=-1 then
            local definition=GameInfo.Resources[resource]
            if not definition then return false end
            if (definition.ResourceType=="RESOURCE_ANTIQUITY_SITE" or definition.ResourceType=="RESOURCE_SHIPWRECK")
              and Safe(plot,player) then return true end
          end
        end
      end
    end
    return false
  end)
  return ok and needed==true
end

-- Keep ordinary project legality separate from a temporary recruitment goal.
-- This helper supplies a score only; the existing city writer owns the request.
local function PrayerProjectWanted(ctx,player,city)
  local ok,wanted=pcall(function()
    local function Integer(value,max)
      return BaiqiPolicy.Number(value) and value>=0 and value<=max and value%1==0
    end
    local function DenseSize(list)
      if type(list)~="table" or getmetatable(list)~=nil then return nil end
      local count,highest=0,0
      for key in pairs(list) do
        count=count+1
        if count>128 or not Integer(key,128) or key<1 then return nil end
        highest=math.max(highest,key)
      end
      if count~=highest then return nil end
      return count
    end
    if not BaiqiPolicy.Context(ctx) or Players[ctx.player]~=player
      or Game.GetCurrentGameTurn()~=turn then return false end
    local holy=GameInfo.Districts.DISTRICT_HOLY_SITE
    local project=GameInfo.Projects.PROJECT_ENHANCE_DISTRICT_HOLY_SITE
    if not holy or holy.DistrictType~="DISTRICT_HOLY_SITE" or not Integer(holy.Index,2147483647)
      or not project or project.ProjectType~="PROJECT_ENHANCE_DISTRICT_HOLY_SITE"
      or project.PrereqDistrict~="DISTRICT_HOLY_SITE" or not Integer(project.Index,2147483647)
      or not BaiqiPolicy.Number(project.Hash) or project.Hash%1~=0 then return false end
    local cityID=city:GetID()
    local cities=player:GetCities()
    local owned=cities:FindID(cityID)
    if not Integer(cityID,2147483647) or not BaiqiPolicy.MatchesID(owned,cityID)
      or city:GetOwner()~=ctx.player or owned:GetOwner()~=ctx.player then return false end
    local districts=owned:GetDistricts()
    if districts:HasDistrict(holy.Index,true)~=true or districts:IsPillaged(holy.Index)~=false then return false end
    local religion=player:GetReligion()
    if religion:GetReligionTypeCreated()~=-1 or religion:GetNumBeliefsEarned()~=0
      or religion:HasReligiousFoundingUnit()~=false then return false end
    local class=GameInfo.GreatPersonClasses.GREAT_PERSON_CLASS_PROPHET
    if not class or class.GreatPersonClassType~="GREAT_PERSON_CLASS_PROPHET"
      or not Integer(class.Index,2147483647) then return false end
    local people=Game.GetGreatPeople()
    local timeline=people:GetTimeline()
    local size=DenseSize(timeline)
    if size==nil then return false end
    local seen,unclaimed={},{}
    for i=1,size do
      local entry=timeline[i]
      if type(entry)~="table" or getmetatable(entry)~=nil
        or not Integer(entry.Class,2147483647) then return false end
      if entry.Class==class.Index then
        local id=entry.Individual
        local definition=Integer(id,2147483647) and GameInfo.GreatPersonIndividuals[id]
        if not definition or definition.Index~=id or seen[id]
          or definition.GreatPersonClassType~="GREAT_PERSON_CLASS_PROPHET"
          or (entry.Claimant~=nil and not Integer(entry.Claimant,2147483647)) then return false end
        seen[id]=true
        if entry.Claimant==nil then unclaimed[#unclaimed+1]=id end
      end
    end
    if #unclaimed==0 then return false end
    for _,id in ipairs(unclaimed) do
      -- A ready free recruitment takes precedence; nil is not a known false.
      if people:CanRecruitPerson(ctx.player,id)~=false then return false end
    end
    local count=cities:GetCount()
    if not Integer(count,256) or count==0 then return false end
    local citySeen,n={},0
    for _,member in cities:Members() do
      n=n+1
      local id=member:GetID()
      if n>count or not Integer(id,2147483647) or citySeen[id] or member:GetOwner()~=ctx.player
        or not BaiqiPolicy.MatchesID(cities:FindID(id),id) then return false end
      citySeen[id]=true
      local q=member:GetBuildQueue()
      local hash=q:GetCurrentProductionTypeHash()
      if not BaiqiPolicy.Number(hash) or hash%1~=0 or hash==project.Hash then return false end
      local entries=q:GetSize()
      if not Integer(entries,64) then return false end
      for i=0,entries-1 do
        local entry=q:GetAt(i)
        if type(entry)~="table" then return false end
        if entry.ProjectType~=nil then
          local row=GameInfo.Projects[entry.ProjectType]
          if not row or row.ProjectType==project.ProjectType then return false end
        end
      end
    end
    if n~=count then return false end
    n=0
    for _,pending in pairs(pendingCities) do
      n=n+1
      if n>256 then return false end
      if pending.kind=="project" then
        local row=GameInfo.Projects[pending.hash]
        if not row or row.ProjectType==project.ProjectType then return false end
      end
    end
    local fresh,freshPlayer=PlayerContext()
    return BaiqiPolicy.Context(fresh) and fresh.player==ctx.player and freshPlayer==player
      and Game.GetCurrentGameTurn()==turn and CoreIdle()
  end)
  return ok and wanted==true
end

-- A per-idle-city hint. Do not cache a partial yield scan or let an optional
-- growth/table read prevent normal production when a port is unavailable.
local function BuildingFoodHints(city)
  local ok,food,surplus,stock=pcall(function()
    local growth=city:GetGrowth()
    local net,reserve=growth:GetFoodSurplus(),growth:GetFood()
    if not BaiqiPolicy.Number(net) or net>0 or not BaiqiPolicy.Number(reserve)
      or reserve<0 or reserve>=2 then return nil end
    local yields,count={},0
    for row in GameInfo.Building_YieldChanges() do
      count=count+1
      if count>4096 or type(row)~="table" or type(row.YieldType)~="string" or row.YieldType==""
        or type(row.BuildingType)~="string" or row.BuildingType==""
        or not BaiqiPolicy.Number(row.YieldChange) then return nil end
      if row.YieldType=="YIELD_FOOD" then
        if yields[row.BuildingType]~=nil then return nil end
        yields[row.BuildingType]=row.YieldChange
      end
    end
    return yields,net,reserve
  end)
  if ok then return food,surplus,stock end
end

local function NeighborhoodWanted(city)
  local ok,housing,population=pcall(function()
    return city:GetGrowth():GetHousing(),city:GetPopulation()
  end)
  if not ok then return true end
  return BaiqiPlanner.NeighborhoodDemand(housing,population)
end

-- Only rank the shipped no-power-cost project when its current rules confirm
-- full power while active. Missing optional ports keep ordinary production.
local function PowerProjectWanted(ctx,player,city)
  local ok,wanted=pcall(function()
    if not BaiqiPolicy.Context(ctx) or Players[ctx.player]~=player
      or Game.GetCurrentGameTurn()~=turn then return false end
    local cityID=city:GetID()
    local owned=player:GetCities():FindID(cityID)
    if not BaiqiPolicy.MatchesID(owned,cityID) or city:GetOwner()~=ctx.player
      or owned:GetOwner()~=ctx.player then return false end
    local project=GameInfo.Projects.PROJECT_ENHANCE_DISTRICT_INDUSTRIAL_ZONE
    if not project or project.ProjectType~="PROJECT_ENHANCE_DISTRICT_INDUSTRIAL_ZONE"
      or project.PrereqDistrict~="DISTRICT_INDUSTRIAL_ZONE"
      or not BaiqiPolicy.Number(project.Hash) or project.Hash%1~=0 then return false end
    local rule=GameInfo.Projects_XP2[project.ProjectType]
    if not rule or rule.ProjectType~=project.ProjectType or rule.FullyPoweredWhileActive~=true
      or rule.RequiredPowerWhileActive~=0 then return false end
    local power=owned:GetPower()
    local required,powered=power:GetRequiredPower(),power:IsFullyPowered()
    if not BaiqiPolicy.Number(required) or required<=0 or powered~=false then return false end
    local resources=player:GetResources()
    local coal=resources:GetResourceAmount("RESOURCE_COAL")
    local oil=resources:GetResourceAmount("RESOURCE_OIL")
    local uranium=resources:GetResourceAmount("RESOURCE_URANIUM")
    return BaiqiPlanner.PowerProjectScore(1,required,powered,coal,oil,uranium)==92
  end)
  return ok and wanted==true
end

local function ProjectResumePriority(q,row)
  local ok,score=pcall(function()
    if not row or type(row.ProjectType)~="string" or row.ProjectType=="PROJECT_BAIQI_STANDBY"
      or not BaiqiPolicy.Number(row.Index) or row.Index<0 or row.Index%1~=0
      or not BaiqiPolicy.Number(row.Hash) or row.Hash%1~=0 then return nil end
    return BaiqiPlanner.ResumeProjectScore(1,q:GetProjectProgress(row.Index),q:GetProjectCost(row.Index))
  end)
  if ok and BaiqiPolicy.Number(score) and score>1 then return score end
end

local function ProjectResumeWanted(q,choice)
  local ok,wanted=pcall(function()
    local row=GameInfo.Projects[choice.hash]
    return row~=nil and row.Hash==choice.hash and row.Index==choice.projectIndex
      and row.ProjectType==choice.type and ProjectResumePriority(q,row)~=nil
  end)
  return ok and wanted==true
end

local function FloodBarrierWanted(ctx,player,city)
  local ok,wanted=pcall(function()
    if not BaiqiPolicy.Context(ctx) or Players[ctx.player]~=player or Game.GetCurrentGameTurn()~=turn
      or type(BaiqiFlood)~="table" or type(BaiqiFlood.City)~="function" then return false end
    return BaiqiFlood.City({Game=Game,Players=Players,PlayersVisibility=PlayersVisibility,
      GameInfo=GameInfo,Map=Map,TerrainManager=TerrainManager},ctx.player,city:GetID(),turn)
  end)
  return ok and wanted==true
end

local function ProcessCity(ctx, player, state, city)
  local cityID=city:GetID()
  if type(BaiqiFloodPurchase)=="table" and type(BaiqiFloodPurchase.Holds)=="function"
    and BaiqiFloodPurchase.Holds(ctx.player,cityID)==true then return false end
  if cityEvaluated[cityID]==turn then return false end
  local q=city:GetBuildQueue()
  local completedHead
  if q:GetSize()==1 and CoreIdle() and CityOperationTypes.VALUE_REPLACE_AT~=nil
    and CityOperationTypes.PARAM_QUEUE_DESTINATION_LOCATION~=nil then
    completedHead=CompletedIdleHead(city,q)
  end
  local blockedHead,blockedWork
  if not completedHead and CoreIdle() then blockedHead,blockedWork=BlockedIdleHead(city,q) end
  if not QueueReady(city,q,completedHead,blockedHead,blockedWork) or pendingCities[cityID] then return false end
  cityEvaluated[cityID]=turn
  local amenitiesOK,amenities,amenitiesNeeded=pcall(function()
    local growth=city:GetGrowth()
    return growth:GetAmenities(),growth:GetAmenitiesNeeded()
  end)
  if not amenitiesOK then amenities,amenitiesNeeded=nil,nil end
  local buildingFood,foodSurplus,foodStock=BuildingFoodHints(city)
  local candidates, checked, projectCandidates, hasProjectResume = {}, 0, {}, false
  local bestCandidate
  -- Ranking only, local to this call. Native authority is always checked again.
  local function CouldWin(score,repair,index)
    if not BaiqiPolicy.Number(score) then return false end
    if bestCandidate==nil then return true end
    local proposal={legal=true,score=score,repair=repair,index=index}
    return BaiqiPlanner.Choose({paused=false,queueEmpty=true},{bestCandidate,proposal})==proposal
  end
  local function Add(kind,row,score,repair,placement,firstHolySite,prayerProject,powerProject,floodBarrier,resumeProject)
    if blockedWork and (blockedWork.kind=="project" or blockedWork.kind=="building_repair") then
      local prerequisiteRepair=kind=="district" and repair==true and placement==nil
        and row.Hash==blockedWork.prereqHash and row.Index==blockedWork.prereqIndex
        and row.DistrictType==blockedWork.prereqType
      local barrier=floodBarrier==true and GameInfo.Buildings.BUILDING_FLOOD_BARRIER
      local protectsFloodedWork=barrier and kind=="building" and placement==nil
        and row.BuildingType=="BUILDING_FLOOD_BARRIER" and row.Index==barrier.Index and row.Hash==barrier.Hash
      -- A flooded district may be impossible to repair until its barrier is built.
      -- The reserved emergency candidate still needs all native and final demand checks.
      if not prerequisiteRepair and not protectsFloodedWork then return end
    end
    if kind=="project" and projectCandidates[row.Hash] then return end
    if checked >= C.candidatesPerCity then return end
    checked=checked+1
    -- Retained-project eligibility also sets hasProjectResume for building
    -- ranking; preserve that read even when another candidate already wins.
    if resumeProject~=true and not CouldWin(score,repair,checked) then return end
    local c={kind=kind,hash=row.Hash,index=checked,type=row.BuildingType or row.DistrictType or row.UnitType or row.ProjectType,
      score=score,repair=repair,placement=placement,firstHolySite=firstHolySite==true,
      prayerProject=prayerProject==true,powerProject=powerProject==true,floodBarrier=floodBarrier==true,
      floodBarrierIndex=floodBarrier==true and row.Index or nil,
      resumeProject=resumeProject==true,projectIndex=resumeProject==true and row.Index or nil}
    -- Both original native modes remain required before this candidate enters
    -- the legal pool, and the selected action repeats them at the final boundary.
    if q:CanProduce(row.Hash,true) ~= true or q:CanProduce(row.Hash,false,true) ~= true then return end
    if attempts[CityRequestKey(city,c)] then return end
    local params=BuildParams(c,completedHead,blockedHead)
    if params and CityManager.CanStartOperation(city,CityOperationTypes.BUILD,params,true)==true then
      c.legal=true;candidates[#candidates+1]=c
      bestCandidate=BaiqiPlanner.Choose({paused=false,queueEmpty=true},{bestCandidate or c,c})
      if kind=="project" and row.Hash~=nil then projectCandidates[row.Hash]=true end
      if resumeProject==true then hasProjectResume=true end
    end
  end
  local treasury=player:GetTreasury()
  local netGold=treasury:GetGoldYield()-treasury:GetTotalMaintenance()
  local economy=Economy(player)
  local flood=FloodBarrierWanted(ctx,player,city) and GameInfo.Buildings.BUILDING_FLOOD_BARRIER
  if flood then
    local repair=city:GetBuildings():IsPillaged(flood.Index)==true
    local maintenance=flood.Maintenance or 0
    if not flood.IsWonder and (not flood.RequiresPlacement or repair) and (not flood.MustPurchase or repair)
      and BaiqiPolicy.Number(maintenance) and maintenance>=0
      and (maintenance==0 or netGold-economy.committedMaintenance-maintenance>=C.netGoldMin or repair) then
      Add("building",flood,96,repair,nil,false,false,false,true)
    end
  end
  -- Reserve retained work before ordinary scans can consume the candidate
  -- budget. Its independent investment reason also applies when powered.
  for row in GameInfo.Projects() do
    local priority=ProjectResumePriority(q,row)
    if priority then Add("project",row,priority,false,nil,false,false,false,false,true) end
  end
  local prayerWanted=PrayerProjectWanted(ctx,player,city)
  local prayer=prayerWanted and GameInfo.Projects.PROJECT_ENHANCE_DISTRICT_HOLY_SITE
  -- Reserve this candidate before ordinary entries can exhaust the scan budget.
  -- Its score still loses to essential production, builders and all repairs.
  if prayer then Add("project",prayer,91,false,nil,false,true) end
  local powerWanted=PowerProjectWanted(ctx,player,city)
  local powerProject=powerWanted and GameInfo.Projects.PROJECT_ENHANCE_DISTRICT_INDUSTRIAL_ZONE
  if powerProject then Add("project",powerProject,92,false,nil,false,false,true) end
  for row in GameInfo.Buildings() do
    local repair=city:GetBuildings():IsPillaged(row.Index)
    if (not flood or row.Hash~=flood.Hash) and not row.IsWonder and (not row.RequiresPlacement or repair) and (not row.MustPurchase or repair)
      and ((row.Maintenance or 0)==0 or netGold-economy.committedMaintenance-(row.Maintenance or 0)>=C.netGoldMin or repair) then
      local priority=BaiqiPlanner.AmenityProductionScore(buildingPriority[row.BuildingType] or 40,
        row.Entertainment,amenities,amenitiesNeeded)
      priority=BaiqiPlanner.FoodProductionScore(priority,buildingFood and buildingFood[row.BuildingType],
        foodSurplus,foodStock)
      if (powerWanted or hasProjectResume) and not repair then
        local progressOK,progress,cost=pcall(function()
          return q:GetBuildingProgress(row.Index),q:GetBuildingCost(row.Index)
        end)
        if progressOK then priority=BaiqiPlanner.ResumeProductionScore(priority,progress,cost) end
      end
      Add("building",row,priority,repair)
    end
  end
  local firstHolySite=FirstHolySiteWanted(ctx,player)
  local plots,planningFood={},{}
  for _,index in pairs(Map.GetCityPlots():GetPurchasedPlots(city) or {}) do plots[#plots+1]=index end
  table.sort(plots)
  for row in GameInfo.Districts() do
    -- Disabled districts cannot enter Add; avoid their entire placement scan.
    -- Add and the final writer still repeat both native production modes.
    if row.DistrictType~="DISTRICT_CITY_CENTER" and q:CanProduce(row.Hash,true)==true
      and q:CanProduce(row.Hash,false,true)==true then
      if q:HasBeenPlaced(row.Hash) then
        local priority=BaiqiPlanner.AmenityProductionScore(districtPriority[row.DistrictType] or 35,
          row.Entertainment,amenities,amenitiesNeeded)
        Add("district",row,priority,true)
      elseif row.DistrictType~="DISTRICT_NEIGHBORHOOD" or NeighborhoodWanted(city) then
        local boosted=firstHolySite and row.DistrictType=="DISTRICT_HOLY_SITE"
        local priority=boosted and 92 or (districtPriority[row.DistrictType] or 35)
        if row.DistrictType == "DISTRICT_NEIGHBORHOOD" then
          local ok, housing, population = pcall(function()
            return city:GetGrowth():GetHousing(), city:GetPopulation()
          end)
          if ok then
            priority = BaiqiPlanner.HousingProductionScore(priority, housing, population)
          end
        end
        priority=BaiqiPlanner.AmenityProductionScore(priority,row.Entertainment,amenities,amenitiesNeeded)
        for _, index in ipairs(plots) do
          -- Later equal-score sites lose the existing index tie. No skipped
          -- site supplies permission, and a selected site is still revalidated.
          if not CouldWin(priority,false,checked+1) then break end
          local plot=Map.GetPlotByIndex(index)
          if plot and plot:GetOwner()==ctx.player and ClearPlot(plot,state,player,row,city)
            and plot:CanHaveDistrict(row.Index,ctx.player,city:GetID())
            and DistrictFoodAllows(city,plot,planningFood) then
            Add("district",row,priority,false,{x=plot:GetX(),y=plot:GetY()},boosted)
          end
        end
      end
    end
  end
  economy.cityPopulation=city:GetPopulation()
  for row in GameInfo.Units() do
    local role=row.UnitType=="UNIT_BUILDER" and "builder" or (row.UnitType=="UNIT_SETTLER" and "settler"
      or (row.UnitType=="UNIT_TRADER" and "trader" or (row.UnitType=="UNIT_ARCHAEOLOGIST" and "archaeologist" or (Military(row) and "military" or nil))))
    if role then
      local priority=role=="settler" and 105 or (role=="builder" and 95 or (role=="trader" and 75 or 55))
      if role=="archaeologist" then priority=73 end
      if role=="military" then priority=BaiqiPlanner.MilitaryScore(row,economy,C) end
      if priority and CouldWin(priority,false,checked+1) then
        economy.maintenance=row.Maintenance or 0
        economy.resourceAffordable=q:CanProduce(row.Hash,false,true)==true
        economy.archaeologistDemand=role=="archaeologist" and economy.resourceAffordable and ArchaeologistDemand(ctx,player,city) or false
        if RecruitAllowed(role,economy,player,state) then Add("unit",row,priority,false) end
      end
    end
  end
  for row in GameInfo.Projects() do
    if (not prayer or row.Hash~=prayer.Hash) and (not powerProject or row.Hash~=powerProject.Hash) then
      Add("project",row,row.ProjectType=="PROJECT_BAIQI_STANDBY" and -1000 or 1,false)
    end
  end
  local choice=BaiqiPlanner.Choose({paused=false,queueEmpty=true},candidates)
  if choice == nil then Reason("city:"..city:GetID(),"城市等待合法生产或预算"); return false end
  -- All state and legality are checked again at the write boundary.
  local freshCtx, freshPlayer, freshState=PlayerContext()
  if not BaiqiPolicy.Context(freshCtx) or not BaiqiPolicy.MatchesID(city,cityID) or city:GetOwner()~=freshCtx.player
    or not QueueReady(city,q,completedHead,blockedHead,blockedWork) then return false end
  local params=BuildParams(choice,completedHead,blockedHead)
  if q:CanProduce(choice.hash,true)~=true or q:CanProduce(choice.hash,false,true)~=true
    or CityManager.CanStartOperation(city,CityOperationTypes.BUILD,params,true)~=true then return false end
  if choice.kind=="district" and choice.type=="DISTRICT_NEIGHBORHOOD" and choice.repair~=true
    and not NeighborhoodWanted(city) then
    cityEvaluated[cityID]=nil
    Reason("housing_changed:"..cityID,"住房余量已变化，重新安排合法任务")
    return false
  end
  if choice.kind=="unit" then
    local row=GameInfo.Units[choice.hash]
    local role=row and (row.UnitType=="UNIT_BUILDER" and "builder" or (row.UnitType=="UNIT_SETTLER" and "settler"
      or (row.UnitType=="UNIT_TRADER" and "trader" or (row.UnitType=="UNIT_ARCHAEOLOGIST" and "archaeologist" or (Military(row) and "military" or nil)))))
    local actual=Economy(freshPlayer)
    actual.cityPopulation=city:GetPopulation()
    actual.maintenance=row and row.Maintenance or 0
    actual.resourceAffordable=q:CanProduce(choice.hash,false,true)==true
    actual.archaeologistDemand=role=="archaeologist" and actual.resourceAffordable and ArchaeologistDemand(freshCtx,freshPlayer,city) or false
    if not role or not RecruitAllowed(role,actual,freshPlayer,freshState)
      or (role=="military" and not BaiqiPlanner.MilitaryScore(row,actual,C)) then
      cityEvaluated[cityID]=nil
      Reason("budget_changed:"..cityID,"生产预算已变化，重新安排合法任务")
      return false
    end
  elseif choice.kind=="building" then
    local row=GameInfo.Buildings[choice.hash]
    local maintenance=row and (row.Maintenance or 0)
    local affordable=row~=nil and BaiqiPolicy.Number(maintenance) and maintenance>=0
    if affordable and maintenance>0 and city:GetBuildings():IsPillaged(row.Index)~=true then
      local actual=Economy(freshPlayer)
      affordable=actual.netGold-actual.committedMaintenance-maintenance>=C.netGoldMin
    end
    if not affordable then
      cityEvaluated[cityID]=nil
      Reason("budget_changed:"..cityID,"生产预算已变化，重新安排合法任务")
      return false
    end
  end
  local latest,latestPlayer,latestState=PlayerContext()
  if not BaiqiPolicy.Context(latest) or latest.player~=freshCtx.player or not BaiqiPolicy.MatchesID(city,cityID)
    or city:GetOwner()~=latest.player or not QueueReady(city,q,completedHead,blockedHead,blockedWork) then return false end
  if choice.firstHolySite and not FirstHolySiteWanted(latest,latestPlayer) then
    cityEvaluated[cityID]=nil
    Reason("religion_supply_changed:"..cityID,"首座圣地需求已变化，重新安排合法生产")
    return false
  end
  if choice.prayerProject and not PrayerProjectWanted(latest,latestPlayer,city) then
    cityEvaluated[cityID]=nil
    Reason("religion_prayer_changed:"..cityID,"先知点数需求已变化，重新安排合法生产")
    return false
  end
  if choice.powerProject and not PowerProjectWanted(latest,latestPlayer,city) then
    cityEvaluated[cityID]=nil
    Reason("power_changed:"..cityID,"Power demand or available fuel changed; replan production")
    return false
  end
  if choice.floodBarrier and not FloodBarrierWanted(latest,latestPlayer,city) then
    cityEvaluated[cityID]=nil
    Reason("flood_changed:"..cityID,"Coastal flood demand changed; replan production")
    return false
  end
  -- The extra demand read must not cover a turn/queue change at its boundary.
  if (choice.firstHolySite or choice.prayerProject or choice.powerProject or choice.floodBarrier) and (not CoreIdle() or not QueueReady(city,q,completedHead,blockedHead,blockedWork)
    or Game.GetCurrentGameTurn()~=turn or not BaiqiPolicy.MatchesID(city,cityID)
    or city:GetOwner()~=latest.player) then return false end
  if (choice.prayerProject or choice.powerProject or choice.floodBarrier) and (q:CanProduce(choice.hash,true)~=true
    or q:CanProduce(choice.hash,false,true)~=true
    or CityManager.CanStartOperation(city,CityOperationTypes.BUILD,params,true)~=true) then return false end
  if (choice.powerProject or choice.floodBarrier) and (not CoreIdle() or not QueueReady(city,q,completedHead,blockedHead,blockedWork)
    or Game.GetCurrentGameTurn()~=turn or not BaiqiPolicy.MatchesID(city,cityID)
    or city:GetOwner()~=latest.player) then return false end
  if choice.placement then
    local row=GameInfo.Districts[choice.hash]
    local x,y=choice.placement.x,choice.placement.y
    local plot=Map.GetPlot(x,y)
    if choice.kind~="district" or not row or row.Hash~=choice.hash or not plot
      or plot:GetX()~=x or plot:GetY()~=y
      or plot:CanHaveDistrict(row.Index,latest.player,cityID)~=true
      or plot:GetOwner()~=latest.player or not ClearPlot(plot,latestState,latestPlayer,row,city) then return false end
    if not DistrictFoodAllows(city,plot,{}) then
      cityEvaluated[cityID]=nil
      Reason("placement_food_changed:"..cityID,"工作粮食已变化，重新安排区域选址")
      return false
    end
    if Game.GetCurrentGameTurn()~=turn or not QueueReady(city,q,completedHead,blockedHead,blockedWork)
      or not BaiqiPolicy.MatchesID(city,cityID) or city:GetOwner()~=latest.player then return false end
  end
  if blockedHead and (q:CanProduce(choice.hash,true)~=true or q:CanProduce(choice.hash,false,true)~=true
    or CityManager.CanStartOperation(city,CityOperationTypes.BUILD,params,true)~=true
    or not QueueReady(city,q,completedHead,blockedHead,blockedWork) or Game.GetCurrentGameTurn()~=turn
    or not BaiqiPolicy.MatchesID(city,cityID) or city:GetOwner()~=latest.player) then return false end
  if blockedHead and choice.floodBarrier then
    local barrier=GameInfo.Buildings.BUILDING_FLOOD_BARRIER
    if not barrier or barrier.BuildingType~="BUILDING_FLOOD_BARRIER" or barrier.Hash~=choice.hash
      or barrier.Index~=choice.floodBarrierIndex or not FloodBarrierWanted(latest,latestPlayer,city) then
      cityEvaluated[cityID]=nil
      Reason("flood_changed:"..cityID,"Coastal flood demand changed; replan production")
      return false
    end
    if barrier.Hash~=choice.hash or barrier.Index~=choice.floodBarrierIndex
      or barrier.BuildingType~="BUILDING_FLOOD_BARRIER" or not CoreIdle()
      or not QueueReady(city,q,completedHead,blockedHead,blockedWork) or Game.GetCurrentGameTurn()~=turn
      or not BaiqiPolicy.MatchesID(city,cityID) or city:GetOwner()~=latest.player then return false end
  end
  if choice.resumeProject then
    if q:CanProduce(choice.hash,true)~=true or q:CanProduce(choice.hash,false,true)~=true
      or CityManager.CanStartOperation(city,CityOperationTypes.BUILD,params,true)~=true then return false end
    -- A stored amount is not permission to start a fresh repeatable project.
    -- Recheck the investment after native legality, then scope after its reads.
    if not ProjectResumeWanted(q,choice) or not CoreIdle() or not QueueReady(city,q,completedHead,blockedHead,blockedWork)
      or Game.GetCurrentGameTurn()~=turn or not BaiqiPolicy.MatchesID(city,cityID)
      or city:GetOwner()~=latest.player then
      cityEvaluated[cityID]=nil
      Reason("project_resume_changed:"..cityID,"项目投资或生产状态已变化，重新安排合法任务")
      return false
    end
  end
  local id=NextRequest(CityRequestKey(city,choice))
  if id==nil then return false end
  pendingCities[city:GetID()]={id=id,hash=choice.hash,kind=choice.kind,elapsed=0,replacesHead=completedHead,prependsHead=blockedHead,blockedWork=blockedWork,
    firstHolySite=choice.firstHolySite,prayerProject=choice.prayerProject,floodBarrier=choice.floodBarrier,
    floodBarrierIndex=choice.floodBarrierIndex}
  if choice.kind=="unit" then
    submittedUnits[cityID]=submittedUnits[cityID] or {}
    submittedUnits[cityID][choice.hash]=true
  end
  Log("request","id="..id.."|source=BACKGROUND|city="..city:GetID().."|type="..choice.type
    ..(choice.resumeProject and "|resume_project=true" or "")
    ..(blockedHead and "|insert=prepend_blocked" or (completedHead and "|insert=replace_completed" or "")))
  CityManager.RequestOperation(city,CityOperationTypes.BUILD,params)
  return true
end

local function ReadBack(player)
  if missionaryPurchase.pending then
    local pending=missionaryPurchase.pending
    local stage,token=missionaryPurchase.Bridge("Inspect",contextID,pending.token)
    if stage=="OBSERVED"and token==pending.token then
      Log("observed","id="..pending.id.."|city="..pending.cityID.."|kind=PURCHASE|unit=UNIT_MISSIONARY|proof=core_new_unit_and_exact_faith_debit")
      missionaryPurchase.pending=nil
    end
  end
  if pendingPurchase then
    local stage,token=NaturalistPurchaseBridge("Inspect",contextID,pendingPurchase.token)
    if stage=="OBSERVED" and token==pendingPurchase.token then
      Log("observed","id="..pendingPurchase.id.."|city="..pendingPurchase.cityID
        .."|kind=PURCHASE|unit=UNIT_NATURALIST|proof=core_new_unit_and_exact_faith_debit")
      pendingPurchase=nil
    end
  end
  for unitID, pending in pairs(pendingUnits) do
    local lookup
    if BaiqiPolicy.Number(unitID) and unitID>=0 and unitID<=2147483647 and unitID%1==0 then
      lookup=player:GetUnits():FindID(unitID)
    end
    local unit=lookup
    if not BaiqiPolicy.MatchesID(unit,unitID) then unit=nil end
    if pending.kind=="FOUND_RELIGION" then
      local stage,token=ProphetBridge("Inspect",contextID,unitID)
      local religion=player.GetReligion and player:GetReligion()
      local earned=religion and religion.GetNumBeliefsEarned and religion:GetNumBeliefsEarned() or 0
      if pending.persistent==true and type(pending.token)=="string" and stage=="OBSERVED" and token==pending.token
        and BaiqiPolicy.Number(earned) and earned>pending.earned then
        Log("observed","id="..pending.id.."|unit="..unitID.."|kind=FOUND_RELIGION|proof=bridge_observed_and_earned_qualification")
        pendingUnits[unitID]=nil
      elseif (pending.elapsed or 0)>=C.productionObservationSeconds and not pending.unresolvedLogged then
        Log("prophet_request_unresolved","id="..pending.id.."|unit="..unitID.."|awaiting_bridge_observed_and_earned_qualification=true")
        pending.unresolvedLogged=true
      end
    elseif pending.kind=="DESIGNATE_PARK" then
      local stage,token=NaturalistBridge("Inspect",contextID,unitID)
      if stage=="OBSERVED" and token==pending.token then
        Log("observed","id="..pending.id.."|unit="..unitID.."|kind=DESIGNATE_PARK|proof=core_owned_visible_national_park")
        pendingUnits[unitID]=nil
        naturalistSearches[unitID]=nil
        if unit then unitEvaluated[UnitKey(unit)]=nil end
      elseif (pending.elapsed or 0)>=C.productionObservationSeconds and not pending.unresolvedLogged then
        Log("naturalist_request_unresolved","id="..pending.id.."|unit="..unitID.."|awaiting_actual_park_proof=true")
        pending.unresolvedLogged=true
      end
    elseif pending.kind=="EXCAVATE" or pending.kind=="CHOOSE_ARTIFACT_PLAYER" then
      local stage,token=ArchaeologyBridge("Inspect",contextID,unitID)
      if stage=="OBSERVED" and token==pending.token then
        Log("observed","id="..pending.id.."|unit="..unitID.."|kind=ARCHAEOLOGY|proof=core_created_work_receipt")
        pendingUnits[unitID]=nil;archaeologySearches[unitID]=nil
        if unit then unitEvaluated[UnitKey(unit)]=nil end
      elseif (pending.elapsed or 0)>=C.productionObservationSeconds and not pending.unresolvedLogged then
        Log("archaeology_request_unresolved","id="..pending.id.."|unit="..unitID.."|awaiting_actual_artifact_receipt=true")
        pending.unresolvedLogged=true
      end
    elseif pending.kind=="SPREAD_RELIGION" then
      local stage,token=ReligiousBridge("Inspect",contextID,unitID)
      local religion,charges
      if unit and unit:GetOwner()==contextID then religion,charges=MissionaryData(unit) end
      if stage=="OBSERVED" and token==pending.token and pending.charges==1 and not unit then
        Log("observed","id="..pending.id.."|unit="..unitID.."|kind=SPREAD_RELIGION|proof=core_final_charge_receipt")
        pendingUnits[unitID]=nil
      elseif stage=="OBSERVED" and token==pending.token and religion==pending.religion
        and charges and charges<pending.charges then
        Log("observed","id="..pending.id.."|unit="..unitID.."|kind=SPREAD_RELIGION|proof=core_and_ui_charge_decrease|charges="..charges)
        pendingUnits[unitID]=nil
        unitEvaluated[UnitKey(unit)]=nil
      elseif (pending.elapsed or 0)>=C.productionObservationSeconds and not pending.unresolvedLogged then
        Log("missionary_request_unresolved","id="..pending.id.."|unit="..unitID.."|awaiting_current_charge_proof=true")
        pending.unresolvedLogged=true
      end
    elseif pending.kind=="CREATE_GREAT_WORK" then
      local stage,token=CreativeBridge("Inspect",contextID,unitID)
      if stage=="OBSERVED" and token==pending.token and CreatedWorkObserved(player,pending) then
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
      if pending.persistent then
        local stamp=table.concat({tostring(turn),tostring(unit and unit:GetOwner()),
          tostring(gp and gp:GetActionCharges())},":")
        if pending.receiptDirty or stamp~=pending.inspectStamp then
          local stage,token,proof=GPBridge("Inspect",contextID,unitID)
          pending.inspectStamp=stamp;pending.receiptDirty=nil
          if stage=="OBSERVED" and token==pending.token then
            if gp and gp:GetActionCharges()<pending.charges then proof="charges="..gp:GetActionCharges() end
            Log("observed","id="..pending.id.."|unit="..unitID.."|kind=ACTIVATE_GREAT_PERSON|"..(proof=="native_activation_event" and "proof="..proof or tostring(proof)))
            pendingUnits[unitID]=nil
            if unit then unitEvaluated[UnitKey(unit)]=nil end
          end
        end
        if pendingUnits[unitID] and not gp and not pending.unavailableLogged then
          Log("great_person_request_unavailable","id="..pending.id.."|unit="..unitID.."|awaiting_native_activation_event=true")
          pending.unavailableLogged=true
        elseif pendingUnits[unitID] and (pending.elapsed or 0)>=C.productionObservationSeconds and not pending.unresolvedLogged then
          Log("great_person_request_unresolved","id="..pending.id.."|unit="..unitID.."|awaiting_native_activation_or_charge_change=true")
          pending.unresolvedLogged=true
        end
      elseif pending.nativeActivated then
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
      elseif (pending.elapsed or 0)>=C.productionObservationSeconds and not pending.unresolvedLogged then
        -- A void command and unchanged charges do not prove rejection. Keep
        -- the request across turns until its exact event or effect arrives.
        Log("great_person_request_unresolved","id="..pending.id.."|unit="..unitID.."|awaiting_native_activation_or_charge_change=true")
        pending.unresolvedLogged=true
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
    elseif pending.kind=="FOUND_CITY" then
      local ok,cityID
      if pending.persistent==true then
        local stage,op=SettlementBridge("Inspect",contextID,unitID)
        op=SettlementRecord(op,contextID,unitID)
        ok=stage=="OBSERVED" and op~=nil and op.stage==stage and op.token==pending.token
          and op.requestID==pending.id
        if ok then cityID=op.cityID end
        if not ok and unit and type(pending.dispatch)~="function" then RequestCivilianStandby(unit) end
      else ok,cityID=pcall(FoundCityObserved,player,pending,lookup) end
      if ok and cityID~=nil then
        Log("observed","id="..pending.id.."|unit="..unitID.."|kind=FOUND_CITY|city="..cityID
          ..(pending.persistent and "|proof=core_durable_empty_site_city_and_consumed_settler|token="..pending.token
            or "|proof=new_owned_city_at_empty_site_and_absent_settler"))
        pendingUnits[unitID]=nil
        SettlerGoalBridge("Forget",contextID,unitID)
      elseif (pending.elapsed or 0)>=C.productionObservationSeconds and not pending.unresolvedLogged then
        -- Consumption and city creation may reach UI in different callbacks.
        -- Keep this intent across ordinary turns; neither absence nor movement
        -- points prove an outcome, and unknown results must not be resubmitted.
        Log("settler_request_unresolved","id="..pending.id.."|unit="..unitID
          .."|awaiting_new_owned_city_and_consumed_unit=true")
        pending.unresolvedLogged=true
      end
    elseif unit==nil or unit:GetOwner()~=contextID then
      Log("unit_request_not_observed","id="..pending.id.."|unit="..unitID.."|reason=unit_unavailable")
      pendingUnits[unitID]=nil
    elseif (UnitIndex(unit)~=nil and UnitIndex(unit)~=pending.from)
      or (pending.kind~="MOVE_TO" and unit:GetMovesRemaining()~=pending.moves) then
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
      if pending.prependsHead then
        local ok,preserved=pcall(function()
          local size=q:GetSize()
          if hash~=pending.hash or (size~=1 and size~=2) then return false end
          local _,head=QueueHeadSignature(q)
          local tables={building=GameInfo.Buildings,district=GameInfo.Districts,unit=GameInfo.Units,project=GameInfo.Projects}
          local fields={building="BuildingType",district="DistrictType",unit="UnitType",project="ProjectType"}
          local row=head and tables[pending.kind][head[fields[pending.kind]]]
          if not row or row.Hash~=pending.hash then return false end
          local work=pending.blockedWork
          local barrierHead=false
          if pending.floodBarrier==true then
            local barrier=GameInfo.Buildings.BUILDING_FLOOD_BARRIER
            if pending.kind~="building" or not barrier or barrier.BuildingType~="BUILDING_FLOOD_BARRIER"
              or barrier.Hash~=pending.hash or barrier.Index~=pending.floodBarrierIndex
              or barrier.Index~=head.BuildingType then return false end
            barrierHead=true -- The queued barrier is observed; drainage/completion is not claimed.
          end
          if work and work.kind=="project" then
            if work.buildingIndex~=nil or (not barrierHead and (pending.kind~="district" or pending.hash~=work.prereqHash)) then return false end
            local old=GameInfo.Projects[work.projectIndex]
            local district=GameInfo.Districts[work.prereqType]
            if not old or old.Index~=work.projectIndex or old.Hash~=work.hash or old.ProjectType~=work.projectType
              or old.PrereqDistrict~=work.prereqType or not district or district.Index~=work.prereqIndex
              or district.Hash~=work.prereqHash or district.DistrictType~=work.prereqType then return false end
            local progress,cost=q:GetProjectProgress(work.projectIndex),q:GetProjectCost(work.projectIndex)
            if not BaiqiPolicy.Number(work.progress) or work.progress<=0 or not BaiqiPolicy.Number(work.cost)
              or work.cost<=work.progress or not BaiqiPolicy.Number(progress) or progress<work.progress
              or not BaiqiPolicy.Number(cost) or progress>=cost then return false end
            if size==2 then return QueueHeadSignature(q,1)==pending.prependsHead end
            -- Native may prune the blocked entry; invested unfinished work must remain stored.
            return true
          end
          if work and work.kind=="building_repair" then
            if work.projectIndex~=nil or (not barrierHead and (pending.kind~="district" or pending.hash~=work.prereqHash)) then return false end
            local old=GameInfo.Buildings[work.buildingIndex]
            local district=GameInfo.Districts[work.prereqType]
            if not old or old.Index~=work.buildingIndex or old.Hash~=work.hash or old.BuildingType~=work.buildingType
              or old.PrereqDistrict~=work.prereqType or not district or district.Index~=work.prereqIndex
              or district.Hash~=work.prereqHash or district.DistrictType~=work.prereqType then return false end
            local buildings=city:GetBuildings()
            if buildings:HasBuilding(work.buildingIndex)~=true or buildings:IsPillaged(work.buildingIndex)~=true then return false end
            local progress,cost=q:GetBuildingProgress(work.buildingIndex),q:GetBuildingCost(work.buildingIndex)
            if not BaiqiPolicy.Number(work.progress) or work.progress<=0 or not BaiqiPolicy.Number(work.cost)
              or work.cost<=work.progress or not BaiqiPolicy.Number(progress) or progress<work.progress
              or not BaiqiPolicy.Number(cost) or progress>=cost then return false end
            if size==2 then return QueueHeadSignature(q,1)==pending.prependsHead end
            -- Native PREPEND can prune the unbuildable old entry. Its production
            -- must still be stored; never recreate an illegal queue entry or pay
            -- compensation. Missing/unknown progress leaves this request pending.
            return true
          end
          local old=work and GameInfo.Buildings[work.buildingIndex]
          if not old or old.Index~=work.buildingIndex or old.Hash~=work.hash then return false end
          local progress=q:GetBuildingProgress(work.buildingIndex)
          if not BaiqiPolicy.Number(progress) or not BaiqiPolicy.Number(work.progress)
            or work.progress<0 or progress<work.progress then return false end
          if size==2 then return QueueHeadSignature(q,1)==pending.prependsHead end
          -- Native PREPEND can prune the unbuildable old entry. Its production
          -- must still be stored; never recreate an illegal queue entry or pay
          -- compensation. Missing/unknown progress leaves this request pending.
          return city:GetBuildings():HasBuilding(work.buildingIndex)==false
        end)
        matched=ok and preserved==true
      end
      if matched then
        Log("queue_observed","id="..pending.id.."|city="..cityID.."|hash="..pending.hash)
        pendingCities[cityID]=nil
      elseif pending.prependsHead or pending.replacesHead or pending.firstHolySite or pending.prayerProject then
        -- A missing replacement or boosted religion request is unknown. A late
        -- operation could overwrite work or duplicate the empire's supply goal.
        -- Retain the request and never infer failure from a temporary empty head.
        if (pending.elapsed or 0)>=C.productionObservationSeconds and CoreIdle() and not pending.unresolvedLogged then
          Log(pending.prependsHead and "queue_prepend_unresolved" or pending.prayerProject and "prayer_project_request_unresolved"
            or (pending.firstHolySite and "first_holy_site_request_unresolved" or "queue_replacement_unresolved"),
            "id="..pending.id.."|city="..cityID.."|actual_hash="..hash)
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

local function CivilianWorkHeld(unit,kind,key)
  return (kind=="UNIT_BUILDER"and unitEvaluated[key]=="native_wait")
    or (BaiqiPolicy.DistrictGreatPersonClass(kind)and DistrictPersonHeld(unit))
    or (kind=="UNIT_SETTLER"and SettlementHeld(unit))
    or (BaiqiPolicy.CreativeGreatPersonClass(kind)and CreativeHeld(unit))
    or (kind=="UNIT_MISSIONARY"and MissionaryHeld(unit))
    or (kind=="UNIT_GREAT_PROPHET"and ProphetHeld(unit))
    or (kind=="UNIT_NATURALIST"and NaturalistHeld(unit))
    or (kind=="UNIT_ARCHAEOLOGIST"and ArchaeologyHeld(unit))
end

-- A later arrival or disappearing threat does not change this actor's UnitKey.
-- Reconsider only overlap parking, never repeat its already evaluated task.
local function RetryCivilianOverlap(ctx,player,state,unit)
  local id,kind,index=unit:GetID(),unit:GetUnitType(),UnitIndex(unit)
  local key,stamp,epoch=UnitKey(unit),turn,settlementWorldEpoch
  local def=GameInfo.Units[kind]
  if not def or not BaiqiPolicy.CivilianType(def.UnitType)or not index
    or unitEvaluated[key]~=true or pendingUnits[id]~=nil then return false end
  local name=def.UnitType
  local manager=UnitManager
  local can,writer,queue,path=manager.CanStartOperation,manager.RequestOperation,manager.GetQueuedDestination,manager.GetMoveToPathEx
  local byIndex,activity=Map.GetPlotByIndex,manager.GetActivityType
  local skipRow=GameInfo.UnitOperations and GameInfo.UnitOperations.UNITOPERATION_SKIP_TURN
  local skip=skipRow and skipRow.Hash
  if type(can)~="function"or type(writer)~="function"or type(queue)~="function"
    or type(path)~="function"or type(activity)~="function"or not BaiqiPolicy.Number(skip)then return false end
  local function Bound()
    return UnitManager==manager and manager.CanStartOperation==can and manager.RequestOperation==writer
      and manager.GetQueuedDestination==queue and manager.GetMoveToPathEx==path
      and manager.GetActivityType==activity and Map.GetPlotByIndex==byIndex
      and GameInfo.UnitOperations.UNITOPERATION_SKIP_TURN==skipRow and skipRow.Hash==skip
  end
  local function Empty(ok,...)return ok and select("#",...)<=1 and (...)==nil end
  local function False(ok,...)return ok and select("#",...)==1 and (...)==false end
  local function Fresh()
    local ok,fresh=pcall(function()
      local c,p,s=PlayerContext();local u=p and p:GetUnits():FindID(id)
      if not c or c.player~=ctx.player or not CoreIdle()or not Bound()or turn~=stamp
        or Game.GetCurrentGameTurn()~=stamp or settlementWorldEpoch~=epoch
        or pendingUnits[id]~=nil or unitEvaluated[key]~=true
        or not BaiqiPolicy.MatchesID(u,id)or u:GetOwner()~=ctx.player or u:GetUnitType()~=kind
        or UnitIndex(u)~=index or UnitKey(u)~=key or not BaiqiPolicy.CanCivilian(c,UnitSnapshot(u,s))
        or type(u.IsReadyToMove)~="function"or u:IsReadyToMove()~=true
        or type(u.IsReadyToSelect)~="function"or u:IsReadyToSelect()~=true
        or type(u.IsDead)~="function"or u:IsDead()~=false
        or type(u.IsDelayedDeath)~="function"or u:IsDelayedDeath()~=false
        or type(u.HasPendingOperations)~="function"or not False(pcall(u.HasPendingOperations,u))
        or not Empty(pcall(queue,u))or activity(u)~=ActivityTypes.ACTIVITY_AWAKE
        or CivilianWorkHeld(u,name,key)then return nil end
      if not CoreIdle()or not Bound()or turn~=stamp or Game.GetCurrentGameTurn()~=stamp
        or settlementWorldEpoch~=epoch or pendingUnits[id]~=nil then return nil end
      return u
    end)
    return ok and fresh or nil
  end
  local fresh=Fresh()
  if not fresh or not False(pcall(can,fresh,skip,nil,{}))or not Fresh()then return false end
  return ClearCivilianOverlap(ctx,player,state,fresh,function(plot,target,x,y)
    local current=Fresh();local cell=byIndex(target)
    if not current or not cell or cell:GetIndex()~=target or cell:GetX()~=x or cell:GetY()~=y
      or cell:GetOwner()~=ctx.player or cell:IsWater()~=false or cell:IsImpassable()~=false
      or not Revealed(cell)or visibility:IsVisible(x,y)~=true then return false end
    local here=UnitPlot(current)
    return here~=nil and here:GetOwner()==ctx.player and Revealed(here)
      and visibility:IsVisible(here:GetX(),here:GetY())==true
      and Map.GetPlotDistance(here:GetX(),here:GetY(),x,y)==1
      and Safe(here,player)and Safe(cell,player)and CivilianMoveTarget(here,cell,current,ctx.player)==true
  end)
end

-- The cursor schedules work only; it never carries a native object or permission.
-- Re-read membership on every callback, and keep every actual city write guarded
-- by ProcessCity's existing current owner, queue, price and legality checks.
local function NextCityForPlanning(player)
  local ok,city,index=pcall(function()
    local wanted=cityCursor+1;local seen,first=0,nil
    for _,candidate in player:GetCities():Members()do
      seen=seen+1
      if first==nil then first=candidate end
      if seen==wanted then return candidate,wanted end
    end
    if first~=nil then return first,1 end
    return nil,0
  end)
  cityCursor=ok and index or 0
  if ok then return city end
end

local function Tick(allowOrders)
  planningStarted=PlanningTime()
  if stopped then return end
  local ctx,player,state=PlayerContext()
  if ctx==nil then builderSearches={};builderRejectedGoals={};settlerSearches={};return end
  contextID=ctx.player
  if not BaiqiPolicy.Context(ctx) then builderSearches={};builderRejectedGoals={};settlerSearches={};return end
  visibility=PlayersVisibility[ctx.player]
  if visibility==nil then builderSearches={};builderRejectedGoals={};settlerSearches={};return end
  local current=type(Game.GetCurrentGameTurn)=="function" and Game.GetCurrentGameTurn()
  if not BaiqiPolicy.Number(current) or current<0 or current>2147483647 or current%1~=0 then return end
  if current~=turn then
    cityCursor=0
    builderResumeStreak=0;districtRoute.used=false
    for _,plan in pairs(districtPersonPlans) do plan.route=nil end
    purchaseSearch=nil;purchaseDoneTurn=-1;purchaseResumeStreak=0
    turn=current; requestCount=0; attempts={}; reservations={}; lastReasons={}; cityEvaluated={}; unitEvaluated={}; submittedUnits={}; builderSearches={}; builderRejectedGoals={}; settlerSearches={}
    -- SKIP_TURN can leave movement points unchanged. Its intent expires with the
    -- turn; retaining that pending slot would strand the civilian indefinitely.
    for id,pending in pairs(pendingUnits) do
      if pending.kind=="SKIP_TURN" then pendingUnits[id]=nil end
      -- Live unsent permission is deliberately narrower than durable intent.
      -- A later turn still retains ARMED, without reconstructing a grant.
      if pending.kind=="FOUND_CITY" then pending.dispatch=nil end
    end
    for id in pairs(districtPersonPlans) do
      local unit=player:GetUnits():FindID(id)
      if not BaiqiPolicy.MatchesID(unit,id) or unit:GetOwner()~=ctx.player then districtPersonPlans[id]=nil end
    end
    for id in pairs(missionaryPlans) do
      local unit=player:GetUnits():FindID(id)
      if not BaiqiPolicy.MatchesID(unit,id) or unit:GetOwner()~=ctx.player then missionaryPlans[id]=nil end
    end
  end
  -- Passive initialization and effect receipts still reconcile while busy.
  -- Only ordinary movement, route and queue receipts may await an idle tick.
  if allowOrders~=false and not CoreIdle() then
    local effectPending=pendingPurchase~=nil or missionaryPurchase.pending~=nil
    for _,pending in pairs(pendingUnits) do
      local kind=pending.kind
      if kind=="ACTIVATE_GREAT_PERSON" or kind=="CREATE_GREAT_WORK"
        or kind=="FOUND_RELIGION" or kind=="SPREAD_RELIGION" or kind=="DESIGNATE_PARK"
        or kind=="EXCAVATE" or kind=="CHOOSE_ARTIFACT_PLAYER" or kind=="FOUND_CITY" then
        effectPending=true;break
      end
    end
    if not effectPending then return end
  end
  RefreshSettlement(ctx.player)
  ReadBack(player)
  for id,entry in pairs(builderRejectedGoals) do
    local unit=player:GetUnits():FindID(id)
    local row=unit and GameInfo.Units[unit:GetUnitType()]
    if entry.player~=ctx.player or entry.turn~=turn or not BaiqiPolicy.MatchesID(unit,id)
      or unit:GetOwner()~=ctx.player or not row or row.UnitType~="UNIT_BUILDER"
      or unit:GetFormationUnitCount()~=1 then builderRejectedGoals[id]=nil end
  end
  for id,search in pairs(builderSearches) do
    local unit=player:GetUnits():FindID(id)
    local row=unit and GameInfo.Units[unit:GetUnitType()]
    if not BaiqiPolicy.MatchesID(unit,id) or not row or row.UnitType~="UNIT_BUILDER"
      or search.player~=ctx.player or search.turn~=turn or UnitKey(unit)~=search.key
      or not BaiqiPolicy.CanCivilian(ctx,UnitSnapshot(unit,state)) then builderSearches[id]=nil end
  end
  for id,search in pairs(settlerSearches) do
    local unit=player:GetUnits():FindID(id)
    local row=unit and GameInfo.Units[unit:GetUnitType()]
    if not BaiqiPolicy.MatchesID(unit,id) or not row or row.UnitType~="UNIT_SETTLER"
      or search.player~=ctx.player or search.turn~=turn or UnitKey(unit)~=search.key
      or not BaiqiPolicy.CanCivilian(ctx,UnitSnapshot(unit,state)) then settlerSearches[id]=nil end
  end
  -- Existing factual receipts may reconcile while the core is busy. New
  -- gameplay orders wait until both native processing readers report idle.
  if allowOrders==false or not CoreIdle() then return end
  for _,pending in pairs(pendingUnits) do
    if pending.kind=="FOUND_CITY" and type(pending.dispatch)=="function" and pending.dispatch() then
      status="已提交移民建城，等待实际结果";return
    end
  end
  -- Only the engine's actual extraction queue permits an artifact choice.
  -- This runs before ordinary scheduling because a pending artifact can block it.
  local artifact,artifactStatus=ArchaeologyPendingRead(ctx,player)
  if artifactStatus=="ok" and RequestArchaeologyChoice(artifact) then
    status="已提交文物归属选择，等待实际入藏";return
  end
  -- Share the existing two-continuation allowance with builders. One GP
  -- continuation per ordinary pass also leaves the other slot to builders.
  if builderResumeStreak<2 and not districtRoute.used then
    for _,plan in pairs(districtPersonPlans) do
      if plan.route then
        local worked,submitted=districtRoute.Run(plan)
        if worked then
          districtRoute.used=true;builderResumeStreak=builderResumeStreak+1
          status=submitted and "已提交文职伟人移动，等待实际结果" or "文职伟人继续检查安全路线；军队由你指挥"
          return
        end
      end
    end
  end
  -- At most two continuation callbacks before normal city/unit scheduling.
  if builderResumeStreak<2 then
    for id,search in pairs(builderSearches) do
      if search.phase then
        local unit=player:GetUnits():FindID(id)
        if unit and BuilderRouteValid(ctx,state,unit,search) then
          builderResumeStreak=builderResumeStreak+1
          local submitted,continuing=AdvanceBuilderRoute(ctx,player,state,unit,search)
          status=submitted and "已提交建造者操作，等待实际结果" or (continuing and "建造者继续检查安全路线；军队由你指挥" or "建造者按当前状态重新规划；军队由你指挥")
          return
        end
        builderSearches[id]=nil
      end
    end
  end
  builderResumeStreak=0;districtRoute.used=false
  local city=NextCityForPlanning(player)
  if city and ProcessCity(ctx,player,state,city) then status="已安排生产；军队等待你的命令"; return end
  -- One city's quote per callback, at most two purchase continuations before
  -- normal unit scheduling. Scalar failed IDs never authorize a later command.
  if missionaryPurchase.streak<2 then
    local submitted,continuing=missionaryPurchase.Process(ctx,player)
    if submitted then missionaryPurchase.streak=0;status="已登记传教士购买；等待实际扣费与新单位";return end
    if continuing then missionaryPurchase.streak=missionaryPurchase.streak+1;return end
  end
  missionaryPurchase.streak=0
  if purchaseResumeStreak<2 then
    local submitted,continuing=ProcessNaturalistPurchase(ctx,player)
    if submitted then purchaseResumeStreak=0;status="已登记自然学家购买；等待实际扣费与新单位";return end
    if continuing then purchaseResumeStreak=purchaseResumeStreak+1;return end
  end
  purchaseResumeStreak=0
  for _,unit in player:GetUnits():Members() do
    local def=GameInfo.Units[unit:GetUnitType()]
    if def and BaiqiPolicy.CivilianType(def.UnitType) then
      local unitKey=UnitKey(unit)
      if not unitEvaluated[unitKey] and pendingUnits[unit:GetID()]==nil then
        local snapshot=UnitSnapshot(unit,state)
        local allowed,denied
        if snapshot.plot~=nil then allowed,denied=BaiqiPolicy.CanCivilian(ctx,snapshot) end
        if denied=="owner_mismatch" then
          Reason("civilian-eligibility:"..tostring(snapshot.id),"文职所有权变更或无法确认，等待可核验的己方单位状态")
        elseif denied=="formation_or_unknown" then
          Reason("civilian-eligibility:"..tostring(snapshot.id),"文职处于护送编队或编队信息不明，等待可确认的独立状态")
        end
        if snapshot.plot~=nil and allowed then
          unitEvaluated[unitKey]=true
          if snapshot.type=="UNIT_SETTLER" then
            local submitted,continuing=ProcessSettler(ctx,player,state,unit)
            if submitted then status="已提交移民操作，等待实际结果"; return end
            if continuing==true then
              unitEvaluated[unitKey]=nil
              status="移民继续检查安全路线；军队由你指挥"
              return
            end
          elseif snapshot.type=="UNIT_BUILDER" then
            local submitted,continuing=ProcessBuilder(ctx,player,state,unit)
            if submitted then status="已提交建造者操作，等待实际结果"; return end
            if continuing==true then
              unitEvaluated[unitKey]=nil
              status="建造者继续检查安全路线；军队由你指挥"
              return
            end
          elseif snapshot.type=="UNIT_TRADER" then
            if ProcessTrader(ctx,player,state,unit) then status="已提交国内商路，等待实际结果";return end
          elseif snapshot.type=="UNIT_MISSIONARY" then
            if missionaryPurchase.Held() then
              unitEvaluated[unitKey]=nil
            elseif ProcessMissionary(ctx,player,state,unit) then
              status="已登记传教士国内任务；等待实际结果";return
            end
          elseif snapshot.type=="UNIT_NATURALIST" then
            local submitted,continuing=ProcessNaturalist(ctx,player,state,unit)
            if submitted then status="已登记自然学家公园任务；等待实际公园";return end
            if continuing then
              unitEvaluated[unitKey]=nil
              status="自然学家继续检查安全路线；军队由你指挥"
              return
            end
          elseif snapshot.type=="UNIT_ARCHAEOLOGIST" then
            local submitted,continuing=ProcessArchaeologist(ctx,player,state,unit)
            if submitted then status="已提交国内考古任务，等待实际文物";return end
            if continuing then unitEvaluated[unitKey]=nil;return end
          elseif BaiqiPolicy.DistrictGreatPersonClass(snapshot.type) then
            local submitted,continuing=ProcessDistrictPerson(ctx,player,state,unit)
            if submitted then status="已提交文职伟人内政任务，等待实际结果";return end
            if continuing==true then
              unitEvaluated[unitKey]=nil
              status="文职伟人继续检查安全路线；军队由你指挥"
              return
            end
          elseif BaiqiPolicy.CreativeGreatPersonClass(snapshot.type) then
            if ProcessCreative(ctx,player,state,unit) then status="已提交自动创作，等待实际作品";return end
          elseif snapshot.type=="UNIT_GREAT_PROPHET" then
            local submitted,quarantined=ProcessProphet(ctx,player,state,unit)
            if submitted then status="先知自动前往圣地并取得建教资格，等待实际结果";return end
            if quarantined then status="先知等待持久化许可与新鲜身份核对；其他内政继续执行";return end
          end
          local held=CivilianWorkHeld(unit,snapshot.type,unitKey)
          local here=not held and UnitPlot(unit)
          if here and RequestCivilian(ctx,state,unit,"SKIP_TURN",here) then
            status="文职单位本回合等待安全任务；军队由你指挥";return
          end
          if not held and ClearCivilianOverlap(ctx,player,state,unit) then
            status="文职单位自动移出重叠地块；军队由你指挥";return
          end
        end
      end
      local waiting=pendingUnits[unit:GetID()]
      if (not waiting and unitEvaluated[UnitKey(unit)]==true)
        or (waiting and waiting.persistent and (waiting.elapsed or 0)>=C.productionObservationSeconds) then
        if RequestCivilianStandby(unit) then
          status="文职单位本回合自动待命；原能力回执继续保留";return
        end
        if not waiting and RetryCivilianOverlap(ctx,player,state,unit)then
          status="文职单位重新检查并移出重叠地块；军队由你指挥";return
        end
      end
    end
  end
end

function BaiqiController.RunNow(allowOrders)
  if running or stopped then return end
  running=true
  local ok,err=pcall(Tick,allowOrders)
  running=false
  if not ok then stopped=true; status="托管因脚本错误停止，请查看 Lua.log"; Log("error",tostring(err)) end
end

function BaiqiController.Update(delta,allowOrders)
  local ctx=PlayerContext()
  if not ctx or ctx.activeTurn~=true then return end
  for _,pending in pairs(pendingUnits) do pending.elapsed=(pending.elapsed or 0)+delta end
  for _,pending in pairs(pendingCities) do pending.elapsed=(pending.elapsed or 0)+delta end
  if pendingPurchase then pendingPurchase.elapsed=(pendingPurchase.elapsed or 0)+delta end
  elapsed=elapsed+delta
  if elapsed>=C.interval then elapsed=0; BaiqiController.RunNow(allowOrders) end
end

function BaiqiController.GetStatus() return status end

local function OnCityCompleted(playerID,cityID)
  if playerID==Game.GetLocalPlayer() then BaiqiController.RefreshProduction() end
end
Events.CityProductionCompleted.Add(OnCityCompleted)
-- Loading another world may reuse the same native function bindings.
if Events.LoadGameViewStateDone then Events.LoadGameViewStateDone.Add(ClearNeighborhoods) end
local function OnUnitCountChanged(playerID)
  if playerID==Game.GetLocalPlayer() then BaiqiController.RefreshProduction() end
end
if Events.UnitAddedToMap then Events.UnitAddedToMap.Add(OnUnitCountChanged) end
if Events.UnitRemovedFromMap then Events.UnitRemovedFromMap.Add(OnUnitCountChanged) end
local function OnGreatPersonActivated(playerID,unitID,classID,individualID)
  local ctx=PlayerContext()
  local pending=pendingUnits[unitID]
  local class=GameInfo.GreatPersonClasses and GameInfo.GreatPersonClasses[classID]
  local individual=GameInfo.GreatPersonIndividuals and GameInfo.GreatPersonIndividuals[individualID]
  if ctx and ctx.player==playerID and class and individual then
    GPBridge("Observe",playerID,unitID,classID,individualID)
    ProphetBridge("Observe",playerID,unitID,classID,individualID)
    if pending and pending.persistent then pending.receiptDirty=true end
  end
  local expected=pending and ((pending.kind=="FOUND_RELIGION" and "GREAT_PERSON_CLASS_PROPHET")
    or (pending.kind=="ACTIVATE_GREAT_PERSON" and BaiqiPolicy.DistrictGreatPersonClass(pending.unitType)))
  if ctx and ctx.player==playerID and class and individual and pending and expected
    and class.Index==pending.class and individual.Index==pending.individual
    and class.GreatPersonClassType==expected and individual.GreatPersonClassType==expected then
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
  ClearNeighborhoods()
  Events.CityProductionCompleted.Remove(OnCityCompleted)
  if Events.LoadGameViewStateDone then Events.LoadGameViewStateDone.Remove(ClearNeighborhoods) end
  if Events.UnitAddedToMap then Events.UnitAddedToMap.Remove(OnUnitCountChanged) end
  if Events.UnitRemovedFromMap then Events.UnitRemovedFromMap.Remove(OnUnitCountChanged) end
  if Events.UnitGreatPersonActivated then Events.UnitGreatPersonActivated.Remove(OnGreatPersonActivated) end
  if Events.GreatWorkCreated then Events.GreatWorkCreated.Remove(OnGreatWorkCreated) end
end
print("BAIQI|ui_controller_loaded|version=2|mandatory_admin=true")
