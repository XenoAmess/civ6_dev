-- Native coastal-flood demand only. No technology, terrain or building writes.
BaiqiFlood={}
local function Integer(v)
  return type(v)=="number" and v==v and v>-math.huge and v<math.huge and v%1==0
end
local function Definition(E)
  local row=E.GameInfo.Buildings.BUILDING_FLOOD_BARRIER
  if not row or row.BuildingType~="BUILDING_FLOOD_BARRIER" or not Integer(row.Index) or row.Index<0
    or not Integer(row.Hash) or type(row.PrereqTech)~="string" or row.PrereqTech=="" then return nil end
  return row
end
function BaiqiFlood.Definition(E)
  local ok,row=pcall(Definition,E)
  if ok then return row end
end

-- true: known salvageable flooded district; false: known no such demand;
-- nil: unavailable, malformed or changing state. Never turn unknown into zero.
function BaiqiFlood.City(E,pid,cityID,turn)
  local ok,wanted=pcall(function()
    if not Integer(pid) or pid<0 or not Integer(cityID) or cityID<0 or not Integer(turn)
      or E.Game.GetLocalPlayer()~=pid or E.Game.GetCurrentGameTurn()~=turn then return nil end
    local player=E.Players[pid]
    local cities=player:GetCities()
    local city=cities:FindID(cityID)
    if not city or city:GetID()~=cityID or city:GetOwner()~=pid then return nil end
    local cx,cy=city:GetX(),city:GetY()
    if not Integer(cx) or not Integer(cy) then return nil end
    local row=Definition(E)
    if not row then return nil end
    local function Barrier(c)
      local b=c:GetBuildings()
      local has,pillaged=b:HasBuilding(row.Index),b:IsPillaged(row.Index)
      if type(has)~="boolean" or type(pillaged)~="boolean" or (not has and pillaged) then return nil end
      return has and not pillaged
    end
    local intact=Barrier(city)
    if intact==nil then return nil end
    local found,count=false,0
    if not intact then
      for _,d in city:GetDistricts():Members() do
        count=count+1
        if count>64 then return nil end
        local complete,pillaged=d:IsComplete(),d:IsPillaged()
        if type(complete)~="boolean" or type(pillaged)~="boolean" then return nil end
        if complete and pillaged then
          local x,y=d:GetX(),d:GetY()
          if not Integer(x) or not Integer(y) then return nil end
          local plot=E.Map.GetPlot(x,y)
          local vis=E.PlayersVisibility[pid]
          if not plot or plot:GetX()~=x or plot:GetY()~=y or plot:GetOwner()~=pid
            or vis:IsVisible(x,y)~=true or vis:IsRevealed(x,y)~=true then return nil end
          local low=E.TerrainManager.GetCoastalLowlandType(plot)
          if not Integer(low) or low< -1 or low>2 then return nil end
          if low>=0 then
            local flooded,submerged=E.TerrainManager.IsFlooded(plot),E.TerrainManager.IsSubmerged(plot)
            if type(flooded)~="boolean" or type(submerged)~="boolean" then return nil end
            if flooded and not submerged then found=true end
          end
        end
      end
    end
    -- Reads are sequential, not an atomic snapshot. Reject detected changes.
    local latest=E.Players[pid]:GetCities():FindID(cityID)
    if not latest or latest:GetID()~=cityID or latest:GetOwner()~=pid
      or latest:GetX()~=cx or latest:GetY()~=cy then return nil end
    local final=Barrier(latest)
    if final==nil or E.Game.GetLocalPlayer()~=pid or E.Game.GetCurrentGameTurn()~=turn then return nil end
    return not final and found
  end)
  if ok then return wanted end
end
