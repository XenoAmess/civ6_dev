-- Read-only proposals. A result never authorizes movement or a special action.
local function Integer(value)
  return type(value)=="number" and value>=0 and value<=2147483647 and value%1==0
end
local function Object(value)
  return type(value)=="table" or type(value)=="userdata"
end
local function Method(object,name)
  assert(Object(object) and type(object[name])=="function")
  return object[name]
end
local function Collect(unitType,pid,unit,game,map,visibility)
  if unitType~="UNIT_NATURALIST" and unitType~="UNIT_ARCHAEOLOGIST" then return {},"unsupported" end
  if not Integer(pid) then return {},"invalid" end
  local ok,result=pcall(function()
    local indices
    if unitType=="UNIT_NATURALIST" then
      local parks=Method(game,"GetNationalParks")()
      indices=Method(parks,"GetPossibleParkTiles")(parks,pid)
    else
      local archaeology=Method(unit,"GetArchaeology")(unit)
      indices=Method(archaeology,"GetActivationHighlightPlots")(archaeology)
    end
    assert(type(indices)=="table")
    Method(map,"GetPlotByIndex")
    Method(visibility,"IsRevealed");Method(visibility,"IsVisible")
    local accepted,seen={},{}
    for _,index in ipairs(indices) do
      if Integer(index) and not seen[index] then
        seen[index]=true
        local plot=map.GetPlotByIndex(index)
        if plot and Method(plot,"GetIndex")(plot)==index then
          local x,y=Method(plot,"GetX")(plot),Method(plot,"GetY")(plot)
          if Integer(x) and Integer(y) and visibility:IsRevealed(x,y)==true
            and visibility:IsVisible(x,y)==true and Method(plot,"GetOwner")(plot)==pid then
            accepted[#accepted+1]=index
          end
        end
      end
    end
    table.sort(accepted)
    return accepted
  end)
  if not ok then return {},"unavailable" end
  return result,"ok"
end
BaiqiHeritageCandidates={Collect=Collect}
return Collect
