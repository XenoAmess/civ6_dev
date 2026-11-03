from pathlib import Path
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
KEY = 'BAIQI_ARCHAEOLOGY_INTENTS_V1'


def archaeology_runtime(inject_key=True, with_events=False, before_module=None):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
      H={turn=92,localPlayer=7,human=true,active=true,leader='LEADER_BAIQI',
        unitID=4,unitOwner=7,unitExists=true,unitType=19,x=4,y=3,moves=2,formation=1,
        cityID=66,cityOwner=7,cityX=2,cityY=3,buildingIndex=24,buildingPresent=true,
        plotX=4,plotY=3,siteOwner=7,resourceIndex=9,revealed=true,visible=true,
        store={},reads=0,writes=0,allowWrite=true,resourceReads=0,listeners={},adds=0,removes=0}
      local h=H
      local function copy(value)
        if type(value)~='table' then return value end
        local out={};for key,item in pairs(value) do out[key]=copy(item) end;return out
      end
      H.Copy=copy
      include=function() end
      Game={GetLocalPlayer=function() return h.localPlayer end,GetCurrentGameTurn=function() return h.turn end}
      GameConfiguration={IsAnyMultiplayer=function() return h.multi==true end,IsHotseat=function() return h.hotseat==true end}
      local unit={GetID=function() return h.unitID end,GetOwner=function() return h.unitOwner end,
        GetType=function() return h.unitType end,GetX=function() return h.x end,GetY=function() return h.y end,
        GetMovesRemaining=function() return h.moves end,GetFormationUnitCount=function() return h.formation end}
      local buildings={HasBuilding=function(_,index) return index==h.buildingIndex and h.buildingPresent end}
      local city={GetID=function() return h.cityID end,GetOwner=function() return h.cityOwner end,
        GetX=function() return h.cityX end,GetY=function() return h.cityY end,
        GetBuildings=function() return buildings end}
      local player={IsHuman=function() return h.human end,IsTurnActive=function() return h.active end,
        GetUnits=function() return {FindID=function(_,id) if h.unitExists and id==h.unitID then return unit end end} end,
        GetCities=function() return {FindID=function(_,id) if id==66 then return city end end} end,
        GetProperty=function(_,key)
          h.reads=h.reads+1
          if h.onRead then h.onRead(h.reads) end
          if h.throwRead then error('metadata unreadable') end
          return copy(h.store[key])
        end,
        SetProperty=function(_,key,value)
          h.writes=h.writes+1
          if h.allowWrite then h.store[key]=copy(value) end
          if h.writeThenThrow then error('write outcome unknown') end
        end}
      Players={[7]=player}
      PlayerConfigurations={[7]={GetLeaderTypeName=function() return h.leader end}}
      local visibility={IsRevealed=function() return h.revealed end,IsVisible=function() return h.visible end}
      PlayersVisibility={[7]=visibility}
      local plot={GetX=function() return h.plotX end,GetY=function() return h.plotY end,
        GetOwner=function() return h.siteOwner end,GetResourceType=function()
          h.resourceReads=h.resourceReads+1
          local result=h.resourceIndex
          if h.onResource then h.onResource(h.resourceReads) end
          return result
        end}
      Map={GetPlot=function(x,y) if x==4 and y==3 then return plot end end}
      GameInfo={Units={[19]={UnitType='UNIT_ARCHAEOLOGIST'},[20]={UnitType='UNIT_NATURALIST'}},
        Buildings={BUILDING_MUSEUM_ARTIFACT={BuildingType='BUILDING_MUSEUM_ARTIFACT',Index=24}},
        Resources={[9]={ResourceType='RESOURCE_ANTIQUITY_SITE'},[10]={ResourceType='RESOURCE_SHIPWRECK'}}}
      ExposedMembers={}
      H.unit=unit;H.city=city;H.buildings=buildings;H.visibility=visibility;H.plot=plot;H.player=player
      H.proposal={homeCityID=66,cityX=2,cityY=3,buildingIndex=24,x=4,y=3,
        resourceIndex=9,resourceType='RESOURCE_ANTIQUITY_SITE',baselineWorkIDs={}}
      H.descriptor={unitID=4,unitType='UNIT_ARCHAEOLOGIST',homeCityID=66,x=4,y=3,
        artifactIndex=5,artifactType=0,actingPlayerID=2,choicePlayerID=2,targetPlayerID=3}
    ''')
    for name in ('BaiqiConfig', 'BaiqiArchaeologyJournal', 'BaiqiArchaeologistUnit'):
        lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
    if inject_key:
        lua.globals().BaiqiConfig.archaeologyIntentKey = KEY
    else:
        lua.globals().BaiqiConfig.archaeologyIntentKey = None
    if with_events:
        lua.execute('''
          Events={GreatWorkCreated={Add=function(...)
            assert(select('#',...)==1 and type((...))=='function','static Add(callback)')
            H.listeners[(...)]=true;H.adds=H.adds+1
          end,Remove=function(...)
            assert(select('#',...)==1 and type((...))=='function','static Remove(callback)')
            H.listeners[(...)]=nil;H.removes=H.removes+1
          end}}
          H.ListenerCount=function() local n=0;for _ in pairs(H.listeners) do n=n+1 end;return n end
          H.Emit=function(...)
            local list={};for callback in pairs(H.listeners) do list[#list+1]=callback end
            for _,callback in ipairs(list) do callback(...) end
          end
        ''')
    if before_module:
        lua.execute(before_module)
    module = lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiArchaeologyIntentGameplay.lua').read_text(encoding='utf-8'))
    return lua, module, lua.globals().H
