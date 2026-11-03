-- Data-row lookup only; caller must still qualify the exact native operation.
local function Resolve(unitType,operation,unitOperations)
  local valid = (unitType=="UNIT_NATURALIST" and operation=="DESIGNATE_PARK") or (unitType=="UNIT_ARCHAEOLOGIST" and operation=="EXCAVATE")
  if not valid then return nil,"unsupported" end
  if type(unitOperations)~="table" and type(unitOperations)~="userdata" then return nil,"unavailable" end
  local key = "UNITOPERATION_"..operation
  local ok,row = pcall(function() return unitOperations[key] end)
  if not ok or type(row)~="table" and type(row)~="userdata" then return nil,"unavailable" end
  local okType,opType = pcall(function() return row.OperationType end)
  if not okType or opType~=key then return nil,"unavailable" end
  local okHash,hash = pcall(function() return row.Hash end)
  if not okHash or type(hash)~="number" or hash~=hash or math.abs(hash)>=math.huge or hash<-2147483648 or hash>4294967295 or hash%1~=0 then return nil,"unavailable" end
  return hash,"ok"
end
BaiqiHeritageActions={Resolve=Resolve}
return Resolve
