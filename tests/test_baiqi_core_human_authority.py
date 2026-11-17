"""Exercise actual Core consumers: only an absent config port permits fallback."""
import json
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime
import test_baiqi_creative_intents as creative
import test_baiqi_gp_intents as great_person
import test_baiqi_prophet_intents as prophet
import test_baiqi_food_tile_core_human as food
import test_baiqi_settler_goals_core as goals
from archaeology_intent_harness import archaeology_runtime
from naturalist_intent_harness import core_runtime
from purchase_intent_harness import make_purchase_core
from missionary_purchase_core_harness import make_missionary_core

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = ('archaeology', 'creative', 'food', 'great_person', 'missionary_purchase',
            'naturalist', 'naturalist_purchase', 'prophet', 'religious',
            'settlement_state', 'settlement_intent', 'settler_goals')


def world(family):
    """Reuse the product's existing isolated Core fixtures, without native orders."""
    if family in ('creative', 'great_person', 'prophet'):
        cls = {'creative': creative.CreativeIntentTests,
               'great_person': great_person.GreatPersonIntentTests,
               'prophet': prophet.ProphetIntentTests}[family]
        fixture = cls(); fixture.setUp()
        lua, env, pid = fixture.lua, fixture.h.core, 7
        call, ready = lambda: fixture.bridge.Inspect(7, 4)[0], 'OPEN'
    elif family == 'food':
        lua = food.FoodTileCoreHumanTests().world()
        env, pid = lua.globals(), 0
        call = lambda: lua.globals().ExposedMembers.BaiqiFoodTileRescueBridge.Inspect(0, 458758)[0]
        ready = 'OPEN'
    elif family == 'archaeology':
        lua, module, _ = archaeology_runtime()
        env, pid = lua.globals(), 7
        call, ready = lambda: module.bridge.Inspect(7, 4)[0], 'OPEN'
    elif family == 'naturalist':
        lua, bridge = core_runtime()
        env, pid = lua.globals(), 4
        call, ready = lambda: bridge.Inspect(4, 100001)[0], 'OPEN'
    elif family in ('naturalist_purchase', 'missionary_purchase', 'religious'):
        lua = make_purchase_core() if family == 'naturalist_purchase' else make_missionary_core()
        env, pid, ready = lua.globals(), 0, 'OPEN'
        name = {'naturalist_purchase': 'BaiqiNaturalistPurchaseBridge',
                'missionary_purchase': 'BaiqiMissionaryPurchaseBridge',
                'religious': 'BaiqiReligiousIntentBridge'}[family]
        bridge = env.ExposedMembers[name]
        call = (lambda: bridge.Inspect(0, 6000000)[0]) if family == 'religious' else (lambda: bridge.Inspect(0)[0])
    elif family == 'settler_goals':
        fixture = goals.SettlerGoalsCoreTests(); fixture.setUp()
        lua, env, pid = fixture.lua, fixture.lua.globals().E, 0
        call, ready = lambda: lua.globals().API.Read(0, 393216)[0], 'READY'
    else:
        lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('BaiqiSettlementJournal', 'BaiqiSettlementStateCore', 'BaiqiSettlementIntentCore'):
            lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        lua.execute(json.loads((ROOT / 'tests/fixtures/settlement_intent_core_cases.json').read_text(encoding='utf-8'))['fixture_lua'])
        api = lua.eval('Init()')
        env, pid = lua.globals().E, 0
        call, ready = (lambda: api.Snapshot(0)[0], 'READY') if family == 'settlement_state' else (lambda: api.Inspect(0, 7929900)[0], 'OPEN')
    lua.globals().AUTH_ENV, lua.globals().AUTH_PID = env, pid
    lua.execute('''
      AUTH={fallback=0,reads=0,writes=0}
      local p=AUTH_ENV.Players[AUTH_PID]
      p.IsHuman=function() AUTH.fallback=AUTH.fallback+1;return true end
      local get,set=p.GetProperty,p.SetProperty
      p.GetProperty=function(...) AUTH.reads=AUTH.reads+1;return get(...) end
      p.SetProperty=function(...) AUTH.writes=AUTH.writes+1;return set(...) end
    ''')
    return lua, call, ready


class CoreHumanAuthorityTests(unittest.TestCase):
    def test_absent_config_port_uses_actual_player_fallback(self):
        for family in FAMILIES:
            with self.subTest(family=family):
                lua, call, ready = world(family)
                lua.execute('AUTH_ENV.PlayerConfigurations[AUTH_PID].IsHuman=nil')
                self.assertEqual(call(), ready)
                self.assertGreater(lua.globals().AUTH.fallback, 0)
                self.assertGreater(lua.globals().AUTH.reads, 0)

    def test_present_nonfunction_config_never_reads_player_or_journal(self):
        for family in FAMILIES:
            for value in ('false', '0', '"true"', '{}', 'setmetatable({},{__call=function()return true end})'):
                with self.subTest(family=family, value=value):
                    lua, call, _ = world(family)
                    lua.execute('AUTH_ENV.PlayerConfigurations[AUTH_PID].IsHuman=' + value)
                    self.assertEqual(call(), 'UNAVAILABLE')
                    auth = lua.globals().AUTH
                    self.assertEqual((auth.fallback, auth.reads, auth.writes), (0, 0, 0))

    def test_config_function_false_unknown_or_throw_never_falls_back(self):
        for family in FAMILIES:
            for result in ('return false', 'return nil', 'return 1', 'error("unknown")'):
                with self.subTest(family=family, result=result):
                    lua, call, _ = world(family)
                    lua.execute('AUTH_ENV.PlayerConfigurations[AUTH_PID].IsHuman=function()' + result + ' end')
                    self.assertEqual(call(), 'UNAVAILABLE')
                    auth = lua.globals().AUTH
                    self.assertEqual((auth.fallback, auth.reads, auth.writes), (0, 0, 0))

    def test_true_config_does_not_consult_player(self):
        for family in FAMILIES:
            with self.subTest(family=family):
                lua, call, ready = world(family)
                lua.execute('''AUTH_ENV.PlayerConfigurations[AUTH_PID].IsHuman=function()return true end
                  AUTH_ENV.Players[AUTH_PID].IsHuman=function()error('must not fall back')end''')
                self.assertEqual(call(), ready)
                self.assertGreater(lua.globals().AUTH.reads, 0)

    def test_missing_config_rejects_uncertain_player_without_journal_access(self):
        for family in FAMILIES:
            for port in ('nil', 'false', '0', '{}', 'function()return false end',
                         'function()return nil end', 'function()return 1 end',
                         'function()error("unknown")end'):
                with self.subTest(family=family, player_port=port):
                    lua, call, _ = world(family)
                    lua.execute('AUTH_ENV.PlayerConfigurations[AUTH_PID].IsHuman=nil;'
                                'AUTH_ENV.Players[AUTH_PID].IsHuman=' + port)
                    self.assertEqual(call(), 'UNAVAILABLE')
                    self.assertEqual((lua.globals().AUTH.reads, lua.globals().AUTH.writes), (0, 0))

    def test_settlement_armed_record_survives_denied_prepare_commit_and_inspect(self):
        lua, _, _ = world('settlement_intent')
        lua.execute('''
          m.bank=Arm();local before=m.bank;local api=Protocol()
          E.PlayerConfigurations[0].IsHuman=false
          local r=api.Prepare(0,7929900,906,26,20,'0:148:1');assert(r=='UNAVAILABLE')
          local grant=api.Commit(0,7929900,'settle:0:1','0:148:1');assert(grant==false)
          local s=api.Inspect(0,7929900);assert(s=='UNAVAILABLE')
          local init=api.Initialize(0,false);assert(init=='UNAVAILABLE')
          assert(AUTH.fallback==0 and AUTH.reads==0 and AUTH.writes==0)
          assert(m.bank==before and m.bank.operations['7929900'].stage=='ARMED')
          assert(m.bank.operations['7929900'].token=='settle:0:1' and m.bank.serial==1)
        ''')


if __name__ == '__main__':
    unittest.main()
