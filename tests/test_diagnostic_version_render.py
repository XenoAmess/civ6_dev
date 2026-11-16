from pathlib import Path
import unittest
import hashlib
from tools.diagnostic_version_render import render_helper
from tools.build_static_control import clock_prelude
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53

ROOT=Path(__file__).resolve().parents[1]


class DiagnosticVersionRenderTests(unittest.TestCase):
    def template(self,kind):
        return (ROOT/f"tools/lua/{kind}.lua").read_text(encoding="utf-8")

    def test_legacy_templates_are_byte_exact(self):
        for kind in ("benchmark_end_bridge","diagnostic_plan_stage"):
            text=self.template(kind)
            for version in (140,141,142):
                self.assertEqual(render_helper(text,kind,version),text)

    def test_current_render_compiles_with_new_version_and_preserves_raw_file(self):
        for kind in ("benchmark_end_bridge","diagnostic_plan_stage"):
            text=self.template(kind);rendered=render_helper(text,kind,143)
            self.assertIn("sourceVersion==143",rendered)
            self.assertIn("baiqi143-pressure-",rendered)
            self.assertNotIn("baiqi142-pressure-",rendered)
            for L in (L51,L53):L().compile(rendered)
            self.assertEqual(self.template(kind),text)

    def test_source144_current_render_compiles_with_new_version_and_preserves_raw_file(self):
        for kind in ("benchmark_end_bridge","diagnostic_plan_stage"):
            text=self.template(kind);rendered=render_helper(text,kind,144)
            self.assertIn("sourceVersion==144",rendered)
            self.assertIn("baiqi144-pressure-",rendered)
            self.assertNotIn("baiqi142-pressure-",rendered)
            for L in (L51,L53):L().compile(rendered)
            self.assertEqual(self.template(kind),text)

    def test_source145_current_render_compiles_with_new_version_and_preserves_raw_file(self):
        for kind in ("benchmark_end_bridge","diagnostic_plan_stage"):
            text=self.template(kind);rendered=render_helper(text,kind,145)
            self.assertIn("sourceVersion==145",rendered)
            self.assertIn("baiqi145-pressure-",rendered)
            self.assertNotIn("baiqi142-pressure-",rendered)
            for L in (L51,L53):L().compile(rendered)
            self.assertEqual(self.template(kind),text)

    def test_source143_pressure_prefix_remains_byte_exact(self):
        prefix=clock_prelude(normal_end_bridge=True,source_version=143,pressure_initial_turn=1)
        self.assertEqual(hashlib.sha256(prefix.encode()).hexdigest(),'fa1f9b5552ff2d821853a9eeae37f70826c28ba51ea83aafc81b9fb665fc9dc3')

    def test_source144_pressure_prefix_remains_byte_exact(self):
        prefix=clock_prelude(normal_end_bridge=True,source_version=144,pressure_initial_turn=1)
        self.assertEqual(hashlib.sha256(prefix.encode()).hexdigest(),'67f2c77141485edb173c6fffb9a822d9130e5b001dbd1339bd6a366e2d5f5bc8')

    def test_exact_type_and_unknown_kind_or_version_rejected(self):
        class IntSubclass(int):pass
        for value in (True,143.0,"143",None,157,IntSubclass(143)):
            with self.assertRaises(ValueError):
                render_helper(self.template("benchmark_end_bridge"),"benchmark_end_bridge",value)
        with self.assertRaises(ValueError):render_helper("return {}","unknown",143)
        with self.assertRaises(ValueError):render_helper(None,"benchmark_end_bridge",143)

    def test_drifted_or_duplicate_anchors_fail_closed(self):
        for kind in ("benchmark_end_bridge","diagnostic_plan_stage"):
            text=self.template(kind)
            for bad in (text.replace("sourceVersion==140","sourceVersion==139"),
                        text+"\n-- sourceVersion==140 or sourceVersion==141 or sourceVersion==142",
                        text.replace("baiqi142-pressure-","drifted-pressure-")):
                with self.assertRaises(ValueError):render_helper(bad,kind,143)

    def test_current_pressure_prefix_runs_all_five_segments_in_both_lua_versions(self):
        for L in (L51,L53):
            lua=L(unpack_returned_tuples=True)
            lua.execute("""
Turn=1;Clock=10;Callbacks={};ExposedMembers={}
Game={GetCurrentGameTurn=function()return Turn end,GetLocalPlayer=function()return 0 end}
Automation={GetTime=function()return Clock end}
Events={PlayerTurnActivated={Add=function(f)Callbacks[#Callbacks+1]=f end,Remove=function()end}}
""")
            lua.execute(clock_prelude(normal_end_bridge=True,source_version=143,pressure_initial_turn=1))
            lua.execute("P6PairStage={phase='RECORDING',token=string.rep('a',32),ends={},normal_end=true,source_version=143,source='baiqi143-pressure-paired-v1',initial_turn=1}")
            g=lua.globals()
            for turn in range(1,6):
                g.Turn=turn;g.Clock=100+20*turn;g.P6PairStage.ends[turn]=True
                self.assertTrue(g.ExposedMembers.P6BaiqiPairEndBridge.Begin(turn,"a"*32))
                g.Turn=turn+1;g.Clock+=2;lua.execute("for _,f in ipairs(Callbacks)do f(0,false)end")
            self.assertEqual([r.to_turn for r in g.P6PairClock.Snapshot(g.P6PairClock).records.values()],[2,3,4,5,6])
            self.assertIsNone(g.P6PairStage.ends[6])

    def test_source144_current_pressure_prefix_runs_all_five_segments_in_both_lua_versions(self):
        for L in (L51,L53):
            lua=L(unpack_returned_tuples=True)
            lua.execute("""
Turn=1;Clock=10;Callbacks={};ExposedMembers={}
Game={GetCurrentGameTurn=function()return Turn end,GetLocalPlayer=function()return 0 end}
Automation={GetTime=function()return Clock end}
Events={PlayerTurnActivated={Add=function(f)Callbacks[#Callbacks+1]=f end,Remove=function()end}}
""")
            lua.execute(clock_prelude(normal_end_bridge=True,source_version=144,pressure_initial_turn=1))
            lua.execute("P6PairStage={phase='RECORDING',token=string.rep('a',32),ends={},normal_end=true,source_version=144,source='baiqi144-pressure-paired-v1',initial_turn=1}")
            g=lua.globals()
            for turn in range(1,6):
                g.Turn=turn;g.Clock=100+20*turn;g.P6PairStage.ends[turn]=True
                self.assertTrue(g.ExposedMembers.P6BaiqiPairEndBridge.Begin(turn,"a"*32))
                g.Turn=turn+1;g.Clock+=2;lua.execute("for _,f in ipairs(Callbacks)do f(0,false)end")
            self.assertEqual([r.to_turn for r in g.P6PairClock.Snapshot(g.P6PairClock).records.values()],[2,3,4,5,6])
            self.assertIsNone(g.P6PairStage.ends[6])

    def test_source145_current_pressure_prefix_runs_all_five_segments_in_both_lua_versions(self):
        for L in (L51,L53):
            lua=L(unpack_returned_tuples=True)
            lua.execute("""
Turn=1;Clock=10;Callbacks={};ExposedMembers={}
Game={GetCurrentGameTurn=function()return Turn end,GetLocalPlayer=function()return 0 end}
Automation={GetTime=function()return Clock end}
Events={PlayerTurnActivated={Add=function(f)Callbacks[#Callbacks+1]=f end,Remove=function()end}}
""")
            lua.execute(clock_prelude(normal_end_bridge=True,source_version=145,pressure_initial_turn=1))
            lua.execute("P6PairStage={phase='RECORDING',token=string.rep('a',32),ends={},normal_end=true,source_version=145,source='baiqi145-pressure-paired-v1',initial_turn=1}")
            g=lua.globals()
            for turn in range(1,6):
                g.Turn=turn;g.Clock=100+20*turn;g.P6PairStage.ends[turn]=True
                self.assertTrue(g.ExposedMembers.P6BaiqiPairEndBridge.Begin(turn,"a"*32))
                g.Turn=turn+1;g.Clock+=2;lua.execute("for _,f in ipairs(Callbacks)do f(0,false)end")
            self.assertEqual([r.to_turn for r in g.P6PairClock.Snapshot(g.P6PairClock).records.values()],[2,3,4,5,6])
            self.assertIsNone(g.P6PairStage.ends[6])

    def test_source146_current_render_compiles_with_new_version_and_preserves_raw_file(self):
        for kind in ("benchmark_end_bridge", "diagnostic_plan_stage"):
            text=self.template(kind);rendered=render_helper(text,kind,146)
            self.assertIn("sourceVersion==146",rendered)
            self.assertIn("baiqi146-pressure-",rendered)
            self.assertNotIn("baiqi145-pressure-",rendered)
            for L in (L51,L53):L().compile(rendered)
            self.assertEqual(self.template(kind),text)
            with self.assertRaises(ValueError):render_helper(text,kind,157)

    def test_source147_current_render_compiles_with_new_version_and_preserves_raw_file(self):
        for kind in ("benchmark_end_bridge", "diagnostic_plan_stage"):
            text=self.template(kind);rendered=render_helper(text,kind,147)
            self.assertIn("sourceVersion==147",rendered)
            self.assertIn("baiqi147-pressure-",rendered)
            self.assertNotIn("baiqi145-pressure-",rendered)
            for L in (L51,L53):L().compile(rendered)
            self.assertEqual(self.template(kind),text)
            with self.assertRaises(ValueError):render_helper(text,kind,157)

    def test_source148_current_render_compiles_with_new_version_and_preserves_raw_file(self):
        for kind in ("benchmark_end_bridge", "diagnostic_plan_stage"):
            text=self.template(kind);rendered=render_helper(text,kind,148)
            self.assertIn("sourceVersion==148",rendered)
            self.assertIn("baiqi148-pressure-",rendered)
            self.assertNotIn("baiqi145-pressure-",rendered)
            for L in (L51,L53):L().compile(rendered)
            self.assertEqual(self.template(kind),text)
            with self.assertRaises(ValueError):render_helper(text,kind,157)

    def test_source149_current_render_compiles_with_new_version_and_preserves_raw_file(self):
        for kind in ("benchmark_end_bridge", "diagnostic_plan_stage"):
            text=self.template(kind);rendered=render_helper(text,kind,149)
            self.assertIn("sourceVersion==149",rendered)
            self.assertIn("baiqi149-pressure-",rendered)
            self.assertNotIn("baiqi145-pressure-",rendered)
            for L in (L51,L53):L().compile(rendered)
            self.assertEqual(self.template(kind),text)
            with self.assertRaises(ValueError):render_helper(text,kind,157)

    def test_source150_current_render_compiles_with_new_version_and_preserves_raw_file(self):
        for kind in ("benchmark_end_bridge", "diagnostic_plan_stage"):
            text=self.template(kind);rendered=render_helper(text,kind,150)
            self.assertIn("sourceVersion==150",rendered)
            self.assertIn("baiqi150-pressure-",rendered)
            self.assertNotIn("baiqi145-pressure-",rendered)
            for L in (L51,L53):L().compile(rendered)
            self.assertEqual(self.template(kind),text)
            with self.assertRaises(ValueError):render_helper(text,kind,157)

    def test_source151_current_render_compiles_with_new_version_and_preserves_raw_file(self):
        for kind in ("benchmark_end_bridge", "diagnostic_plan_stage"):
            text=self.template(kind);rendered=render_helper(text,kind,151)
            self.assertIn("sourceVersion==151",rendered)
            self.assertIn("baiqi151-pressure-",rendered)
            self.assertNotIn("baiqi145-pressure-",rendered)
            for L in (L51,L53):L().compile(rendered)
            self.assertEqual(self.template(kind),text)
            with self.assertRaises(ValueError):render_helper(text,kind,157)

    def test_source152_current_render_compiles_with_new_version_and_preserves_raw_file(self):
        for kind in ("benchmark_end_bridge", "diagnostic_plan_stage"):
            text=self.template(kind);rendered=render_helper(text,kind,152)
            self.assertIn("sourceVersion==152",rendered)
            self.assertIn("baiqi152-pressure-",rendered)
            self.assertNotIn("baiqi145-pressure-",rendered)
            for L in (L51,L53):L().compile(rendered)
            self.assertEqual(self.template(kind),text)
            with self.assertRaises(ValueError):render_helper(text,kind,157)

    def test_source153_render_and_pressure_clock_keep_version_boundaries(self):
        for kind in ('benchmark_end_bridge','diagnostic_plan_stage'):
            raw=self.template(kind)
            rendered=render_helper(raw,kind,153)
            self.assertIn('sourceVersion==153',rendered)
            self.assertIn('baiqi153-pressure-',rendered)
            self.assertNotIn('baiqi152-pressure-',rendered)
            for L in (L51,L53):L().compile(rendered)
            self.assertEqual(raw,self.template(kind))
        for L in (L51,L53):
            lua=L(unpack_returned_tuples=True)
            lua.execute('''Turn=1;Clock=10;Callbacks={};ExposedMembers={}
Game={GetCurrentGameTurn=function()return Turn end,GetLocalPlayer=function()return 0 end}
Automation={GetTime=function()return Clock end}
Events={PlayerTurnActivated={Add=function(f)Callbacks[#Callbacks+1]=f end,Remove=function()end}}''')
            lua.execute(clock_prelude(normal_end_bridge=True,source_version=153,pressure_initial_turn=1))
            lua.execute("P6PairStage={phase='RECORDING',token=string.rep('a',32),ends={},normal_end=true,source_version=153,source='baiqi153-pressure-paired-v1',initial_turn=1}")
            g=lua.globals()
            for turn in range(1,6):
                g.Turn=turn;g.Clock=100+20*turn;g.P6PairStage.ends[turn]=True
                self.assertTrue(g.ExposedMembers.P6BaiqiPairEndBridge.Begin(turn,'a'*32))
                g.Turn=turn+1;g.Clock+=2;lua.execute('for _,f in ipairs(Callbacks)do f(0,false)end')
            self.assertEqual([r.to_turn for r in g.P6PairClock.Snapshot(g.P6PairClock).records.values()],[2,3,4,5,6])
            self.assertIsNone(g.P6PairStage.ends[6])






    def test_source146_current_pressure_prefix_runs_all_five_segments_in_both_lua_versions(self):
        for L in (L51,L53):
            lua=L(unpack_returned_tuples=True)
            lua.execute("""
Turn=1;Clock=10;Callbacks={};ExposedMembers={}
Game={GetCurrentGameTurn=function()return Turn end,GetLocalPlayer=function()return 0 end}
Automation={GetTime=function()return Clock end}
Events={PlayerTurnActivated={Add=function(f)Callbacks[#Callbacks+1]=f end,Remove=function()end}}
""")
            lua.execute(clock_prelude(normal_end_bridge=True,source_version=146,pressure_initial_turn=1))
            lua.execute("P6PairStage={phase='RECORDING',token=string.rep('a',32),ends={},normal_end=true,source_version=146,source='baiqi146-pressure-paired-v1',initial_turn=1}")
            g=lua.globals()
            for turn in range(1,6):
                g.Turn=turn;g.Clock=100+20*turn;g.P6PairStage.ends[turn]=True
                self.assertTrue(g.ExposedMembers.P6BaiqiPairEndBridge.Begin(turn,"a"*32))
                g.Turn=turn+1;g.Clock+=2;lua.execute("for _,f in ipairs(Callbacks)do f(0,false)end")
            self.assertEqual([r.to_turn for r in g.P6PairClock.Snapshot(g.P6PairClock).records.values()],[2,3,4,5,6])
            self.assertIsNone(g.P6PairStage.ends[6])

    def test_source147_current_pressure_prefix_runs_all_five_segments_in_both_lua_versions(self):
        for L in (L51,L53):
            lua=L(unpack_returned_tuples=True)
            lua.execute("""
Turn=1;Clock=10;Callbacks={};ExposedMembers={}
Game={GetCurrentGameTurn=function()return Turn end,GetLocalPlayer=function()return 0 end}
Automation={GetTime=function()return Clock end}
Events={PlayerTurnActivated={Add=function(f)Callbacks[#Callbacks+1]=f end,Remove=function()end}}
""")
            lua.execute(clock_prelude(normal_end_bridge=True,source_version=147,pressure_initial_turn=1))
            lua.execute("P6PairStage={phase='RECORDING',token=string.rep('a',32),ends={},normal_end=true,source_version=147,source='baiqi147-pressure-paired-v1',initial_turn=1}")
            g=lua.globals()
            for turn in range(1,6):
                g.Turn=turn;g.Clock=100+20*turn;g.P6PairStage.ends[turn]=True
                self.assertTrue(g.ExposedMembers.P6BaiqiPairEndBridge.Begin(turn,"a"*32))
                g.Turn=turn+1;g.Clock+=2;lua.execute("for _,f in ipairs(Callbacks)do f(0,false)end")
            self.assertEqual([r.to_turn for r in g.P6PairClock.Snapshot(g.P6PairClock).records.values()],[2,3,4,5,6])
            self.assertIsNone(g.P6PairStage.ends[6])

    def test_source148_current_pressure_prefix_runs_all_five_segments_in_both_lua_versions(self):
        for L in (L51,L53):
            lua=L(unpack_returned_tuples=True)
            lua.execute("""
Turn=1;Clock=10;Callbacks={};ExposedMembers={}
Game={GetCurrentGameTurn=function()return Turn end,GetLocalPlayer=function()return 0 end}
Automation={GetTime=function()return Clock end}
Events={PlayerTurnActivated={Add=function(f)Callbacks[#Callbacks+1]=f end,Remove=function()end}}
""")
            lua.execute(clock_prelude(normal_end_bridge=True,source_version=148,pressure_initial_turn=1))
            lua.execute("P6PairStage={phase='RECORDING',token=string.rep('a',32),ends={},normal_end=true,source_version=148,source='baiqi148-pressure-paired-v1',initial_turn=1}")
            g=lua.globals()
            for turn in range(1,6):
                g.Turn=turn;g.Clock=100+20*turn;g.P6PairStage.ends[turn]=True
                self.assertTrue(g.ExposedMembers.P6BaiqiPairEndBridge.Begin(turn,"a"*32))
                g.Turn=turn+1;g.Clock+=2;lua.execute("for _,f in ipairs(Callbacks)do f(0,false)end")
            self.assertEqual([r.to_turn for r in g.P6PairClock.Snapshot(g.P6PairClock).records.values()],[2,3,4,5,6])
            self.assertIsNone(g.P6PairStage.ends[6])

    def test_source149_current_pressure_prefix_runs_all_five_segments_in_both_lua_versions(self):
        for L in (L51,L53):
            lua=L(unpack_returned_tuples=True)
            lua.execute("""
Turn=1;Clock=10;Callbacks={};ExposedMembers={}
Game={GetCurrentGameTurn=function()return Turn end,GetLocalPlayer=function()return 0 end}
Automation={GetTime=function()return Clock end}
Events={PlayerTurnActivated={Add=function(f)Callbacks[#Callbacks+1]=f end,Remove=function()end}}
""")
            lua.execute(clock_prelude(normal_end_bridge=True,source_version=149,pressure_initial_turn=1))
            lua.execute("P6PairStage={phase='RECORDING',token=string.rep('a',32),ends={},normal_end=true,source_version=149,source='baiqi149-pressure-paired-v1',initial_turn=1}")
            g=lua.globals()
            for turn in range(1,6):
                g.Turn=turn;g.Clock=100+20*turn;g.P6PairStage.ends[turn]=True
                self.assertTrue(g.ExposedMembers.P6BaiqiPairEndBridge.Begin(turn,"a"*32))
                g.Turn=turn+1;g.Clock+=2;lua.execute("for _,f in ipairs(Callbacks)do f(0,false)end")
            self.assertEqual([r.to_turn for r in g.P6PairClock.Snapshot(g.P6PairClock).records.values()],[2,3,4,5,6])
            self.assertIsNone(g.P6PairStage.ends[6])

    def test_source150_current_pressure_prefix_runs_all_five_segments_in_both_lua_versions(self):
        for L in (L51,L53):
            lua=L(unpack_returned_tuples=True)
            lua.execute("""
Turn=1;Clock=10;Callbacks={};ExposedMembers={}
Game={GetCurrentGameTurn=function()return Turn end,GetLocalPlayer=function()return 0 end}
Automation={GetTime=function()return Clock end}
Events={PlayerTurnActivated={Add=function(f)Callbacks[#Callbacks+1]=f end,Remove=function()end}}
""")
            lua.execute(clock_prelude(normal_end_bridge=True,source_version=150,pressure_initial_turn=1))
            lua.execute("P6PairStage={phase='RECORDING',token=string.rep('a',32),ends={},normal_end=true,source_version=150,source='baiqi150-pressure-paired-v1',initial_turn=1}")
            g=lua.globals()
            for turn in range(1,6):
                g.Turn=turn;g.Clock=100+20*turn;g.P6PairStage.ends[turn]=True
                self.assertTrue(g.ExposedMembers.P6BaiqiPairEndBridge.Begin(turn,"a"*32))
                g.Turn=turn+1;g.Clock+=2;lua.execute("for _,f in ipairs(Callbacks)do f(0,false)end")
            self.assertEqual([r.to_turn for r in g.P6PairClock.Snapshot(g.P6PairClock).records.values()],[2,3,4,5,6])
            self.assertIsNone(g.P6PairStage.ends[6])

    def test_source151_current_pressure_prefix_runs_all_five_segments_in_both_lua_versions(self):
        for L in (L51,L53):
            lua=L(unpack_returned_tuples=True)
            lua.execute("""
Turn=1;Clock=10;Callbacks={};ExposedMembers={}
Game={GetCurrentGameTurn=function()return Turn end,GetLocalPlayer=function()return 0 end}
Automation={GetTime=function()return Clock end}
Events={PlayerTurnActivated={Add=function(f)Callbacks[#Callbacks+1]=f end,Remove=function()end}}
""")
            lua.execute(clock_prelude(normal_end_bridge=True,source_version=151,pressure_initial_turn=1))
            lua.execute("P6PairStage={phase='RECORDING',token=string.rep('a',32),ends={},normal_end=true,source_version=151,source='baiqi151-pressure-paired-v1',initial_turn=1}")
            g=lua.globals()
            for turn in range(1,6):
                g.Turn=turn;g.Clock=100+20*turn;g.P6PairStage.ends[turn]=True
                self.assertTrue(g.ExposedMembers.P6BaiqiPairEndBridge.Begin(turn,"a"*32))
                g.Turn=turn+1;g.Clock+=2;lua.execute("for _,f in ipairs(Callbacks)do f(0,false)end")
            self.assertEqual([r.to_turn for r in g.P6PairClock.Snapshot(g.P6PairClock).records.values()],[2,3,4,5,6])
            self.assertIsNone(g.P6PairStage.ends[6])

    def test_source152_current_pressure_prefix_runs_all_five_segments_in_both_lua_versions(self):
        for L in (L51,L53):
            lua=L(unpack_returned_tuples=True)
            lua.execute("""
Turn=1;Clock=10;Callbacks={};ExposedMembers={}
Game={GetCurrentGameTurn=function()return Turn end,GetLocalPlayer=function()return 0 end}
Automation={GetTime=function()return Clock end}
Events={PlayerTurnActivated={Add=function(f)Callbacks[#Callbacks+1]=f end,Remove=function()end}}
""")
            lua.execute(clock_prelude(normal_end_bridge=True,source_version=152,pressure_initial_turn=1))
            lua.execute("P6PairStage={phase='RECORDING',token=string.rep('a',32),ends={},normal_end=true,source_version=152,source='baiqi152-pressure-paired-v1',initial_turn=1}")
            g=lua.globals()
            for turn in range(1,6):
                g.Turn=turn;g.Clock=100+20*turn;g.P6PairStage.ends[turn]=True
                self.assertTrue(g.ExposedMembers.P6BaiqiPairEndBridge.Begin(turn,"a"*32))
                g.Turn=turn+1;g.Clock+=2;lua.execute("for _,f in ipairs(Callbacks)do f(0,false)end")
            self.assertEqual([r.to_turn for r in g.P6PairClock.Snapshot(g.P6PairClock).records.values()],[2,3,4,5,6])
            self.assertIsNone(g.P6PairStage.ends[6])







    def test_source145_prefixes_remain_byte_exact(self):
        for pressure,expected in ((None,'4554f4a51928199e56ffbfc2dddcf449a974d03feb2b33a728282622fa602f0b'),(1,'d65f6c552893e16b86894726bb1c698996a29a90f2d5b271af0d54c681341f9c')):
            text=clock_prelude(normal_end_bridge=True,source_version=145,pressure_initial_turn=pressure)
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),expected)

    def test_source146_prefixes_remain_byte_exact(self):
        for pressure,expected in ((None,'f208ef24a5dfb61a3e67c469b59c7008ec2aaeaa70085bd73d668fcb67a5a933'),(1,'662c953f2dcf407d59acad981d495b9cff3fb01a4ef836591e9b90b048d1bcfd')):
            text=clock_prelude(normal_end_bridge=True,source_version=146,pressure_initial_turn=pressure)
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),expected)

    def test_source147_prefixes_remain_byte_exact(self):
        for pressure,expected in ((None,'c872aa1ed23494e1e68548029b4c0612fb958001458eb64e1ccf81f3e431be8b'),(1,'cee6fd873b60a4bd0606772a83421db635f4d16f20a302dab60db1d195f64f6d')):
            text=clock_prelude(normal_end_bridge=True,source_version=147,pressure_initial_turn=pressure)
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),expected)

    def test_source148_prefixes_remain_byte_exact(self):
        for pressure,expected in ((None,'50776a504b9faa56c076197cd341aef22180a4b6081f7ef55e8d9d803941329e'),(1,'aa9adad19a8e6dc3a8996ec8cfd29d43a88426bc43f88e115548ad779fd708f7')):
            text=clock_prelude(normal_end_bridge=True,source_version=148,pressure_initial_turn=pressure)
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),expected)

    def test_source149_prefixes_remain_byte_exact(self):
        for pressure,expected in ((None,'87f9bd0d9adf002c56d634a0bb3888a750eec27a23306ea04380da9b0ce98f5b'),(1,'8152088523417961f3631d17264c5594a95e09fe52fb99cc2fa3f3d4a73f0539')):
            text=clock_prelude(normal_end_bridge=True,source_version=149,pressure_initial_turn=pressure)
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),expected)

    def test_source150_prefixes_remain_byte_exact(self):
        for pressure,expected in ((None,'0d2a8e074657da12889bf520e14bd8d1f3fc3c4de73c1188b08cf5ab70d07847'),(1,'1cd6fc3f7d57db7419d7982d1c03eb05d17fa79a35f0cdefcb49bfb80a26d9a2')):
            text=clock_prelude(normal_end_bridge=True,source_version=150,pressure_initial_turn=pressure)
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),expected)

    def test_source151_prefixes_remain_byte_exact(self):
        for pressure,expected in ((None,'a763e9f6f2cdcb317ba813cb52a7d03e8bb7d267d31e9dbc6a3607fcbb8c9564'),(1,'71411c6aa2389099b6e714fa8c248d50b3b7b3c064da6a4865a3439a4e12f295')):
            text=clock_prelude(normal_end_bridge=True,source_version=151,pressure_initial_turn=pressure)
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),expected)


if __name__=="__main__":unittest.main()
