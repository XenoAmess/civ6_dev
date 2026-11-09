-- Read-only QA. A map class cap minus founded religions is not an available slot.
local M={}
local function Integer(v)
  return type(v)=="number" and v==v and v>-math.huge and v<math.huge
    and v>=0 and v<=2147483647 and v%1==0
end
local function Unknown(reason)return {status="UNKNOWN",reason=reason}end
function M.Read(E)
  local ok,result=pcall(function()
    if type(E)~="table" then return Unknown("ports") end
    local index=E.Map.GetMapSize()
    if not Integer(index) then return Unknown("map_index") end
    local map=E.GameInfo.Maps[index]
    local kind=map and map.MapSizeType
    if type(kind)~="string" or #kind<1 or #kind>96 then return Unknown("map_row") end
    local cap,matched,n=nil,false,0
    -- Preserve all generic-for iterator returns. At most 512 data rows; a
    -- further row is only an overflow witness and its fields are never read.
    for row in E.GameInfo.Map_GreatPersonClasses() do
      n=n+1;if n>512 then return Unknown("class_row_bound") end
      if row.MapSizeType==kind and row.GreatPersonClassType=="GREAT_PERSON_CLASS_PROPHET" then
        if matched then return Unknown("duplicate_prophet_row") end
        matched=true
        if not Integer(row.MaxWorldInstances) then return Unknown("class_cap") end
        cap=row.MaxWorldInstances
      end
    end
    if not matched then return Unknown("missing_prophet_row") end
    local religion=E.Game.GetReligion()
    if religion==nil then return Unknown("religion_object") end
    local list=religion:GetReligions()
    if type(list)~="table" or getmetatable(list)~=nil then return Unknown("religion_list") end
    local length,highest=0,0
    for key in pairs(list) do
      length=length+1
      if length>64 or not Integer(key) or key<1 or key>64 then return Unknown("religion_list_shape") end
      if key>highest then highest=key end
    end
    if highest~=length then return Unknown("sparse_religion_list") end
    local founded,ids,records=0,{},{}
    for i=1,length do
      local info=list[i]
      if type(info)~="table" or getmetatable(info)~=nil or records[info] then return Unknown("religion_record") end
      records[info]=true
      local id=info.Religion
      if not Integer(id) or ids[id] then return Unknown("religion_id") end
      ids[id]=true
      local definition=E.GameInfo.Religions[id]
      local pantheon=definition and definition.Pantheon
      if type(pantheon)~="boolean" then return Unknown("religion_definition") end
      if not pantheon then
        local value=religion:HasBeenFounded(id)
        if type(value)~="boolean" then return Unknown("founded_flag") end
        if value then founded=founded+1 end
      end
    end
    return {status="OK",reason="map_class_counts_only_not_founder_availability",
      mapSizeIndex=index,mapSizeType=kind,mapClassCap=cap,foundedCount=founded,
      arithmeticDifference=cap-founded}
  end)
  if not ok then return Unknown("native_read_error") end
  return result
end
return M
