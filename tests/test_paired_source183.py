"""Execute source183 performance consumers with synthetic transport, never Native."""
from copy import deepcopy
from pathlib import Path
import json
import subprocess
import unittest

from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
from tools import paired_normal_end as end
from tools.analyze_paired_turns import analyze_pairs, analyze_pressure_pairs
from tools.analyze_plan_capture import analyze_plan_capture, analyze_pressure_plan_capture
from tools.paired_player_callback import make_callback
from tools.run_paired_acceptance import run
import test_paired_source151_preflight as preflight_fixture
from test_paired_normal_driver import NormalHarness
from test_pressure_paired_driver import PressureHarness
from test_analyze_plan_capture import capture
import test_analyze_pressure_plan_capture as pressure_plan_fixture


READY = '''
Game.IsAllowStrategicCommands=function()return true end
UI.CanEndTurn=function()return true end
UI.HasSentTurnComplete=function()return false end
Players[0].CanUnreadyTurn=function()return false end
CheckUnitsHaveMovesState=function()return false end
CheckCityRangeAttackState=function()return false end
'''


class Source183PairedTests(unittest.TestCase):
    def endpoint(self, runtime, pressure, change=''):
        return preflight_fixture.Source151PreflightTests().invoke(runtime, pressure, change, source=183)

    def harness(self, pressure=False):
        h = PressureHarness(source_version=183) if pressure else NormalHarness(source_version=183)
        h.lua.execute(READY)
        return h

    def ordinary(self, h, variant='enabled', callback=None):
        def record(name, value):
            with (h.ledger/(name+'.json')).open('x', encoding='utf-8') as f:
                json.dump(value, f)
        cb = make_callback(h.query, lambda *args: 'P6_PAIR142_NO_NEW_LEGAL_MILITARY_SKIP',
                           record, h.visible, expected_source_version=183)
        return run(h.query, h.visible, h.close, h.now, h.sleep, h.emit, h.ledger,
                   variant=variant, fixture_sha256='0'*64, expected_source_version=183,
                   request_normal_end=cb if callback is None else callback)

    def test_both_lua_versions_and_calendars_issue_once_after_clock(self):
        for runtime in (Lua51, Lua53):
            for pressure in (False, True):
                with self.subTest(runtime=runtime, pressure=pressure):
                    vm, issue, codes = self.endpoint(runtime, pressure)
                    self.assertTrue(issue()['requested'])
                    self.assertEqual((vm.globals().T.begins, vm.globals().T.requests), (1, 1))
                    self.assertNotIn('UserForced', codes[0])

    def test_current183_preflight_ports_fail_closed_before_clock_and_action(self):
        ports = ('CheckUnitsHaveMovesState', 'CheckCityRangeAttackState',
                 'Players[0].CanUnreadyTurn', 'UI.HasSentTurnComplete')
        changes = [port+'='+value for port in ports for value in ('nil', 'false', '3')]
        changes += [port+'=function()return '+value+' end' for port in ports
                    for value in ('true', 'nil', '0', "'false'")]
        changes += ['UI.IsGameCoreBusy=function()return true end',
                    'UI.CanEndTurn=function()return false end',
                    "ExposedMembers.P6BaiqiPairEndBridge.source_version=172"]
        for runtime in (Lua51, Lua53):
            for pressure in (False, True):
                for change in changes:
                    with self.subTest(runtime=runtime, pressure=pressure, change=change):
                        vm, issue, _ = self.endpoint(runtime, pressure, change)
                        with self.assertRaises(Exception):
                            issue()
                        self.assertEqual((vm.globals().T.begins, vm.globals().T.requests), (0, 0))

    def test_current183_five_groups_real_driver_to_analyzers(self):
        for pressure in (False, True):
            pairs = []
            for number in range(1, 6):
                order = ['enabled', 'control'] if number % 2 else ['control', 'enabled']
                pair = dict(pair=number, order=order)
                for variant in order:
                    h = self.harness(pressure)
                    pair[variant] = h.run(variant=variant) if pressure else self.ordinary(h, variant)
                    first = 1 if pressure else 85
                    self.assertEqual(list(h.t.actions.values()), list(range(first, first+5)))
                    self.assertFalse((h.ledger/f'end-{first+5}.json').exists())
                    self.assertTrue(h.lua.eval('P6PairClock:Snapshot().retired'))
                pairs.append(pair)
            before = deepcopy(pairs)
            result = (analyze_pressure_pairs(pairs, '0'*64, initial_turn=1, expected_source_version=183)
                      if pressure else analyze_pairs(pairs, '0'*64, expected_source_version=183,
                                                    require_ordinary=True))
            self.assertEqual(pairs, before)
            self.assertEqual(len(result['matched_rows']), 25)
            pairs[0]['control']['source_version'] = 172
            with self.assertRaises(ValueError):
                if pressure:
                    analyze_pressure_pairs(pairs, '0'*64, initial_turn=1, expected_source_version=183)
                else:
                    analyze_pairs(pairs, '0'*64, expected_source_version=183, require_ordinary=True)

    def test_unknown_receipt_after_actual_fixture_action_is_never_replayed(self):
        for pressure in (False, True):
            h = self.harness(pressure)
            original = h.query
            def lost(context, code):
                messages = original(context, code)
                if 'UI.RequestAction' in code:
                    raise OSError('fixture action happened; receipt unknown')
                return messages
            h.query = lost
            with self.assertRaises(OSError):
                h.run() if pressure else self.ordinary(h)
            self.assertEqual(list(h.t.actions.values()), [1 if pressure else 85])
            self.assertEqual(len(list(h.ledger.glob('end-*.json'))), 1)

    def test_wrong_pressure_receipt_stops_before_any_action(self):
        h = self.harness(True)
        def bad(turn, token):
            return dict(turn=turn, token=token, requested=True, forced=False, initial_turn=1,
                        source='baiqi172-pressure-paired-v1', source_version=183)
        with self.assertRaisesRegex(RuntimeError, 'issuance receipt'):
            h.run(bad)
        self.assertEqual(list(h.t.actions.values()), [])

    def test_pressure_tag_cannot_enter_ordinary_analyzer_without_calendar(self):
        h = self.harness()
        data = self.ordinary(h)
        data['source'] = 'baiqi183-pressure-paired-v1'
        from tools.analyze_paired_turns import validate_capture_mode
        with self.assertRaisesRegex(ValueError, 'pressure analyzer'):
            validate_capture_mode(data, 183, True)

    def test_plan_analyzers_current_tags_and_accounting(self):
        ordinary = capture()
        ordinary['source'] = 'baiqi183-stageA-v1'
        pressure = pressure_plan_fixture.PressureAnalyzerTests()._pressure(210)
        pressure['source'] = 'baiqi183-pressure-stageA-v1'
        for data, analyze in ((ordinary, analyze_plan_capture),
                              (pressure, analyze_pressure_plan_capture)):
            before = deepcopy(data)
            self.assertTrue(analyze(data, expected_source_version=183)['overall_budget_ok'])
            self.assertEqual(data, before)
            data['profile']['dropped'] = 1
            with self.assertRaises(ValueError):
                analyze(data, expected_source_version=183)
            data['profile']['dropped'] = 0
            data['source'] = data['source'].replace('183', '172')
            with self.assertRaises(ValueError):
                analyze(data, expected_source_version=183)

    def test_invalid_version_types_reject_before_transport_or_child(self):
        for version in (True, 183.0, '183', 184):
            calls = []
            q = lambda *args: calls.append(args)
            with self.assertRaises(ValueError):
                end.request_end(q, 85, 'a'*32, expected_source_version=version)
            with self.assertRaises(ValueError):
                end.request_pressure_end(q, 1, 'a'*32, initial_turn=1,
                                         expected_source_version=version)
            with self.assertRaises(ValueError):
                make_callback(q, q, q, q, expected_source_version=version)
            self.assertEqual(calls, [])

    def test_historical_140_to172_renderings_still_match_fixed_parent(self):
        root = Path(__file__).resolve().parents[1]
        old = {}
        source = subprocess.check_output(['git', 'show',
            '2ce2ec3db20d4c52edefc84dc7df25dd10d60008:tools/paired_normal_end.py'], cwd=root).decode()
        exec(compile(source, 'fixed-pre183-admission', 'exec'), old)
        for pressure, versions in ((False, range(140, 173)), (True, range(142, 173))):
            for version in versions:
                captures = [[], []]
                for index, ns in enumerate((old, vars(end))):
                    def query(context, code):
                        captures[index].append((context, code))
                        marker = 'P6_PRESSURE_PAIR_ORDINARY_ISSUED' if pressure else 'P6_PAIR_ORDINARY_ISSUED'
                        return [{'tag': -1, 'payload': 'O\0ActionPanel: '+marker+'\t85\t'+'a'*32+('\t85' if pressure else '')}]
                    if pressure:
                        ns['request_pressure_end'](query, 85, 'a'*32, initial_turn=85,
                                                   expected_source_version=version)
                    else:
                        ns['request_end'](query, 85, 'a'*32, expected_source_version=version)
                self.assertEqual(captures[0], captures[1])


if __name__ == '__main__':
    unittest.main()
