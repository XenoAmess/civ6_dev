from types import SimpleNamespace
import test_baiqi_naturalist_purchase_core as snapshots

ROOT = snapshots.ROOT
KEY = 'BAIQI_NATURALIST_PURCHASE_INTENTS_V1'


def make_purchase_core(inject_key=True, stored=None, with_receipt_events=False):
    host = SimpleNamespace()
    snapshots.PurchaseSnapshotTests.setUp(host)
    lua = host.lua
    lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiConfig.lua').read_text(encoding='utf-8'))
    lua.execute('''
      include=function() end
      H={store={},writes=0,reads=0,allowWrite=true,turn=92,localPlayer=0,human=true,active=true}
      local function copy(value)
        if type(value)~='table' then return value end
        local result={};for k,v in pairs(value) do result[k]=copy(v) end;return result
      end
      H.Copy=copy
      Game={GetLocalPlayer=function() return H.localPlayer end,GetCurrentGameTurn=function() return H.turn end}
      GameConfiguration={IsAnyMultiplayer=function() return H.multiplayer==true end,
        IsHotseat=function() return H.hotseat==true end}
      GameInfo.Units.UNIT_NATURALIST=GameInfo.Units[19]
      GameInfo.Units[19].Hash=1877270220
      S.records[1].dead=true;S.records[2].dead=true
      Player.IsHuman=function() return H.human end
      Player.IsTurnActive=function() return H.active end
      Player.GetProperty=function(_,key)
        H.reads=H.reads+1
        if H.throwRead then error('read unavailable') end
        return copy(H.store[key])
      end
      Player.SetProperty=function(_,key,value)
        H.writes=H.writes+1
        if H.throwWrite then error('unknown write result') end
        if H.allowWrite then
          H.store[key]=copy(value)
          if H.corruptWrite then H.store[key].unexpected=true end
        end
      end
      Players={[0]=Player}
      PlayerConfigurations={[0]={GetLeaderTypeName=function() return H.leader or BaiqiConfig.leader end}}
      ExposedMembers={}
      function AddPurchasedUnit(id)
        local record={id=id,owner=0,x=16,y=14,charges=1,formation=1}
        H.newUnit=record
        TestObjects[5]={GetID=function() return record.id end,GetOwner=function() return record.owner end,
          GetType=function() return 19 end,GetX=function() return record.x end,GetY=function() return record.y end,
          GetParkCharges=function() return record.charges end,GetMovesRemaining=function() return 0 end,
          GetFormationUnitCount=function() return record.formation end,IsDelayedDeath=function() return record.dead==true end}
      end
      CityManager=setmetatable({},{__index=function() error('Core must not issue city commands') end})
    ''')
    if inject_key:
        lua.globals().BaiqiConfig.naturalistPurchaseIntentKey = KEY
    else:
        lua.globals().BaiqiConfig.naturalistPurchaseIntentKey = None
    if with_receipt_events:
        lua.execute('''
          H.listeners={UnitAddedToMap={},PlayerTurnDeactivated={}}
          H.adds=0;H.removes=0
          Events={}
          for name,listeners in pairs(H.listeners) do
            Events[name]={Add=function(...)
              assert(select('#',...)==1 and type((...))=='function','Event.Add is static Add(callback)')
              listeners[(...)]=true;H.adds=H.adds+1
            end,Remove=function(...)
              assert(select('#',...)==1 and type((...))=='function','Event.Remove is static Remove(callback)')
              listeners[(...)]=nil;H.removes=H.removes+1
            end}
          end
          H.Fire=function(name,playerID,unitID)
            local snapshot={};for callback in pairs(H.listeners[name]) do snapshot[#snapshot+1]=callback end
            for _,callback in ipairs(snapshot) do callback(playerID,unitID) end
          end
          H.ListenerCount=function(name) local n=0;for _ in pairs(H.listeners[name]) do n=n+1 end;return n end
        ''')
    if stored is not None:
        def plain(value):
            if hasattr(value, 'items'):
                return {key:plain(item) for key,item in value.items()}
            return value
        def into_runtime(value):
            if isinstance(value, dict):
                return lua.table_from({key:into_runtime(item) for key,item in value.items()})
            return value
        lua.globals().H.store = into_runtime(plain(stored))
    for name in ('BaiqiNaturalistPurchaseJournal','BaiqiMissionaryPurchaseJournal','BaiqiFaithPurchaseGuard','BaiqiNaturalistPurchaseIntentGameplay'):
        lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
    return lua
