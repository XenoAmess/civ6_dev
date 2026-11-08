"""Execute actual storage consumers in Lua 5.1 with isolated native bindings."""
from pathlib import Path
from lupa.lua51 import LuaRuntime
from missionary_purchase_fixtures import snapshot_fixture

ROOT=Path(__file__).resolve().parents[1]
KEY='BAIQI_MISSIONARY_PURCHASE_INTENTS_V1'
NKEY='BAIQI_NATURALIST_PURCHASE_INTENTS_V1'
RKEY='BAIQI_RELIGIOUS_INTENTS_V1'


def make_missionary_core(stored=None, source=None, religious_source=None):
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.execute(snapshot_fixture)
    lua.execute('''
      records={}
      include=function()end
      print=function()end
      H={store={},writes=0,reads=0,history={},allowWrite=true,turn=119,localPlayer=0,human=true,active=true,
         listeners={UnitAddedToMap={},PlayerTurnDeactivated={}},adds=0,removes=0}
      function H.Copy(v)
        if type(v)~='table'then return v end
        local c={};for k,x in pairs(v)do c[k]=H.Copy(x)end;return c
      end
      Game={GetLocalPlayer=function()return H.localPlayer end,GetCurrentGameTurn=function()return H.turn end}
      GameConfiguration={IsAnyMultiplayer=function()return H.multiplayer==true end,
        IsHotseat=function()return H.hotseat==true end}
      Player.IsHuman=function()return H.human end
      Player.IsTurnActive=function()return H.active end
      Player.GetProperty=function(self,k)
        assert(self==Player);H.reads=H.reads+1
        if H.throwRead then error('read failed')end
        if H.onRead then H.onRead(k,H.reads)end
        return H.Copy(H.store[k])
      end
      Player.SetProperty=function(self,k,v)
        assert(self==Player);H.writes=H.writes+1;H.history[#H.history+1]=k
        if H.throwWrite then error('write unknown')end
        if H.allowWrite and k~=H.rejectKey then
          H.store[k]=H.Copy(v)
          if H.corruptWrite then H.store[k].unexpected=true end
        end
      end
      Units.FindID=function(self,id)
        assert(self==Units)
        for _,r in ipairs(records)do if r.id==id then return Make(r)end end
      end
      Players={[0]=Player}
      PlayerConfigurations={[0]={GetLeaderTypeName=function()return H.leader or BaiqiConfig.leader end}}
      GameInfo.Units.UNIT_MISSIONARY=GameInfo.Units[17]
      GameInfo.Units[17].Hash=-199
      GameInfo.Units[17].MustPurchase=true
      GameInfo.Units[17].PurchaseYield='YIELD_FAITH'
      ExposedMembers={}
      GameEvents={OnGameTurnStarted={Add=function()end},BaiqiRequisitionRecover={Add=function()end}}
      Events={}
      for name,listeners in pairs(H.listeners)do
        Events[name]={Add=function(...)
          assert(select('#',...)==1 and type((...))=='function')
          listeners[(...)]=true;H.adds=H.adds+1
        end,Remove=function(...)
          assert(select('#',...)==1 and type((...))=='function')
          listeners[(...)]=nil;H.removes=H.removes+1
        end}
      end
      function H.Fire(name,pid)
        local copy={};for cb in pairs(H.listeners[name])do copy[#copy+1]=cb end
        for _,cb in ipairs(copy)do cb(pid)end
      end
      function H.ListenerCount(name)local n=0;for _ in pairs(H.listeners[name])do n=n+1 end;return n end
      function H.Add(id)
        local r={id=id,owner=0,type=17,religion=4,charges=3,x=16,y=14,moves=0,formation=1}
        records[#records+1]=r;H.newUnit=r;return r
      end
      CityManager=setmetatable({},{__index=function()error('Core may not issue city commands')end})
      UnitManager=setmetatable({},{__index=function()error('Core may not issue unit commands')end})
    ''')
    for name in ('BaiqiConfig','BaiqiPolicy','BaiqiReligiousJournal','BaiqiNaturalistPurchaseJournal',
                 'BaiqiMissionaryPurchaseJournal','BaiqiFaithPurchaseGuard','BaiqiMissionaryPurchaseSnapshot'):
        lua.execute((ROOT/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
    if stored is not None:
        def plain(v):
            return {k:plain(x)for k,x in v.items()}if hasattr(v,'items')else v
        def convert(v):
            return lua.table_from({k:convert(x)for k,x in v.items()})if isinstance(v,dict)else v
        lua.globals().H.store=convert(plain(stored))
    lua.execute(religious_source or (ROOT/'mod/Baiqi/Lua/BaiqiReligiousIntentGameplay.lua').read_text(encoding='utf-8'))
    lua.execute(source or (ROOT/'mod/Baiqi/Lua/BaiqiMissionaryPurchaseIntentGameplay.lua').read_text(encoding='utf-8'))
    lua.execute('H.writes=0;H.reads=0;H.history={}')
    return lua
