-- Known visible site facts only; a city alone is not a founding receipt.
BaiqiSettlementTileCore = {}
local M = BaiqiSettlementTileCore
local MAX = 2147483647

local function Plain(t) return type(t) == "table" and getmetatable(t) == nil end

local function IsInt(v, max)
  return type(v) == "number" and v == v and v >= 0 and v <= max and v == math.floor(v)
end

function M.Read(J, E, pid, index, x, y)
  local ok, state, data, reason = pcall(function()
    -- 1. Validate Inputs and Environment
    if not Plain(J) or not Plain(E) then return "UNKNOWN", nil, "invalid_env" end
    if type(J.Integer) ~= "function" or not J.Integer(pid, MAX) or not J.Integer(index, MAX) or not J.Integer(x, MAX) or not J.Integer(y, MAX) then
      return "UNKNOWN", nil, "invalid_coords"
    end

    -- 2. Validate Core Dependencies (Static Dot API)
    if not E.Map or type(E.Map.GetGridSize) ~= "function" then return "UNKNOWN", nil, "missing_grid_size" end
    if not E.Map.GetPlotByIndex or type(E.Map.GetPlotByIndex) ~= "function" then return "UNKNOWN", nil, "missing_plot_lookup" end
    if not E.CityManager or type(E.CityManager.GetCityAt) ~= "function" then return "UNKNOWN", nil, "missing_city_lookup" end
    if not E.PlayersVisibility or type(E.PlayersVisibility) ~= "table" then return "UNKNOWN", nil, "missing_visibility" end
    if not E.Players or type(E.Players) ~= "table" then return "UNKNOWN", nil, "missing_players" end

    -- 3. Get Grid Dimensions
    local gw, gh = E.Map.GetGridSize()
    if not IsInt(gw, 65536) or not IsInt(gh, 65536) then return "UNKNOWN", nil, "invalid_grid_dims" end
    if gw < 1 or gh < 1 then return "UNKNOWN", nil, "invalid_grid_dims" end
    if gw * gh > MAX then return "UNKNOWN", nil, "grid_overflow" end

    -- 4. Validate Coordinates against Grid
    if x < 0 or x >= gw or y < 0 or y >= gh then return "UNKNOWN", nil, "out_of_bounds" end
    if index < 0 or index >= gw * gh then return "UNKNOWN", nil, "out_of_bounds" end

    -- 5. Visibility Check (Must be true to read content)
    local vis = E.PlayersVisibility[pid]
    if not vis or type(vis.IsRevealed) ~= "function" or type(vis.IsVisible) ~= "function" then
      return "UNKNOWN", nil, "missing_visibility_api"
    end
    if vis:IsRevealed(x, y) ~= true or vis:IsVisible(x, y) ~= true then
      return "UNKNOWN", nil, "not_visible"
    end

    -- 6. Get Plot
    local plot = E.Map.GetPlotByIndex(index)
    if not plot then return "UNKNOWN", nil, "plot_nil" end
    if type(plot.GetIndex) ~= "function" or type(plot.GetX) ~= "function" or type(plot.GetY) ~= "function" or
       type(plot.IsCity) ~= "function" or type(plot.GetOwner) ~= "function" then
      return "UNKNOWN", nil, "plot_api_missing"
    end

    local pIdx = plot:GetIndex()
    local pX = plot:GetX()
    local pY = plot:GetY()
    if not IsInt(pIdx, MAX) or not IsInt(pX, MAX) or not IsInt(pY, MAX) then return "UNKNOWN", nil, "plot_coords_invalid" end
    if pIdx ~= index or pX ~= x or pY ~= y then return "UNKNOWN", nil, "plot_mismatch" end

    local isCity = plot:IsCity()
    if type(isCity) ~= "boolean" then return "UNKNOWN", nil, "is_city_not_bool" end

    local owner = plot:GetOwner()
    if owner ~= -1 and not IsInt(owner, MAX) then return "UNKNOWN", nil, "owner_invalid" end
    if owner < -1 then return "UNKNOWN", nil, "owner_negative" end

    -- 7. City Lookup
    local city = E.CityManager.GetCityAt(x, y)
    if city ~= nil and type(city.GetID) ~= "function" then return "UNKNOWN", nil, "city_api_missing" end

    if isCity == false then
      if city ~= nil then return "UNKNOWN", nil, "city_exists_but_not_flagged" end
      -- EMPTY
      return "EMPTY", {plot=index, x=x, y=y, owner=owner, empty=true}, nil
    end

    -- isCity == true
    if city == nil then return "UNKNOWN", nil, "city_flagged_but_nil" end

    local cID = city:GetID()
    local cOwner = city:GetOwner()
    local cX = city:GetX()
    local cY = city:GetY()

    if not IsInt(cID, MAX) or not IsInt(cOwner, MAX) or not IsInt(cX, MAX) or not IsInt(cY, MAX) then
      return "UNKNOWN", nil, "city_data_invalid"
    end
    if cX ~= x or cY ~= y then return "UNKNOWN", nil, "city_coords_mismatch" end
    if owner ~= cOwner then return "UNKNOWN", nil, "owner_mismatch" end

    if cOwner ~= pid then
      -- FOREIGN_CITY
      return "FOREIGN_CITY", {plot=index, x=x, y=y, owner=owner, cityID=cID, empty=false}, nil
    end

    -- cOwner == pid
    local player = E.Players[pid]
    if not player or type(player.GetCities) ~= "function" then return "UNKNOWN", nil, "player_api_missing" end
    local cities = player:GetCities()
    if not cities or type(cities.FindID) ~= "function" then return "UNKNOWN", nil, "cities_api_missing" end

    local foundCity = cities:FindID(cID)
    if not foundCity then return "UNKNOWN", nil, "city_not_in_roster" end

    local fID = foundCity:GetID()
    local fOwner = foundCity:GetOwner()
    local fX = foundCity:GetX()
    local fY = foundCity:GetY()

    if not IsInt(fID, MAX) or not IsInt(fOwner, MAX) or not IsInt(fX, MAX) or not IsInt(fY, MAX) then
      return "UNKNOWN", nil, "found_city_data_invalid"
    end
    if fID ~= cID or fOwner ~= pid or fX ~= x or fY ~= y then
      return "UNKNOWN", nil, "found_city_mismatch"
    end

    -- OWN_CITY
    return "OWN_CITY", {plot=index, x=x, y=y, owner=owner, cityID=cID, empty=false}, nil
  end)

  if not ok then return "UNKNOWN", nil, "exception" end
  return state, data, reason
end
