"""Actual metadata provider and UI consumer in separate Lua environments.

Only native bindings/property storage are fake. No journal/permission algorithm
is mocked. UI property lag defaults on; Gameplay exposes GetType, not GetUnitType.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def install_gp_bridge(lua, stored=None):
    lua.execute('''
local ui=_G
TestBridge={store={},writes=0,uiLag=true,allowWrite=true}
local h=TestBridge
local function copy(value)
 if type(value)~='table' then return value end
 local result={};for key,item in pairs(value) do result[key]=copy(item) end;return result
end
h.Copy=copy
local function wrap(unit)
 return {GetID=function() return unit:GetID() end,GetOwner=function() return unit:GetOwner() end,
  GetType=function() return unit:GetUnitType() end,
  GetX=function() return unit:GetX() end,GetY=function() return unit:GetY() end,
  GetMovesRemaining=function() return unit:GetMovesRemaining() end,
  GetFormationUnitCount=function() return unit:GetFormationUnitCount() end,
  GetGreatPerson=function() return unit.GetGreatPerson and unit:GetGreatPerson() end}
end
local corePlayer={IsHuman=function() return ui.PlayerConfigurations[7]:IsHuman() end,
 IsTurnActive=function() return ui.Players[7]:IsTurnActive() end,
 GetProperty=function(_,key) return copy(h.store[key]) end,
 SetProperty=function(_,key,value)
  h.writes=h.writes+1
  if h.writeError then error('injected property exception') end
  if h.allowWrite then h.store[key]=copy(value) end
 end,
 GetUnits=function()
  local units=ui.Players[7]:GetUnits()
  return {FindID=function(_,id) local u=units:FindID(id);return u and wrap(u) end,
   Members=function()
    local iter=units:Members()
    return function() local index,u=iter();if u then return index,wrap(u) end end
   end}
 end}
local allowed={type=true,pairs=true,ipairs=true,pcall=true,tostring=true,select=true,
 math=true,string=true,table=true,Game=true,GameInfo=true,GameConfiguration=true,
 Map=true,PlayersVisibility=true,print=true}
ExposedMembers={}
local listeners={}
local function event()
 return {Add=function(fn) listeners[#listeners+1]=fn end}
end
local core={include=function() end,Players={[7]=corePlayer},
 PlayerConfigurations={[7]={GetLeaderTypeName=function() return ui.PlayerConfigurations[7]:GetLeaderTypeName() end}},
 ExposedMembers=ExposedMembers,GameEvents={OnGameTurnStarted=event(),BaiqiRequisitionRecover=event()}}
setmetatable(core,{__index=function(_,key) if allowed[key] then return ui[key] end end})
core._G=core
h.core=core
function h.FireBootstrap() for _,fn in ipairs(listeners) do fn() end end
local previous=ui.Players[7].GetProperty
ui.Players[7].GetProperty=function(self,key)
 if key=='BAIQI_GREAT_PERSON_INTENTS_V1' then
  if h.uiLag then return nil end
  return copy(h.store[key])
 end
 return previous(self,key)
end
''')
    load = lua.eval('function(source,name,env) local fn,err=load(source,name,"t",env);assert(fn,err);return fn() end')
    core = lua.globals().TestBridge.core
    if stored is not None:
        lua.globals().TestBridge.store = lua.globals().TestBridge.Copy(stored)
    for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiRequisition', 'BaiqiGPJournal', 'BaiqiGPIntentGameplay'):
        load((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'), name, core)
