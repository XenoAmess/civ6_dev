"""Software prototype only: no router integration or Native performance proof."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class BuilderPacketPrototypeTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua','tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua','mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua','mod/Baiqi/Lua/BaiqiPlanner.lua'):
            self.lua.execute((ROOT/name).read_text(encoding='utf-8'))
        source=(ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
        prototype=(ROOT/'docs/implementation/prototypes/builder-path-packet.lua').read_text(encoding='utf-8')
        exports="\nreturn {PlayerContext=PlayerContext,PrepareBuilderPathPacket=PrepareBuilderPathPacket,ValidateBuilderPathPacket=ValidateBuilderPathPacket}\n"
        self.private=self.lua.execute(source+'\n'+prototype+exports)
        self.w=self.lua.globals().TestWorld
        self.w.withBuilder=True
        for name in ('PlayerContext','PrepareBuilderPathPacket','ValidateBuilderPathPacket'):
            self.lua.globals()[name]=self.private[name]
        self.lua.globals().BaiqiController.RunNow(False)

    def prepare(self):
        ctx,player,state=self.private.PlayerContext()
        return self.private.PrepareBuilderPathPacket(ctx,player,state,self.w.objects.builder,self.lua.globals().Map.GetPlotByIndex(43))

    def validate(self,packet):
        ctx,player,state=self.private.PlayerContext()
        return self.private.ValidateBuilderPathPacket(ctx,player,state,self.w.objects.builder,packet)

    def test_prepare_builder_path_packet_validates_prequery_safety(self):
        self.lua.execute('''
            TestWorld.enemyPlot=43
            local ctx,player,state=PlayerContext()
            local packet=PrepareBuilderPathPacket(ctx,player,state,TestWorld.objects.builder,Map.GetPlotByIndex(43))
            assert(packet==nil)
        ''')
        self.assertEqual(len(self.w.pathQueries), 0)

    def test_validate_builder_path_packet_rejects_changed_formation(self):
        self.lua.execute('''
            TestWorld.enemyPlot=0
            local ctx,player,state=PlayerContext()
            local packet=PrepareBuilderPathPacket(ctx,player,state,TestWorld.objects.builder,Map.GetPlotByIndex(43))
            assert(packet~=nil)
            TestWorld.formation=2
            local step=ValidateBuilderPathPacket(ctx,player,state,TestWorld.objects.builder,packet)
            assert(step==nil)
        ''')
        self.assertEqual(len(self.w.pathQueries), 1)

    def test_validate_builder_path_packet_rejects_new_enemy_on_path(self):
        self.lua.execute('''
            TestWorld.enemyPlot=0
            local ctx,player,state=PlayerContext()
            local packet=PrepareBuilderPathPacket(ctx,player,state,TestWorld.objects.builder,Map.GetPlotByIndex(43))
            assert(packet~=nil)
            TestWorld.enemyPlot=42
            local step=ValidateBuilderPathPacket(ctx,player,state,TestWorld.objects.builder,packet)
            assert(step==nil)
        ''')
        self.assertEqual(len(self.w.pathQueries), 1)

    def test_copy_positive_and_no_writes(self):
      p=self.prepare();self.assertIsNotNone(p);self.lua.execute('TestWorld.paths[43][2]=44')
      self.assertEqual(p.path[2],43);self.assertEqual(self.validate(p).GetIndex(),43);self.assertEqual(len(self.w.unitRequests),0)

    def test_prepare_rejects_move_busy_or_turn_change_in_native_query(self):
      for change in ['TestWorld.packetMoves=1','TestWorld.busy=true','TestWorld.turn=TestWorld.turn+1']:
       with self.subTest(change=change):
        self.setUp();self.lua.execute('''
    TestWorld.packetMoves=2
    TestWorld.objects.builder.GetMovesRemaining=function() return TestWorld.packetMoves end
    local original=UnitManager.GetMoveToPathEx
    UnitManager.GetMoveToPathEx=function(...) local result=original(...);CHANGE;return result end
    '''.replace('CHANGE',change));self.assertIsNone(self.prepare())

    def test_validate_rechecks_moves_busy_and_turn_after_reads(self):
      for change in ['TestWorld.packetMoves=1','TestWorld.busy=true','TestWorld.turn=TestWorld.turn+1']:
       with self.subTest(change=change):
        self.setUp();self.lua.execute('TestWorld.packetMoves=2;TestWorld.objects.builder.GetMovesRemaining=function() return TestWorld.packetMoves end')
        p=self.prepare();self.assertIsNotNone(p)
        self.lua.execute('''local original=Units.GetUnitsInPlot
    Units.GetUnitsInPlot=function(...) local result=original(...);CHANGE;return result end'''.replace('CHANGE',change));self.assertIsNone(self.validate(p))

    def test_malformed_packet_fails_closed_without_lua_error(self):
      self.assertIsNone(self.validate(42))
