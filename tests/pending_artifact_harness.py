from pathlib import Path
from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


def pending_runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    inspect = lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiPendingArtifact.lua').read_text(encoding='utf-8'))
    player, game, game_info, configurations, fixture, trace = lua.execute('''
      local f={pendingState='ready',unitID=100001,liveID=100001,unitOwner=4,liveOwner=4,
        unitType='UNIT_ARCHAEOLOGIST',homeID=65536,cityID=65536,homeOwner=4,x=8,y=9,
        artifactIndex=7,artifactType=3,actingID=2,targetID=3}
      local trace={pending=0,component=0,index=0,artifact=0}
      local function throwing(name) if f.throwAt==name then error(name) end end
      local unit,live,city,units,cities,player,arch={},{},{},{},{},{},{}
      function unit:GetID() assert(self==unit);return f.unitID end
      function unit:GetOwner() assert(self==unit);return f.unitOwner end
      function unit:GetUnitType() assert(self==unit);return 8 end
      function live:GetID() assert(self==live);return f.liveID end
      function live:GetOwner() assert(self==live);return f.liveOwner end
      function live:GetUnitType() assert(self==live);return 8 end
      function live:GetArchaeologyHomeCity() assert(self==live);return f.homeID end
      function live:GetX() assert(self==live);return f.x end
      function live:GetY() assert(self==live);return f.y end
      function live:GetArchaeology()
        assert(self==live);trace.component=trace.component+1
        throwing('artifact_component');return arch
      end
      function arch:GetArtifactIndex()
        assert(self==arch);trace.index=trace.index+1
        throwing('artifact_index');return f.artifactIndex
      end
      function units:GetNextExtractingArchaeologist()
        assert(self==units);trace.pending=trace.pending+1;throwing('get_pending')
        if f.pendingState=='none' then return nil end
        if f.pendingState=='false' then return false end
        if f.pendingState=='throw' then error('pending') end
        assert(f.pendingState=='ready');return unit
      end
      function units:FindID(id) assert(self==units and id==f.unitID);return live end
      function cities:FindID(id)
        assert(self==cities and id==f.homeID);throwing('city_lookup');return city
      end
      function city:GetID() assert(self==city);return f.cityID end
      function city:GetOwner() assert(self==city);return f.homeOwner end
      function player:GetUnits() assert(self==player);return units end
      function player:GetCities() assert(self==player);return cities end
      local game={GetArtifactByIndex=function(...)
        assert(select('#',...)==1 and (...)==f.artifactIndex)
        trace.artifact=trace.artifact+1;throwing('artifact_lookup')
        return {Type=f.artifactType,ActingPlayerID=f.actingID,TargetPlayerID=f.targetID}
      end}
      local gameInfo={Units=setmetatable({}, {__index=function(_,index)
        assert(index==8);return {UnitType=f.unitType}
      end})}
      local configurations=setmetatable({}, {__index=function(_,id)
        if (id==2 or id==3) and id~=f.configMissingID then return {} end
      end})
      return player,game,gameInfo,configurations,f,trace
    ''')
    return lua, inspect, player, game, game_info, configurations, fixture, trace
