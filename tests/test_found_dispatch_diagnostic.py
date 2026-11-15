"""Private instrumentation must preserve the real live-grant consumer contract."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from tests import test_baiqi_found_city_receipt as receipt
from tests import test_baiqi_found_city_live_dispatch as live_dispatch
from tools.build_found_dispatch_diagnostic import ROOT, HELPER, build, instrument, recover
from tools.build_mod import digest

CONTROLLER = ROOT / 'mod/Baiqi/Lua/BaiqiController.lua'


class FoundDispatchDiagnosticTests(unittest.TestCase):
    def test_real_package_recovery_and_all_file_hashes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.local-model') as temp:
            out = Path(temp) / 'prepared'
            result = build(out)
            self.assertEqual(result['files'], 119)
            self.assertEqual(recover((out / 'Baiqi/Lua/BaiqiController.lua').read_bytes()), CONTROLLER.read_bytes())
            changed = [n for n, sha in result['source_hashes'].items()
                       if sha != result['instrumented_hashes'][n]]
            self.assertEqual(changed, ['Lua/BaiqiController.lua'])
            archive = out / f'Baiqi-found-dispatch{result["source_version"]}.zip'
            with zipfile.ZipFile(archive) as z:
                self.assertEqual(set(z.namelist()), {'Baiqi/' + n for n in result['source_hashes']})
                for n in result['source_hashes']:
                    self.assertEqual(z.read('Baiqi/' + n), (out / 'Baiqi' / n).read_bytes())
            self.assertEqual(digest(archive), result['archive_sha256'])
            with self.assertRaises(ValueError):
                build(out)

    def test_unknown_duplicate_and_already_instrumented_sources_reject(self):
        raw = CONTROLLER.read_bytes()
        for value in (b'', raw + raw, instrument(raw)):
            with self.subTest(length=len(value)), self.assertRaises(ValueError):
                instrument(value)
        with self.assertRaises(ValueError):
            recover(raw)

    def test_ring_snapshot_is_bounded_copied_and_scalar_without_native_environment(self):
        for engine in (L51, L53):
            lua = engine(unpack_returned_tuples=True)
            record, snapshot = lua.execute(HELPER.read_text(encoding='utf-8'))
            for i in range(40):
                record(2, '7:1:9', 1, 1, 'qualification', 'qualify_error', False, False)
            actual = snapshot()
            self.assertEqual((len(actual.events), actual.total, actual.dropped), (32, 40, 8))
            for row in actual.events.values():
                self.assertTrue(all(type(v) in (int, float, str, bool) for v in row.values()))
            actual.events[1].reason = 'foreign mutation'
            actual.events[2] = None
            self.assertEqual(snapshot().events[1].reason, 'qualify_error')
            self.assertEqual(len(snapshot().events), 32)

    def test_existing_live_dispatch_contracts_with_private_instrumentation_in_both_engines(self):
        original_read = Path.read_text
        private = instrument(CONTROLLER.read_bytes()).decode('utf-8')

        def read(path, *args, **kwargs):
            return private if path == CONTROLLER else original_read(path, *args, **kwargs)

        methods = unittest.defaultTestLoader.getTestCaseNames(live_dispatch.FoundCityLiveDispatchTests)
        for engine in (L51, L53):
            for method in methods:
                with self.subTest(engine=engine.__module__, method=method):
                    with patch.object(Path, 'read_text', read), patch.object(receipt, 'LuaRuntime', engine):
                        case = live_dispatch.FoundCityLiveDispatchTests(method)
                        result = unittest.TestResult()
                        case.run(result)
                    self.assertEqual(result.errors + result.failures, [])

    def test_outcomes_distinguish_native_false_error_bound_rejection_and_writer_throw(self):
        original_read = Path.read_text
        private = instrument(CONTROLLER.read_bytes()).decode('utf-8')

        def read(path, *args, **kwargs):
            return private if path == CONTROLLER else original_read(path, *args, **kwargs)

        for engine in (L51, L53):
            for scenario in ('false', 'error', 'binding', 'writer_throw'):
                with self.subTest(engine=engine.__module__, scenario=scenario):
                    with patch.object(Path, 'read_text', read), patch.object(receipt, 'LuaRuntime', engine):
                        case = live_dispatch.FoundCityLiveDispatchTests()
                        case.setUp()
                        case.arm_without_order()
                        c = case.h.controller
                        before = c.P6FoundDispatchSnapshot()
                        self.assertEqual(before.events[len(before.events)].reason, 'armed_final_native_unavailable')
                        if scenario == 'error':
                            # Throw through the existing qualifier's callback, preserving
                            # the native binding captured by the live grant.
                            run = c.RunNow
                            case.lua.execute('TestWorld.holdFound=false;TestWorld.reenter=true;BaiqiController.RunNow=function()error({})end')
                            run()
                            event = c.P6FoundDispatchSnapshot().events
                            self.assertEqual(event[len(event)].reason, 'qualify_error')
                            self.assertFalse(event[len(event)].qualifyOK)
                        elif scenario == 'binding':
                            case.lua.execute('UnitManager.RequestOperation=function()error("must not enter")end')
                            case.h.run_now()
                            event = c.P6FoundDispatchSnapshot().events
                            self.assertEqual(event[len(event)].kind, 'held')
                        elif scenario == 'writer_throw':
                            # A replacement writer is deliberately not a valid old grant.
                            # Set it before arming a new fixture instead.
                            case.setUp()
                            case.lua.execute('UnitManager.RequestOperation=function()error("unknown")end')
                            case.arm_without_order()
                            c = case.h.controller
                            case.resume(1)
                            event = c.P6FoundDispatchSnapshot().events
                            self.assertEqual(event[len(event)].kind, 'writer')
                            self.assertTrue(event[len(event)].entered)
                            self.assertFalse(event[len(event)].writerOK)
                        else:
                            case.h.run_now()
                            event = c.P6FoundDispatchSnapshot().events
                            self.assertEqual(event[len(event)].reason, 'armed_final_native_unavailable')
                            self.assertFalse(event[len(event)].entered)


if __name__ == '__main__':
    unittest.main()
