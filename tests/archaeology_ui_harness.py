from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = 'BAIQI_ARCHAEOLOGY_INTENTS_V1'


def install_archaeology_bridge(lua, stored=None):
    lua.execute('''
      local ui=_G
      TestArchBridge={store={},allowWrite=true,writes=0,listeners={}}
      local h=TestArchBridge
      local function copy(value)
        if type(value)~='table' then return value end
        local out={};for key,item in pairs(value) do out[key]=copy(item) end;return out
      end
      h.Copy=copy
      local function wrap(unit)
        return {GetID=function() return unit:GetID() end,GetOwner=function() return unit:GetOwner() end,
          GetType=function() return unit:GetUnitType() end,GetX=function() return unit:GetX() end,
          GetY=function() return unit:GetY() end,GetMovesRemaining=function() return unit:GetMovesRemaining() end,
          GetFormationUnitCount=function() return unit:GetFormationUnitCount() end}
      end
      local player={IsHuman=function() return ui.PlayerConfigurations[7]:IsHuman() end,
        IsTurnActive=function() return ui.Players[7]:IsTurnActive() end,
        GetProperty=function(_,key) return copy(h.store[key]) end,
        SetProperty=function(_,key,value) h.writes=h.writes+1;if h.allowWrite then h.store[key]=copy(value) end end,
        GetUnits=function() return {FindID=function(_,id)
          local unit=ui.Players[7]:GetUnits():FindID(id);return unit and wrap(unit)
        end} end,
        GetCities=function() return {FindID=function(_,id)
          local city=ui.Players[7]:GetCities():FindID(id)
          if city then return {GetID=function() return city:GetID() end,GetOwner=function() return city:GetOwner() end,
            GetX=function() return city:GetX() end,GetY=function() return city:GetY() end,
            GetBuildings=function() return {HasBuilding=function(_,index) return city:GetBuildings():HasBuilding(index) end} end} end
        end} end}
      ExposedMembers={}
      local allowed={type=true,pairs=true,ipairs=true,pcall=true,tostring=true,tonumber=true,select=true,assert=true,
        getmetatable=true,math=true,string=true,table=true,Game=true,GameInfo=true,GameConfiguration=true,
        Map=true,PlayersVisibility=true,print=true}
      local event={Add=function(callback) h.listeners[callback]=true end,Remove=function(callback) h.listeners[callback]=nil end}
      local core={Players={[7]=player},PlayerConfigurations={[7]={GetLeaderTypeName=function()
        return ui.PlayerConfigurations[7]:GetLeaderTypeName() end}},ExposedMembers=ExposedMembers,
        Events={GreatWorkCreated=event}}
      setmetatable(core,{__index=function(_,key) if allowed[key] then return ui[key] end end})
      h.core=core
      h.Emit=function(...) for callback in pairs(h.listeners) do callback(...) end end
    ''')
    h = lua.globals().TestArchBridge
    if stored is not None:
        h.store = h.Copy(stored)
    load = lua.eval('function(source,name,env) local chunk,err=load(source,name,"t",env);assert(chunk,err);return chunk() end')
    sources = {name: (ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8') for name in (
        'BaiqiConfig', 'BaiqiArchaeologyJournal', 'BaiqiArchaeologistUnit',
        'BaiqiArchaeologyIntentGameplay', 'BaiqiArchaeologyReceiptEvents')}
    h.core.include = lambda name: load(sources[name], name, h.core)
    for name in ('BaiqiConfig', 'BaiqiArchaeologyJournal', 'BaiqiArchaeologistUnit', 'BaiqiArchaeologyReceiptEvents'):
        load(sources[name], name, h.core)
