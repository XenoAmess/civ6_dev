-- UI-context own-city evidence only; no transfer or foreign-inventory proof.
local M = {}

local function integer(value, minimum, maximum)
  return type(value)=="number" and value==value and value~=math.huge and value~=-math.huge
    and value%1==0 and math.abs(value)<=9007199254740991
    and (minimum==nil or value>=minimum) and (maximum==nil or value<=maximum)
end

local function need(condition)
  if not condition then error("READ_FAILED",0) end
end

local function flag(value)
  need(type(value)=="boolean" or value==0 or value==1)
  return value==true or value==1
end

local function context(env)
  local pid=env.Game.GetLocalPlayer()
  need(pid==0 and env.GameConfiguration.IsAnyMultiplayer()==false)
  if env.GameConfiguration.IsHotseat~=nil then need(env.GameConfiguration.IsHotseat()==false) end
  need(env.PlayerConfigurations[pid]:GetLeaderTypeName()=="LEADER_BAIQI")
  local turn=env.Game.GetCurrentGameTurn()
  need(integer(turn,0))
  return pid,turn,env.Players[pid]
end

local function identity(city,pid,id)
  need(city~=nil and city:GetID()==id and city:GetOwner()==pid)
  local x,y,population=city:GetX(),city:GetY(),city:GetPopulation()
  need(integer(x,0) and integer(y,0) and integer(population,0))
  return x,y,population
end

local function read(env,cityId)
  need(integer(cityId,0))
  local pid,turn,player=context(env)
  local city=player:GetCities():FindID(cityId)
  local x,y,population=identity(city,pid,cityId)
  local buildings=city:GetBuildings()
  need(buildings~=nil)
  for _,name in ipairs({"HasBuilding","IsPillaged","GetNumGreatWorkSlots",
    "GetGreatWorkInSlot","GetGreatWorkTypeFromIndex"}) do
    need(type(buildings[name])=="function")
  end
  local result={turn=turn,player_id=pid,city_id=cityId,x=x,y=y,population=population,buildings={}}
  local count,seen=0,{}
  for row in env.GameInfo.Buildings() do
    count=count+1
    need(count<=4096 and type(row)=="table" and integer(row.Index,0))
    need(type(row.BuildingType)=="string" and #row.BuildingType>0 and not seen[row.Index])
    seen[row.Index]=true
    local wonder=flag(row.IsWonder)
    local present=buildings:HasBuilding(row.Index)
    need(type(present)=="boolean")
    if present then
      local item={index=row.Index,type=row.BuildingType,is_wonder=wonder,slots={}}
      item.pillaged=buildings:IsPillaged(row.Index)
      need(type(item.pillaged)=="boolean")
      item.slot_count=buildings:GetNumGreatWorkSlots(row.Index)
      need(integer(item.slot_count,0,64))
      for slot=0,item.slot_count-1 do
        local work=buildings:GetGreatWorkInSlot(row.Index,slot)
        need(integer(work,-1))
        local value={slot=slot,work=work}
        if work>=0 then
          value.type_index=buildings:GetGreatWorkTypeFromIndex(work)
          need(integer(value.type_index,0))
        end
        item.slots[#item.slots+1]=value
      end
      result.buildings[#result.buildings+1]=item
    end
  end
  table.sort(result.buildings,function(a,b) return a.index<b.index end)
  local freshPid,freshTurn,freshPlayer=context(env)
  need(freshPid==pid and freshTurn==turn)
  local fresh=freshPlayer:GetCities():FindID(cityId)
  local freshX,freshY,freshPopulation=identity(fresh,pid,cityId)
  need(freshX==x and freshY==y and freshPopulation==population)
  return result
end

function M.Read(env,cityId)
  local ok,result=pcall(read,env,cityId)
  if not ok then return nil,"READ_FAILED" end
  return result,nil
end

return M
