"""Run actual prophet Gameplay in a separate Core-shaped software environment."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def install_prophet_bridge(lua, stored=None, *, fresh=True, foreign=False):
    lua.execute("""
local ui=_G
TestPropBridge={store={},writes=0,allowWrite=true,findIDs={}}
local h=TestPropBridge
local function copy(v)
 if type(v)~='table' then return v end
 local out={};for k,item in pairs(v) do out[k]=copy(item) end;return out
end
h.Copy=copy
local function wrap(u)
 return {GetID=function() return u:GetID() end,GetOwner=function() return u:GetOwner() end,
  GetType=function() return u:GetUnitType() end,GetX=function() return u:GetX() end,GetY=function() return u:GetY() end,
  GetMovesRemaining=function() return u:GetMovesRemaining() end,
  GetFormationUnitCount=function() return u:GetFormationUnitCount() end,
  GetGreatPerson=function()
   if type(u.GetGreatPerson)~='function' then return nil end
   local gp=u:GetGreatPerson()
   return {GetIndividual=function() return gp:GetIndividual() end,GetClass=function() return gp:GetClass() end}
  end}
end
local corePlayer={
 IsHuman=function() return ui.PlayerConfigurations[7]:IsHuman() end,
 IsTurnActive=function() return ui.Players[7]:IsTurnActive() end,
 GetProperty=function(_,key)
  if h.failNextRead then h.failNextRead=false;return nil end
  return copy(h.store[key])
 end,
 SetProperty=function(_,key,value)
  h.writes=h.writes+1
  if h.writeError then error('injected property failure') end
  if h.allowWrite then h.store[key]=copy(value) end
  if h.loseWriteReadback then h.failNextRead=true end
  if h.afterWrite then h.afterWrite() end
 end,
 -- Native Core deliberately lacks UI's earned/founding getters.
 GetReligion=function() return {GetReligionTypeCreated=function() return ui.TestWorld.createdReligion end} end,
 GetUnits=function()
  local units=ui.Players[7]:GetUnits()
  return {
   FindID=function(_,id)
    h.findIDs[#h.findIDs+1]=id
    local u=units:FindID(id);return u and wrap(u)
   end,
   Members=function()
    local iter=units:Members()
    return function() local i,u=iter();if u then return i,wrap(u) end end
   end}
 end}
local map=setmetatable({GetPlot=function(x,y)
 local p=ui.Map.GetPlot(x,y)
 if not p then return nil end
 return {GetOwner=function() return p:GetOwner() end,IsWater=function() return ui.TestWorld.prophetWater==true end}
end},{__index=ui.Map})
local listeners={}
local function event() return {Add=function(fn) listeners[#listeners+1]=fn end} end
local allowed={type=true,pairs=true,ipairs=true,pcall=true,tostring=true,select=true,
 math=true,string=true,table=true,Game=true,GameInfo=true,GameConfiguration=true,PlayersVisibility=true,print=true}
ExposedMembers={}
local core={include=function() end,Players={[7]=corePlayer},Map=map,
 PlayerConfigurations={[7]={GetLeaderTypeName=function() return ui.PlayerConfigurations[7]:GetLeaderTypeName() end}},
 ExposedMembers=ExposedMembers,GameEvents={OnGameTurnStarted=event(),BaiqiRequisitionRecover=event()}}
setmetatable(core,{__index=function(_,key) if allowed[key] then return ui[key] end end})
h.core=core
function h.FireBootstrap() for _,fn in ipairs(listeners) do fn() end end
""")
    h = lua.globals().TestPropBridge
    if stored is not None:
        h.store = h.Copy(stored)
    if foreign:
        lua.execute("ExposedMembers.BaiqiProphetIntentBridge={marker='foreign',version=9}")
    world = lua.globals().TestWorld
    previous = world.withScientist
    if fresh:
        world.withScientist = False
    loader = lua.eval('function(source,name,env) local fn,err=load(source,name,"t",env);assert(fn,err);return fn() end')
    for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiProphetJournal', 'BaiqiProphetIntentGameplay'):
        loader((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'), name, h.core)
    world.withScientist = previous
    return h
