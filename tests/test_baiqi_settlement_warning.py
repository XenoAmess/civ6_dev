"""Fresh native negative warnings veto settlement; other guards still decide."""
from pathlib import Path
import json
import unittest

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class SettlementWarningControllerTests(unittest.TestCase):
    controller_source = None

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for path in ('tests/lua/mock_world.lua', 'tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua', 'tests/lua/mock_settlement_border.lua',
                     'mod/Baiqi/Lua/BaiqiConfig.lua', 'mod/Baiqi/Lua/BaiqiPolicy.lua',
                     'mod/Baiqi/Lua/BaiqiPlanner.lua', 'mod/Baiqi/Lua/BaiqiSettlementWarning.lua'):
            self.lua.execute((ROOT / path).read_text(encoding='utf-8'))
        source = self.controller_source or (
            ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
        self.support = self.lua.execute(source + '\nreturn KnownExpansionSupport')
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController
        self.w.foreign = False
        self.w.ownX, self.w.ownY = 2, 3
        self.lua.execute('''
            local w=TestWorld;w.ruleset='RULESET_EXPANSION_2';w.loyalty=100;w.rate=20
            w.warnings={};w.warningCalls=0
            w.objects.city.GetCulturalIdentity=function()
              return {GetLoyalty=function()return w.loyalty end,
                GetLoyaltyPerTurn=function()return w.rate end}
            end
            Map.GetContinentPlotsLoyalty=function(...)
              assert(select('#',...)==0);w.warningCalls=w.warningCalls+1
              return w.warnings
            end
        ''')
        self.w.withSettler = False
        self.c.RunNow(False)
        self.w.withSettler = True

    def run_now(self, count=2):
        for _ in range(count):
            self.c.RunNow()
        self.assertNotIn('脚本错误', self.c.GetStatus())
        for request in self.w.unitRequests.values():
            self.assertEqual(request.unit, 2)

    def orders(self, operation):
        return [r for r in self.w.unitRequests.values() if r.op == operation]

    def support47(self):
        return self.support(self.lua.globals().Map.GetPlotByIndex(47),
                            self.w.objects.player, 7)

    def select_then_arrive(self):
        self.run_now(1)
        self.assertEqual(len(self.orders(10)), 1)
        self.w.turn += 1
        self.w.settlerPlot = 47

    def test_negative_warning_vetoes_recommendation_without_foreign_roster(self):
        self.w.warnings[47] = -6
        self.run_now()
        self.assertEqual(self.orders(10), [])
        self.assertEqual(self.orders(11), [])
        self.assertEqual(self.support47(), (False, 'native_negative_loyalty_warning'))

    def test_retained_goal_with_new_negative_warning_cannot_found(self):
        self.select_then_arrive()
        self.w.warnings[47] = -6
        self.run_now()
        self.assertEqual(self.orders(11), [])
        self.assertIsNone(self.w.goalProposals['2'])

    def test_warning_appearing_during_final_native_found_check_vetoes_write(self):
        self.select_then_arrive()
        self.lua.execute('''
            local original=UnitManager.CanStartOperation;local n=0
            UnitManager.CanStartOperation=function(u,op,...)
              local allowed=original(u,op,...)
              if op==11 then n=n+1;if n==2 then TestWorld.warnings[47]=-6 end end
              return allowed
            end
        ''')
        self.run_now()
        self.assertEqual(self.orders(11), [])

    def test_negative_warning_has_no_cache_after_native_value_changes(self):
        self.w.warnings[47] = -6
        self.assertEqual(self.support47()[0], False)
        self.w.warnings[47] = 0
        self.assertEqual(self.support47()[0], True)

    def test_nonnegative_warning_does_not_override_existing_city_decline(self):
        self.w.warnings[47] = 0
        self.w.rate = -1
        self.assertEqual(self.support47()[0], False)

    def test_missing_entry_remains_unknown_and_foreign_border_still_blocks(self):
        self.w.foreign = True
        self.w.ownX, self.w.ownY = 3, 4
        self.assertEqual(self.support47()[0], False)
        env = self.lua.table_from({k: self.lua.globals()[k]
                                   for k in ('GameConfiguration', 'Map', 'PlayersVisibility')})
        self.assertEqual(self.lua.globals().BaiqiSettlementWarning.Read(env, 7, 47),
                         ('UNKNOWN', None, 'no_warning_entry'))

    def test_unknown_native_warning_keeps_previous_geometry_without_safety_claim(self):
        self.lua.execute("Map.GetContinentPlotsLoyalty=function()error('unavailable')end")
        self.assertEqual(self.support47()[0], True)
        self.w.foreign = True
        self.w.ownX, self.w.ownY = 3, 4
        self.assertEqual(self.support47()[0], False)

    def test_base_does_not_call_native_loyalty_map(self):
        self.w.ruleset = 'RULESET_STANDARD'
        self.w.warnings[47] = -6
        self.assertEqual(self.support47()[0], True)
        self.assertEqual(self.w.warningCalls, 0)

    def test_first_capital_exception_does_not_query_native_warning(self):
        self.w.withCity = False
        self.w.warnings[47] = -6
        self.run_now(1)
        self.assertEqual(len(self.orders(11)), 1)
        self.assertEqual(self.w.warningCalls, 0)

    def test_missing_reader_waits_without_throw_or_permission(self):
        for statement in ('BaiqiSettlementWarning=nil', 'BaiqiSettlementWarning={}',
                          'BaiqiSettlementWarning=4'):
            with self.subTest(statement=statement):
                self.setUp()
                self.lua.execute(statement)
                self.assertEqual(self.support47(), (None, 'loyalty_warning_unavailable'))

    def test_unexpected_reader_throw_is_contained_by_support_boundary(self):
        self.lua.execute("BaiqiSettlementWarning.Read=function()error('unexpected')end")
        self.assertIsNone(self.support47()[0])

    def test_unrevealed_target_does_not_read_warning_map(self):
        self.w.hidden[47] = True
        self.assertIsNone(self.support47()[0])
        self.assertEqual(self.w.warningCalls, 0)


class SettlementWarningComponentTests(unittest.TestCase):
    def test_product_reuses_exact_reader_and_its_existing_34_cases(self):
        source = (ROOT / 'mod/Baiqi/Lua/BaiqiSettlementWarning.lua').read_text(encoding='utf-8')
        self.assertEqual(source, (ROOT / 'tools/lua/settlement_warning_info.lua').read_text(encoding='utf-8'))
        data = json.loads((ROOT / 'tests/fixtures/settlement_warning_info_cases.json').read_text(encoding='utf-8'))
        self.assertEqual(len(data['cases']), 34)
        for name, check in data['cases'].items():
            with self.subTest(case=name):
                lua = LuaRuntime(unpack_returned_tuples=True)
                lua.execute(data['fixture'])
                lua.globals().M = lua.execute(source)
                lua.execute(check)


if __name__ == '__main__':
    unittest.main()
