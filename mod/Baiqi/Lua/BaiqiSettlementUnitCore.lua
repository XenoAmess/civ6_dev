-- Identity facts only. CONSUMED is not a proof that this unit founded a city.
BaiqiSettlementUnitCore = {}
local M=BaiqiSettlementUnitCore
local MAX=2147483647
function M.Classify(J,E,pid,id)
  local ok,state,data,reason=pcall(function()
    if type(J)~="table" or type(E)~="table" or type(J.Integer)~="function"
      or type(J.UnitKey)~="function" or not J.Integer(pid,MAX)
      or not J.Integer(id,MAX) or not J.UnitKey(id) then return "UNKNOWN",nil,"input" end
    local player=E.Players[pid]
    if not player then return "UNKNOWN",nil,"player" end
    local units=player:GetUnits()
    local function Identity(unit)
      local uid,owner=unit:GetID(),unit:GetOwner()
      if not J.UnitKey(uid) or owner~=pid then return nil end
      return uid
    end
    local function Facts(unit)
      local uid=Identity(unit)
      if uid~=id then return nil end
      local index=unit:GetType()
      if not J.Integer(index,MAX) then return nil end
      local def=E.GameInfo.Units[index]
      if not def or def.UnitType~="UNIT_SETTLER" then return nil end
      local f={id=uid,unitType=def.UnitType,x=unit:GetX(),y=unit:GetY(),
        dead=unit:IsDead(),delayed=unit:IsDelayedDeath()}
      if f.dead==false and f.delayed==false then
        f.moves=unit:GetMovesRemaining();f.formation=unit:GetFormationUnitCount()
      end
      return f
    end
    local count,seen,member=0,{},nil
    for _,unit in units:Members() do
      count=count+1;if count>512 then return "UNKNOWN",nil,"inventory_bound" end
      local uid=Identity(unit);local key=uid and J.UnitKey(uid)
      if not key or seen[key] then return "UNKNOWN",nil,"inventory_identity" end
      seen[key]=true
      if uid==id then member=Facts(unit);if not member then return "UNKNOWN",nil,"member_type" end end
    end
    local lookup=units:FindID(id)
    if lookup==nil then
      if member then return "UNKNOWN",nil,"lookup_inventory_mismatch" end
      return "ABSENT",nil,"nil_lookup_and_full_inventory_absent"
    end
    local uid=Identity(lookup)
    if not uid then return "UNKNOWN",nil,"lookup_identity" end
    if uid~=id then return "ALIAS",{id=uid,requestedID=id},"full_id_alias" end
    local f=Facts(lookup)
    if not f or not member then return "UNKNOWN",nil,"lookup_inventory_mismatch" end
    for _,k in ipairs({"id","unitType","x","y","dead","delayed","moves","formation"}) do
      if f[k]~=member[k] then return "UNKNOWN",nil,"facts_changed" end
    end
    if f.dead==false and f.delayed==true and f.x==-9999 and f.y==-9999 then
      return "CONSUMED",f,"exact_offmap_delayed_settler"
    end
    if f.dead==false and f.delayed==false and J.Integer(f.x,MAX) and J.Integer(f.y,MAX)
      and type(f.moves)=="number" and f.moves==f.moves and f.moves>=0 and f.moves<=1000000
      and J.Integer(f.formation,128) and f.formation>=1 then return "LIVE",f,"live_settler" end
    return "UNKNOWN",nil,"unclassified"
  end)
  if not ok then return "UNKNOWN",nil,"handler_error" end
  return state,data,reason
end
