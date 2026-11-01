"""Native Core event bus and metadata provider separate from UI slot bindings."""
from pathlib import Path
from gp_intent_harness import install_gp_bridge

ROOT = Path(__file__).resolve().parents[1]


def install_creative_bridge(lua, stored=None):
    install_gp_bridge(lua, stored=stored)
    lua.execute('''
local h,ui=TestBridge,_G
local listeners={}
h.core.tonumber=tonumber
h.core.Events={GreatWorkCreated={Add=function(fn) listeners[fn]=true end}}
h.core.Cities={GetCityInPlot=function(x,y)
 local city=ui.Cities.GetCityInPlot(x,y)
 if not city then return nil end
 return {GetOwner=function() return city:GetOwner() end,
  GetBuildings=function() return {HasBuilding=function(_,index) return city:GetBuildings():HasBuilding(index) end} end}
end}
function h.FireCoreWork(...) for fn in pairs(listeners) do fn(...) end end
local original=TestWorld.NativeFireWork or TestWorld.FireWork
TestWorld.NativeFireWork=original
h.FireUIWork=original
function TestWorld.FireWork(...)
 h.FireCoreWork(...)
 original(...)
end
local previous=Players[7].GetProperty
Players[7].GetProperty=function(self,key)
 if key=='BAIQI_CREATIVE_INTENTS_V1' then
  if h.uiLag then return nil end
  return h.Copy(h.store[key])
 end
 return previous(self,key)
end
''')
    load = lua.eval('function(source,name,env) local fn,err=load(source,name,"t",env);assert(fn,err);return fn() end')
    for name in ('BaiqiCreativeJournal', 'BaiqiCreativeIntentGameplay'):
        load((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'), name, lua.globals().TestBridge.core)
