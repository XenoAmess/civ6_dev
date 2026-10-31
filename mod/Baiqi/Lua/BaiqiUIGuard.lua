-- Per UI context only. The invisible AI executor does not import this module.
include("BaiqiConfig")
if BaiqiUIGuard~=nil then return end
include("BaiqiPolicy")
BaiqiUIGuard={}
local NativePlayers,NativeUnit,NativeCity,NativeUI=Players,UnitManager,CityManager,UI

function BaiqiUIGuard.PlayerID()
  local pid=Game.GetLocalPlayer()
  if pid==nil or pid<0 or GameConfiguration.IsAnyMultiplayer()
    or (GameConfiguration.IsHotseat~=nil and GameConfiguration.IsHotseat()) then return nil end
  local p,c=NativePlayers[pid],PlayerConfigurations[pid]
  if p==nil or c==nil or c:GetLeaderTypeName()~=BaiqiConfig.leader then return nil end
  local human=c.IsHuman and c:IsHuman() or (p.IsHuman and p:IsHuman())
  if human~=true then return nil end
  return pid
end

function BaiqiUIGuard.Civilian(unit)
  local pid=BaiqiUIGuard.PlayerID()
  if pid==nil or unit==nil or unit:GetOwner()~=pid then return false end
  local definition=GameInfo.Units[unit:GetUnitType()]
  return definition~=nil and BaiqiPolicy.CivilianType(definition.UnitType)
end

-- Native colon methods must receive the real native instance, not the proxy table.
local function ObjectProxy(native,blocked)
  local cache={}
  local proxy={}
  return setmetatable(proxy,{__index=function(_,key)
    local value=native[key]
    if type(value)~="function" then return value end
    if cache[key]==nil then
      cache[key]=function(_,...)
        if BaiqiUIGuard.PlayerID()~=nil and blocked[key] then return false end
        return value(native,...)
      end
    end
    return cache[key]
  end})
end

local function BlockUnit(unit,command,params)
  if BaiqiUIGuard.Civilian(unit) then return true end
  if BaiqiUIGuard.PlayerID()~=nil and UnitCommandTypes.ENTER_FORMATION~=nil
    and command==UnitCommandTypes.ENTER_FORMATION and type(params)=="table" then
    local pid,id=params[UnitCommandTypes.PARAM_UNIT_PLAYER],params[UnitCommandTypes.PARAM_UNIT_ID]
    local p=pid~=nil and NativePlayers[pid]
    local target=p and id~=nil and p:GetUnits():FindID(id)
    if BaiqiUIGuard.Civilian(target) then return true end
  end
  return false
end

UnitManager=setmetatable({
  RequestOperation=function(unit,operation,params,...)
    if BaiqiUIGuard.Civilian(unit) then return false end
    return NativeUnit.RequestOperation(unit,operation,params,...)
  end,
  RequestCommand=function(unit,command,params,...)
    if BlockUnit(unit,command,params) then return false end
    return NativeUnit.RequestCommand(unit,command,params,...)
  end,
  CanStartOperation=function(unit,...)
    if BaiqiUIGuard.Civilian(unit) then return false end
    return NativeUnit.CanStartOperation(unit,...)
  end,
  CanStartCommand=function(unit,...)
    if BaiqiUIGuard.Civilian(unit) then return false end
    return NativeUnit.CanStartCommand(unit,...)
  end,
},{__index=NativeUnit})

local function OwnCity(city)
  local pid=BaiqiUIGuard.PlayerID()
  return pid~=nil and city~=nil and city:GetOwner()==pid
end
local function CityCombat(command)
  return CityCommandTypes~=nil and ((CityCommandTypes.RANGE_ATTACK~=nil and command==CityCommandTypes.RANGE_ATTACK)
    or (CityCommandTypes.WMD_STRIKE~=nil and command==CityCommandTypes.WMD_STRIKE))
end
CityManager=setmetatable({
  CanStartOperation=function(city,...)
    if OwnCity(city) then return false end
    return NativeCity.CanStartOperation(city,...)
  end,
  CanStartCommand=function(city,command,...)
    if OwnCity(city) and not CityCombat(command) then return false end
    return NativeCity.CanStartCommand(city,command,...)
  end,
  RequestOperation=function(city,operation,...)
    if OwnCity(city) then return false end
    return NativeCity.RequestOperation(city,operation,...)
  end,
  RequestCommand=function(city,command,...)
    if OwnCity(city) and not CityCombat(command) then return false end
    return NativeCity.RequestCommand(city,command,...)
  end,
},{__index=NativeCity})

UI=setmetatable({RequestPlayerOperation=function(pid,operation,params,...)
  if pid==BaiqiUIGuard.PlayerID() then
    local cityRequest=operation==PlayerOperations.EXECUTE_SCRIPT and type(params)=="table"
      and params.OnStart=="BaiqiRequisition" and params.confirmed==true and params.kind=="city"
    local military=(PlayerOperations.DIPLOMACY_MAKE_PEACE~=nil and operation==PlayerOperations.DIPLOMACY_MAKE_PEACE)
      or (PlayerOperations.LEVY_MILITARY~=nil and operation==PlayerOperations.LEVY_MILITARY)
    if not cityRequest and not military then return false end
  end
  return NativeUI.RequestPlayerOperation(pid,operation,params,...)
end},{__index=NativeUI})

local playerCache={}
Players=setmetatable({},{__index=function(_,pid)
  local native=NativePlayers[pid]
  if native==nil or pid~=BaiqiUIGuard.PlayerID() then return native end
  if playerCache[pid]~=nil then return playerCache[pid] end
  local player=ObjectProxy(native,{})
  local culture=native:GetCulture()
  local cultureProxy=ObjectProxy(culture,{RequestChangeGovernment=true,RequestPolicyChanges=true,SetGovernmentChangeConsidered=true})
  player.GetCulture=function() return cultureProxy end
  playerCache[pid]=player
  return player
end})
