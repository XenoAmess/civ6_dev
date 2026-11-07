"""Actual gameplay publisher bootstrap and private-control suppression."""
import unittest
from tools.static_control_source import transform
import test_baiqi_settler_goals_core as core


class SettlerGoalsGameplayTests(unittest.TestCase):
    def setUp(self):
        core.SettlerGoalsCoreTests.setUp(self)
        self.source=(core.ROOT/'mod/Baiqi/Lua/BaiqiSettlerGoalsGameplay.lua').read_text(encoding='utf-8')
        self.lua.execute('''BaiqiConfig=C;ExposedMembers={};function include()end
            for k,v in pairs(E)do _G[k]=v end''')

    def test_bootstrap_reads_and_repeated_load_never_write(self):
        self.lua.execute(self.source)
        self.assertEqual(self.lua.eval('ExposedMembers.BaiqiSettlerGoalsBridge.Read(0,393216)')[:2],('READY',None))
        self.lua.execute('original=ExposedMembers.BaiqiSettlerGoalsBridge')
        self.lua.execute(self.source)
        self.assertTrue(self.lua.eval('original==ExposedMembers.BaiqiSettlerGoalsBridge'))
        self.assertEqual(self.w.writes,0)

    def test_actual_published_bridge_remembers_without_found_property_access(self):
        self.lua.execute(self.source)
        self.assertEqual(self.lua.eval('ExposedMembers.BaiqiSettlerGoalsBridge.Remember(0,393216,21,1,2)')[0],'READY')
        self.assertEqual(self.w.writes,1)

    def test_private_static_control_closes_both_metadata_mutators(self):
        source,_=transform(self.source,'Lua/BaiqiSettlerGoalsGameplay.lua',84)
        self.lua.execute(source)
        self.assertEqual(self.lua.eval('ExposedMembers.BaiqiSettlerGoalsBridge.Remember(0,393216,21,1,2)')[0],'UNAVAILABLE')
        self.assertEqual(self.lua.eval('ExposedMembers.BaiqiSettlerGoalsBridge.Forget(0,393216)')[0],'UNAVAILABLE')
        self.assertEqual(self.lua.eval('ExposedMembers.BaiqiSettlerGoalsBridge.Read(0,393216)')[0],'READY')
        self.assertEqual(self.w.writes,0)

    def test_foreign_bridge_is_retained(self):
        self.lua.execute("ExposedMembers.BaiqiSettlerGoalsBridge={marker='foreign',version=1}")
        self.lua.execute(self.source)
        self.assertEqual(self.lua.eval('ExposedMembers.BaiqiSettlerGoalsBridge.marker'),'foreign')
        self.assertEqual(self.w.writes,0)


if __name__=='__main__':unittest.main()
