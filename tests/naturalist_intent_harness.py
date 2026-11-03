from pathlib import Path
from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'mod/Baiqi/Lua'


def to_python(value):
    if hasattr(value, 'items'):
        return {key: to_python(item) for key, item in value.items()}
    return value


def core_runtime(initial_state=None, inject_config_key=True):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
      F={localPlayer=4,unitID=100001,slot=100001,unitOwner=4,kind='UNIT_NATURALIST',
        charges=1,x=8,y=9,moves=4,formation=1,active=true,leader='LEADER_BAIQI',
        visible=true,revealed=true,plotOwner=4,parkValue=false,propertyWrites=0,ownerReads=0}
      local function copy(value)
        if type(value)~='table' then return value end
        local result={};for key,item in pairs(value) do result[key]=copy(item) end
        return result
      end
      local unit,units,player,plot,config={},{},{},{},{}
      function unit:GetID() return F.unitID end
      function unit:GetOwner() return F.unitOwner end
      function unit:GetType() return 19 end
      function unit:GetParkCharges()
        if F.changeOwnerDuringRead then F.unitOwner=3 end
        if F.throwCharges then error('charges') end
        return F.charges
      end
      function unit:GetBuildCharges() error('wrong charge API') end
      function unit:GetX() return F.x end
      function unit:GetY() return F.y end
      function unit:GetMovesRemaining() return F.moves end
      function unit:GetFormationUnitCount() return F.formation end
      function units:FindID(id)
        assert(self==units)
        if not F.missingUnit and id==F.slot then return unit end
      end
      function player:GetUnits() assert(self==player);return units end
      function player:IsHuman() return true end
      function player:IsTurnActive() return F.active end
      function player:GetProperty(key)
        assert(key=='BAIQI_NATURALIST_INTENTS_V1');return copy(Stored)
      end
      function player:SetProperty(key,value)
        assert(key=='BAIQI_NATURALIST_INTENTS_V1');F.propertyWrites=F.propertyWrites+1
        if not F.dropWrites then Stored=copy(value) end
      end
      function config:GetLeaderTypeName() return F.leader end
      -- Deliberately no config.IsHuman and no unit.GetUnitType: actual Core ABI.
      Players={[4]=player};PlayerConfigurations={[4]=config}
      Game={GetLocalPlayer=function() return F.localPlayer end,GetCurrentGameTurn=function() return 56 end}
      GameConfiguration={IsAnyMultiplayer=function() return F.multiplayer==true end,
        IsHotseat=function() return F.hotseat==true end}
      GameInfo={Units=setmetatable({}, {__index=function(_,index)
        assert(index==19);return {UnitType=F.kind}
      end})}
      function plot:GetX() return 8 end
      function plot:GetY() return 9 end
      function plot:GetOwner()
        F.ownerReads=F.ownerReads+1
        if F.forbidHiddenOwner then assert(F.visible and F.revealed) end
        return F.plotOwner
      end
      function plot:IsNationalPark() return F.parkValue end
      Map={GetPlot=function(x,y) if x==8 and y==9 then return plot end end}
      PlayersVisibility={[4]={IsRevealed=function() return F.revealed end,
        IsVisible=function() return F.visible end}}
      ExposedMembers={}
      local event={Add=function() end};GameEvents={OnGameTurnStarted=event,BaiqiRequisitionRecover=event}
    ''')

    def to_lua(value):
        if isinstance(value, dict):
            return lua.table_from({key: to_lua(item) for key, item in value.items()})
        return value

    lua.globals().Stored = to_lua(initial_state)

    def include(name):
        lua.execute((SOURCE / (name + '.lua')).read_text(encoding='utf-8'))
        if name == 'BaiqiConfig' and inject_config_key:
            # Explicit future consumer configuration; source60 has no registered
            # naturalist entry. This fixture does not claim package integration.
            lua.globals().BaiqiConfig.naturalistIntentKey = 'BAIQI_NATURALIST_INTENTS_V1'

    lua.globals().include = include
    include('BaiqiNaturalistIntentGameplay')
    return lua, lua.globals().ExposedMembers.BaiqiNaturalistIntentBridge
