from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def install_naturalist_bridge(lua, stored=None):
    lua.execute('''
      local ui=_G
      TestParkBridge={store={},allowWrite=true,writes=0}
      local h=TestParkBridge
      local function copy(value)
        if type(value)~='table' then return value end
        local result={};for key,item in pairs(value) do result[key]=copy(item) end;return result
      end
      h.Copy=copy
      local function wrap(unit)
        return {GetID=function() return unit:GetID() end,GetOwner=function() return unit:GetOwner() end,
          GetType=function() return unit:GetUnitType() end,GetX=function() return unit:GetX() end,
          GetY=function() return unit:GetY() end,GetMovesRemaining=function() return unit:GetMovesRemaining() end,
          GetFormationUnitCount=function() return unit:GetFormationUnitCount() end,
          GetParkCharges=function() return unit:GetParkCharges() end}
      end
      local player={IsHuman=function() return ui.PlayerConfigurations[7]:IsHuman() end,
        IsTurnActive=function() return ui.Players[7]:IsTurnActive() end,
        GetProperty=function(_,key) return copy(h.store[key]) end,
        SetProperty=function(_,key,value) h.writes=h.writes+1;if h.allowWrite then h.store[key]=copy(value) end end,
        GetUnits=function()
          return {FindID=function(_,id) local unit=ui.Players[7]:GetUnits():FindID(id);return unit and wrap(unit) end}
        end}
      ExposedMembers={}
      local allowed={type=true,pairs=true,ipairs=true,pcall=true,tostring=true,select=true,assert=true,
        getmetatable=true,math=true,string=true,table=true,Game=true,GameInfo=true,GameConfiguration=true,
        Map=true,PlayersVisibility=true,print=true}
      local event={Add=function() end}
      local core={include=function() end,Players={[7]=player},
        PlayerConfigurations={[7]={GetLeaderTypeName=function() return ui.PlayerConfigurations[7]:GetLeaderTypeName() end}},
        ExposedMembers=ExposedMembers,GameEvents={OnGameTurnStarted=event,BaiqiRequisitionRecover=event}}
      setmetatable(core,{__index=function(_,key) if allowed[key] then return ui[key] end end})
      h.core=core
    ''')
    if stored is not None:
        lua.globals().TestParkBridge.store = lua.globals().TestParkBridge.Copy(stored)
    load = lua.eval('function(source,name,env) local chunk,err=load(source,name,"t",env);assert(chunk,err);return chunk() end')
    for name in ('BaiqiConfig', 'BaiqiNaturalistJournal', 'BaiqiNaturalistUnit', 'BaiqiNaturalistIntentGameplay'):
        load((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'), name, lua.globals().TestParkBridge.core)
