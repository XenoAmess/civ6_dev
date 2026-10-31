-- Operating rights are real, property-gated native food/housing modifiers.
-- Buildings remain in their original city. This first profile supports Granary only.
BaiqiRights = {}
local C = BaiqiConfig
local function Integer(n) return BaiqiPolicy.Number(n) and n>=0 and n==math.floor(n) end
local function State()
  local state=Game.GetProperty(C.rightsKey)
  if state==nil then return {version=1,leases={}} end
  if type(state)~="table" or state.version~=1 or type(state.leases)~="table" then return nil end
  local count=0
  for key,lease in pairs(state.leases) do
    if type(lease)~="table" or type(lease.id)~="string" or #lease.id>128
      or not Integer(lease.sourceIndex) or not Integer(lease.recipientIndex)
      or key~=tostring(lease.sourceIndex) or not Integer(lease.sourceOwner) or not Integer(lease.sourceCityID)
      or not Integer(lease.recipientPlayer) or not Integer(lease.recipientCityID)
      or (lease.status~="ACTIVE" and lease.status~="SUSPENDED" and lease.status~="EXPIRED") then return nil end
    if lease.status~="EXPIRED" then count=count+1 end
  end
  if count>C.maxRights then return nil end
  return state
end
local function Save(state) Game.SetProperty(C.rightsKey,state) end
local function At(index)
  local plot=Map.GetPlotByIndex(index)
  return plot,plot and CityManager.GetCityAt(plot:GetX(),plot:GetY())
end
local function Set(plot,key,value)
  if plot and plot:GetProperty(key)~=value then plot:SetProperty(key,value) end
end

function BaiqiRights.Supported()
  local row=GameInfo.Buildings.BUILDING_GRANARY
  if row==nil or row.Housing~=2 or row.Maintenance~=0 then return false end
  local count=0
  for yield in GameInfo.Building_YieldChanges() do
    if yield.BuildingType==row.BuildingType then
      if yield.YieldType~="YIELD_FOOD" or yield.YieldChange~=1 then return false end
      count=count+1
    end
  end
  if count~=1 then return false end
  local modifiers=0
  for modifier in GameInfo.BuildingModifiers() do
    if modifier.BuildingType==row.BuildingType then
      if modifier.ModifierId~="BAIQI_GRANARY_OUT_FOOD" and modifier.ModifierId~="BAIQI_GRANARY_OUT_HOUSING" then return false end
      modifiers=modifiers+1
    end
  end
  return modifiers==2
end

function BaiqiRights.Check(playerID,sourceCity,recipientID)
  if not BaiqiRights.Supported() then return nil,"building_profile_unsupported" end
  local row=GameInfo.Buildings.BUILDING_GRANARY
  local buildings=sourceCity:GetBuildings()
  if buildings:HasBuilding(row.Index)~=true or buildings:IsPillaged(row.Index) then return nil,"no_operating_granary" end
  local state=State()
  if state==nil then return nil,"rights_version" end
  local source=Map.GetPlot(sourceCity:GetX(),sourceCity:GetY())
  local previous=state.leases[tostring(source:GetIndex())]
  if previous~=nil and (type(previous)~="table" or previous.status~="EXPIRED") then return nil,"already_controlled" end
  local count=0
  for _,lease in pairs(state.leases) do
    if type(lease)~="table" then return nil,"rights_version" end
    if lease.status~="EXPIRED" then count=count+1 end
  end
  if count>=C.maxRights then return nil,"rights_limit" end
  local recipient
  for _,city in Players[playerID]:GetCities():Members() do
    if recipientID~=nil then
      if city:GetID()==recipientID then recipient=city; break end
    elseif recipient==nil or city:GetID()<recipient:GetID() then recipient=city end
  end
  if recipient==nil or recipient:GetOwner()~=playerID then return nil,"no_recipient_city" end
  return {sourceIndex=source:GetIndex(),recipientCityID=recipient:GetID(),recipientX=recipient:GetX(),recipientY=recipient:GetY(),
    recipientIndex=Map.GetPlot(recipient:GetX(),recipient:GetY()):GetIndex()}
end

local refreshing,swept,invalidCleared=false,false,false
local function Sweep(outgoing,incoming)
  for index=0,Map.GetPlotCount()-1 do
    local plot=Map.GetPlotByIndex(index)
    if plot and plot:GetProperty("BAIQI_GRANARY_OUT")~=nil then Set(plot,"BAIQI_GRANARY_OUT",outgoing[index] or 0) end
    if plot and plot:GetProperty("BAIQI_GRANARY_IN")~=nil then Set(plot,"BAIQI_GRANARY_IN",incoming[index] or 0) end
  end
end
function BaiqiRights.Refresh()
  if refreshing then return end
  refreshing=true
  local ok,err=pcall(function()
    local state=State()
    if state==nil then
      if not invalidCleared then Sweep({},{}); invalidCleared=true; print("BAIQI|rights_invalid|effects_disabled") end
      return false
    end
    invalidCleared=false
    local outgoing,incoming={},{}
    local supported=BaiqiRights.Supported()
    for _,lease in pairs(state.leases) do
      if type(lease)=="table" and type(lease.sourceIndex)=="number" and type(lease.recipientIndex)=="number" then
        outgoing[lease.sourceIndex]=0; incoming[lease.recipientIndex]=0
      end
    end
    for _,lease in pairs(state.leases) do
      if type(lease)=="table" and lease.status~="EXPIRED" then
        local sourcePlot,sourceCity=At(lease.sourceIndex)
        local recipientPlot,recipientCity=At(lease.recipientIndex)
        local row=GameInfo.Buildings.BUILDING_GRANARY
        if sourceCity==nil or recipientCity==nil or sourceCity:GetOwner()~=lease.sourceOwner
          or sourceCity:GetID()~=lease.sourceCityID or recipientCity:GetOwner()~=lease.recipientPlayer
          or recipientCity:GetID()~=lease.recipientCityID or row==nil
          or sourceCity:GetBuildings():HasBuilding(row.Index)~=true then
          lease.status="EXPIRED"; lease.reason="asset_or_owner_changed"
        elseif not supported or sourceCity:GetBuildings():IsPillaged(row.Index) then
          lease.status="SUSPENDED"; lease.reason=not supported and "profile_changed" or "pillaged"
        else
          lease.status="ACTIVE"; lease.reason="operating"
          outgoing[lease.sourceIndex]=1
          incoming[lease.recipientIndex]=(incoming[lease.recipientIndex] or 0)+1
        end
      end
    end
    Save(state)
    if not swept then Sweep(outgoing,incoming); swept=true end
    for index,count in pairs(outgoing) do Set(Map.GetPlotByIndex(index),"BAIQI_GRANARY_OUT",count) end
    for index,count in pairs(incoming) do Set(Map.GetPlotByIndex(index),"BAIQI_GRANARY_IN",count) end
  end)
  refreshing=false
  if not ok then print("BAIQI|rights_refresh_error|"..tostring(err)) end
  return ok and State()~=nil
end

function BaiqiRights.Grant(quote,operationID)
  local source=CityManager.GetCityAt(quote.x,quote.y)
  if source==nil or source:GetOwner()~=quote.targetOwner or source:GetID()~=quote.cityID then return false end
  local checked=BaiqiRights.Check(quote.playerID,source,quote.recipientCityID)
  if checked==nil or checked.recipientIndex~=quote.recipientIndex or checked.sourceIndex~=quote.sourceIndex then return false end
  local state=State()
  if state==nil then return false end
  state.leases[tostring(quote.sourceIndex)]={id=operationID,sourceIndex=quote.sourceIndex,sourceOwner=quote.targetOwner,
    sourceCityID=quote.cityID,recipientPlayer=quote.playerID,recipientCityID=quote.recipientCityID,
    recipientIndex=quote.recipientIndex,status="ACTIVE",grantedTurn=quote.turn}
  Save(state)
  if not BaiqiRights.Refresh() then return false end
  local seen=State()
  local lease=seen and seen.leases[tostring(quote.sourceIndex)]
  local sourcePlot=Map.GetPlotByIndex(quote.sourceIndex)
  local recipientPlot=Map.GetPlotByIndex(quote.recipientIndex)
  return lease~=nil and lease.id==operationID and lease.status=="ACTIVE"
    and sourcePlot:GetProperty("BAIQI_GRANARY_OUT")==1 and (recipientPlot:GetProperty("BAIQI_GRANARY_IN") or 0)>=1
end
