"""Real private packages, no installation or Native execution."""
from pathlib import Path
import importlib,json,tempfile,unittest,zipfile
from unittest.mock import patch
from tools import build_observed_mod as builder
from tools.build_mod import MOD_ID,digest


class PressureObservedBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.legacy=builder.build(cls.root/'legacy',bounded_zero=True)
        cls.pressure=builder.build(cls.root/'pressure',bounded_zero=True,pressure_initial_turn=6)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_metadata_actual_calendar_and_only_executor_payload_differs(self):
        a,b=self.legacy,self.pressure
        self.assertEqual((b['source'],b['source_version'],b['initial_turn']),('baiqi142-pressure-observed-v1',142,6))
        self.assertEqual(b['window_turns'],[7,8,9,10,11]);self.assertEqual(b['closing_turn'],12)
        self.assertEqual([k for k in a['instrumented_hashes']if a['instrumented_hashes'][k]!=b['instrumented_hashes'][k]],['UI/BaiqiExecutor.lua'])
        for key in('source_hashes','coverage','expected_entry_keys','context_quotas','helper_hashes','files','lua_compile_versions'):
            self.assertEqual(a[key],b[key])
        self.assertEqual(len(b['expected_entry_keys']),33);self.assertEqual(sum(b['context_quotas'].values()),4096)
        self.assertEqual(b['global_retained_sample_capacity'],4096);self.assertEqual(b['files'],119)
        for key in('source','initial_turn','window_turns','closing_turn','pressure_initial_turn','pressure_window_turns','pressure_closing_turn'):
            self.assertNotIn(key,a)

    def test_actual_header_dual_lua_collision_does_not_overwrite(self):
        original=(self.root/'legacy/Baiqi/UI/BaiqiExecutor.lua').read_text(encoding='utf-8')
        actual=(self.root/'pressure/Baiqi/UI/BaiqiExecutor.lua').read_text(encoding='utf-8')
        self.assertTrue(actual.endswith(original));header=actual[:-len(original)]
        for version in('lua51','lua53'):
            module=importlib.import_module('lupa.'+version);lua=module.LuaRuntime()
            lua.execute("Game={GetCurrentGameTurn=function()error('No Native reads in header')end}")
            lua.execute(header)
            self.assertEqual(lua.eval('P6Q20PressureBuild.initial_turn'),6)
            self.assertEqual(lua.eval('P6Q20PressureBuild.source_version'),142)
            lua.execute('Foreign=P6Q20PressureBuild')
            with self.assertRaises(module.LuaError):lua.execute(header)
            self.assertTrue(lua.eval('P6Q20PressureBuild==Foreign'))

    def test_archive_source_hashes_and_saved_metadata(self):
        archive=self.root/'pressure/Baiqi-diagnostic142-q21-bounded-pressure-6.zip'
        self.assertTrue(archive.is_file());self.assertFalse(self.pressure['installed'])
        with zipfile.ZipFile(archive)as z:
            self.assertEqual(set(z.namelist()),{'Baiqi/'+n for n in self.pressure['source_hashes']})
            for n in self.pressure['source_hashes']:self.assertEqual(z.read('Baiqi/'+n),(self.root/'pressure/Baiqi'/n).read_bytes())
        self.assertEqual(json.loads((self.root/'pressure/diagnostic-build.json').read_text(encoding='utf-8')),self.pressure)
        for n,h in self.pressure['source_hashes'].items():self.assertEqual(digest(builder.ROOT/'mod/Baiqi'/n),h)

    def test_strict_input_rejected_before_output_and_boundaries_accepted(self):
        class IntSubclass(int):pass
        for value,bounded in((True,True),(6.0,True),(-1,True),(2147483642,True),(IntSubclass(6),True),(6,1),(6,False)):
            out=self.root/('invalid-'+str(len(list(self.root.iterdir()))))
            with self.assertRaises(ValueError):builder.build(out,bounded_zero=bounded,pressure_initial_turn=value)
            self.assertFalse(out.exists())
        for value in(0,2147483641):
            with self.assertRaisesRegex(ValueError,'new directory'):builder.build(self.root/'pressure',bounded_zero=True,pressure_initial_turn=value)

    def test_other_actual_source_rejected_before_helpers_or_output(self):
        root=self.root/'source139';source=root/'mod/Baiqi';source.mkdir(parents=True)
        (source/'empty.lua').write_text('return {}',encoding='utf-8')
        (source/'Baiqi.modinfo').write_text(f'<Mod id="{MOD_ID}" version="139"><Files><File>empty.lua</File></Files></Mod>',encoding='utf-8')
        out=root/'out'
        with patch.object(builder,'ROOT',root),self.assertRaises(ValueError):builder.build(out,bounded_zero=True,pressure_initial_turn=6)
        self.assertFalse(out.exists())
