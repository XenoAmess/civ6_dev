from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime
from tools.build_observed_mod import transform,prelude

ROOT=Path(__file__).resolve().parents[1]


class ObservedBuildTests(unittest.TestCase):
    def test_real_guard_player_block_and_native_forward_count_once(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('unpack=table.unpack;Game={GetCurrentGameTurn=function() return 85 end};Automation={GetTime=function() return 1 end};ExposedMembers={};Events={PlayerTurnActivated={Add=function() end,Remove=function() end}}')
        for p in ['tests/lua/mock_world.lua','tests/lua/mock_guard.lua']:
            lua.execute((ROOT/p).read_text(encoding='utf-8'))
        lua.execute('''Game.GetCurrentGameTurn=function() return 85 end
EnvBefore={UnitManager=UnitManager,CityManager=CityManager,UI=UI}
''')
        for name in ['BaiqiConfig','BaiqiPolicy','BaiqiUIGuard']:
            p=ROOT/f'mod/Baiqi/Lua/{name}.lua';text,_=transform(p.read_text(encoding='utf-8'),f'Lua/{name}.lua');lua.execute(text)
        lua.execute('''P6BaiqiRegistry=ExposedMembers.P6BaiqiOwnRegistry
for _,e in pairs(P6BaiqiRegistry.entries) do e.SetEnabled(true) end''')
        text,_=transform('function Send(unit) return UnitManager.RequestOperation(unit,55,{}) end','UI/Call.lua')
        lua.execute(text)
        lua.execute('''assert(Send(TestUnit(1,7,8))==false and TestGuard.unitCalls==0)
local before=P6OwnDiag:Snapshot().buckets[85];assert(before==nil)
local ok,tail=Send(TestUnit(0,7,9));assert(ok==true and tail=='native' and TestGuard.unitCalls==1)
local count=0;for _,v in pairs(P6OwnDiag:Snapshot().buckets[85]) do count=count+v end
assert(count==1)''')
        self.assertTrue(lua.eval('UnitManager~=EnvBefore.UnitManager'))
        self.assertEqual(lua.eval('P6OwnDiag.marker'),'baiqi67-q19')

    def test_foreign_diagnostic_name_preserves_source_behavior(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('P6OwnDiag={marker="foreign"}')
        text,_=transform('function F(...) return ... end','test.lua');lua.execute(text)
        self.assertEqual(lua.globals().F(1,False),(1,False));self.assertEqual(lua.globals().P6OwnDiag.marker,'foreign')

    def test_existing_context_reuses_one_anchor_and_one_registry_identity(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''unpack=table.unpack;Adds=0;Game={GetCurrentGameTurn=function() return 1 end};Automation={GetTime=function() return 1 end};ExposedMembers={}
Events={PlayerTurnActivated={Add=function() Adds=Adds+1 end,Remove=function() end}}''')
        lua.execute(prelude('UI/One.lua'));lua.execute('First=P6OwnDiag')
        lua.execute(prelude('Lua/Included.lua'))
        self.assertTrue(lua.eval('P6OwnDiag==First and Adds==1 and ExposedMembers.P6BaiqiOwnRegistry.entries["UI/One.lua"]~=nil and ExposedMembers.P6BaiqiOwnRegistry.entries["Lua/Included.lua"]==nil'))

    def test_late_chunk_early_return_and_varargs_keep_original_results(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''unpack=table.unpack;Game={GetCurrentGameTurn=function() return 1 end};Automation={GetTime=function() return 1 end}
ExposedMembers={P6BaiqiOwnRegistry={marker='baiqi67-q19',entries={},enabled=true}}
Events={PlayerTurnActivated={Add=function() end,Remove=function() end}}''')
        text,manifest=transform('local a=...;if a then return 1,nil,false,nil end;return 3','UI/Late.lua')
        result=lua.execute(text,True)
        self.assertEqual(result,(1,None,False,None));self.assertTrue(manifest['top_level_chunk_wrapped'])
        self.assertEqual(lua.globals().P6OwnDiag.profile.totalCalls,1)
        self.assertEqual(lua.globals().P6OwnDiag.profile.samples[1].name,'UI/Late.lua:$chunk')


if __name__=='__main__':unittest.main()
