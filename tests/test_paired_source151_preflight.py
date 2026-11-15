"""Execute both real END builders in Lua; no engine or game inputs."""
from pathlib import Path
import subprocess
import unittest

from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
from tools import paired_normal_end as end


class Source151PreflightTests(unittest.TestCase):
    def invoke(self, runtime, pressure, change='', source=151):
        vm = runtime()
        vm.execute('''
T={begins=0,requests=0,logs={}}
Game={GetCurrentGameTurn=function()return 85 end,GetLocalPlayer=function()return 0 end,IsAllowStrategicCommands=function()return true end}
Players={[0]={IsTurnActive=function()return true end,CanUnreadyTurn=function()return false end}}
UI={CanEndTurn=function()return true end,IsGameCoreBusy=function()return false end,IsProcessingMessages=function()return false end,HasSentTurnComplete=function()return false end}
CheckUnitsHaveMovesState=function()return false end
CheckCityRangeAttackState=function()return false end
ActionTypes={ACTION_ENDTURN=2}
UI.RequestAction=function(...)assert(select('#',...)==1 and (...)==2);assert(T.begins==1);T.requests=T.requests+1 end
print=function(...)local a={...};for i=1,select('#',...)do a[i]=tostring(a[i])end;T.logs[#T.logs+1]=table.concat(a,'\t')end
''')
        vm.globals().source_version = source
        marker = 'baiqi-paired-end-bridge-pressure-v1' if pressure else 'baiqi-paired-end-bridge-v1'
        vm.globals().marker = marker
        vm.execute('''ExposedMembers={P6BaiqiPairEndBridge={marker=marker,source_version=source_version,source='baiqi'..source_version..'-pressure-paired-v1',initial_turn=85,Begin=function(turn,token)assert(turn==85 and #token==32);T.begins=T.begins+1;return true end}}''')
        vm.execute(change)
        codes = []

        def query(context, code):
            self.assertEqual(context, 'ActionPanel')
            codes.append(code)
            vm.execute(code)
            return [{'tag': -1, 'payload': 'O\0ActionPanel: '+s} for s in vm.globals().T.logs.values()]

        def run():
            return (end.request_pressure_end(query, 85, 'a'*32, initial_turn=85, expected_source_version=source)
                    if pressure else end.request_end(query, 85, 'a'*32, expected_source_version=source))
        return vm, run, codes

    def test_valid_both_builders_issue_once_after_begin(self):
        for runtime in (Lua51, Lua53):
            for pressure in (False, True):
                with self.subTest(runtime=runtime, pressure=pressure):
                    vm, run, _ = self.invoke(runtime, pressure)
                    self.assertTrue(run()['requested'])
                    self.assertEqual((vm.globals().T.begins, vm.globals().T.requests), (1, 1))

    def assert_rejects(self, changes):
        for runtime in (Lua51, Lua53):
            for pressure in (False, True):
                for change in changes:
                    with self.subTest(runtime=runtime, pressure=pressure, change=change):
                        vm, run, _ = self.invoke(runtime, pressure, change)
                        with self.assertRaises(Exception):
                            run()
                        self.assertEqual((vm.globals().T.begins, vm.globals().T.requests), (0, 0))

    def test_city_range_and_unit_move_prompts_reject_before_clock(self):
        self.assert_rejects([name+'=function()return true end' for name in
                             ('CheckCityRangeAttackState', 'CheckUnitsHaveMovesState')])

    def test_unready_or_already_sent_reject_before_clock(self):
        self.assert_rejects([name+'=function()return true end' for name in
                             ('Players[0].CanUnreadyTurn', 'UI.HasSentTurnComplete')])

    def test_missing_or_non_function_ports_reject_before_clock(self):
        self.assert_rejects([name+'='+value for name in
                             ('CheckCityRangeAttackState', 'CheckUnitsHaveMovesState',
                              'Players[0].CanUnreadyTurn', 'UI.HasSentTurnComplete')
                             for value in ('nil', 'false', '3')])

    def test_non_boolean_port_results_do_not_become_false(self):
        self.assert_rejects([name+'=function()return '+value+' end' for name in
                             ('CheckCityRangeAttackState', 'CheckUnitsHaveMovesState',
                              'Players[0].CanUnreadyTurn', 'UI.HasSentTurnComplete')
                             for value in ('nil', '0', "'false'")])

    def test_historical_generated_lua_bytes_match_parent(self):
        # Use the frozen pre-change file, independent of the new renderer.
        root = Path(__file__).resolve().parents[1]
        old_source = subprocess.check_output(
            ['git', 'show', '2a98d6e73b586b9344b7a51254070fa69c7573a5:tools/paired_normal_end.py'],
            cwd=root).decode('utf-8')
        old = {}
        exec(compile(old_source, 'pre151-tool-guard', 'exec'), old)
        for pressure, versions in ((False, range(140, 151)), (True, range(142, 151))):
            for source in versions:
                with self.subTest(pressure=pressure, source=source):
                    _, run, new_codes = self.invoke(Lua51, pressure, source=source)
                    run()
                    saved = []

                    def capture(context, code):
                        saved.append(code)
                        marker = 'P6_PRESSURE_PAIR_ORDINARY_ISSUED' if pressure else 'P6_PAIR_ORDINARY_ISSUED'
                        payload = marker+'\t85\t'+'a'*32+('\t85' if pressure else '')
                        return [{'tag': -1, 'payload': 'O\0ActionPanel: '+payload}]
                    if pressure:
                        old['request_pressure_end'](capture, 85, 'a'*32, initial_turn=85, expected_source_version=source)
                    else:
                        old['request_end'](capture, 85, 'a'*32, expected_source_version=source)
                    self.assertEqual(new_codes, saved)


if __name__ == '__main__':
    unittest.main()
