from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = 'BAIQI_NATURALIST_PURCHASE_INTENTS_V1'


def install_purchase_bridge(lua, stored=None):
    lua.execute('''
      local ui=_G
      TestPurchaseBridge={store={},writes=0,allowWrite=true}
      local h=TestPurchaseBridge
      local function copy(value)
        if type(value)~='table' then return value end
        local out={};for key,item in pairs(value) do out[key]=copy(item) end;return out
      end
      h.Copy=copy
      local function unitWrap(unit)
        return {GetID=function() return unit:GetID() end,GetOwner=function() return unit:GetOwner() end,
          GetType=function() return unit:GetUnitType() end,GetX=function() return unit:GetX() end,
          GetY=function() return unit:GetY() end,GetMovesRemaining=function() return unit:GetMovesRemaining() end,
          GetFormationUnitCount=function() return unit:GetFormationUnitCount() end,
          GetParkCharges=function() return unit:GetParkCharges() end,
          IsDelayedDeath=function() return unit:IsDelayedDeath() end}
      end
      local function cityWrap(city)
        return {GetID=function() return city:GetID() end,GetOwner=function() return city:GetOwner() end,
          GetX=function() return city:GetX() end,GetY=function() return city:GetY() end}
      end
      local player={IsHuman=function() return ui.PlayerConfigurations[7]:IsHuman() end,
        IsTurnActive=function() return ui.Players[7]:IsTurnActive() end,
        GetProperty=function(_,key) if h.throwRead then error('unavailable read') end;return copy(h.store[key]) end,
        SetProperty=function(_,key,value)
          h.writes=h.writes+1;if h.allowWrite then h.store[key]=copy(value) end
        end,
        GetReligion=function() return {GetFaithBalance=function() return ui.TestWorld.faith end} end,
        GetCities=function()
          local cities=ui.Players[7]:GetCities()
          return {FindID=function(_,id) local c=cities:FindID(id);return c and cityWrap(c) end}
        end,
        GetUnits=function()
          local units=ui.Players[7]:GetUnits()
          return {FindID=function(_,id) local unit=units:FindID(id);return unit and unitWrap(unit) end,
            Members=function()
              local list={}
              for _,unit in units:Members() do list[#list+1]=unitWrap(unit) end
              return ipairs(list)
            end}
        end}
      ExposedMembers={}
      local core={include=function() end,Players={[7]=player},ExposedMembers=ExposedMembers,
        PlayerConfigurations={[7]={GetLeaderTypeName=function() return ui.PlayerConfigurations[7]:GetLeaderTypeName() end}}}
      local allowed={type=true,pairs=true,ipairs=true,pcall=true,tostring=true,select=true,assert=true,
        getmetatable=true,math=true,string=true,table=true,Game=true,GameInfo=true,GameConfiguration=true,
        Map=true,PlayersVisibility=true,print=true}
      setmetatable(core,{__index=function(_,key) if allowed[key] then return ui[key] end end})
      h.core=core
    ''')
    if stored is not None:
        lua.globals().TestPurchaseBridge.store = lua.globals().TestPurchaseBridge.Copy(stored)
    load = lua.eval('function(source,name,env) local chunk,err=load(source,name,"t",env);assert(chunk,err);return chunk() end')
    for name in ('BaiqiConfig','BaiqiNaturalistUnit','BaiqiNaturalistPurchaseSnapshot',
                 'BaiqiNaturalistPurchaseJournal','BaiqiMissionaryPurchaseJournal',
                 'BaiqiFaithPurchaseGuard','BaiqiNaturalistPurchaseIntentGameplay'):
        load((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'), name, lua.globals().TestPurchaseBridge.core)
