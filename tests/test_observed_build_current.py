"""Qualify current private instrumentation without installing or mutating the mod."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

from lupa.lua51 import LuaRuntime

from tools import build_observed_mod as builder
from tools.build_mod import digest, manifest_files, MOD_ID
from tests import test_baiqi_food_tile_rescue as rescue_fixture

ROOT = Path(__file__).resolve().parents[1]


class CurrentObservedBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        cls.source = ROOT / 'mod/Baiqi'
        cls.names = manifest_files(cls.source)
        cls.before = {n: digest(cls.source / n) for n in cls.names}
        cls.out = cls.base / 'bounded140'
        cls.result = builder.build(cls.out, bounded_zero=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_current_bounded_build_reports_real_version_and_frozen_schema(self):
        r = self.result
        self.assertEqual((r['source_version'], r['mode'], r['runtime_marker']),
                         (140, 'baiqi140-q21-bounded', 'baiqi67-q19'))
        self.assertEqual(r['lua_compile_versions'], ['5.1', '5.3'])
        self.assertTrue(r['aggregate_zero'])
        self.assertFalse(r['installed'])
        self.assertEqual(len(r['expected_entry_keys']), 33)
        self.assertEqual(sum(r['context_quotas'].values()), 4096)
        self.assertEqual(r['global_retained_sample_capacity'], 4096)

    def test_exact_inventory_source_hashes_and_archive_bytes_remain_qualified(self):
        self.assertEqual(self.result['source_hashes'], self.before)
        self.assertEqual({n: digest(self.source / n) for n in self.names}, self.before)
        self.assertEqual(manifest_files(self.out / 'Baiqi'), self.names)
        archive = self.out / 'Baiqi-diagnostic140-q21-bounded.zip'
        with zipfile.ZipFile(archive) as z:
            self.assertEqual(set(z.namelist()), {'Baiqi/' + n for n in self.names})
            for n in self.names:
                self.assertEqual(z.read('Baiqi/' + n), (self.out / 'Baiqi' / n).read_bytes())
        self.assertEqual(ET.fromstring((self.out / 'Baiqi/Baiqi.modinfo').read_bytes()).get('version'), '140')

    def test_coverage_and_wrapped_canonical_capture_are_real_source_sites(self):
        r = self.result
        lua_names = {n for n in self.names if n.endswith('.lua')}
        self.assertEqual(set(r['coverage']), lua_names)
        self.assertEqual(set(r['changed_files']), lua_names)
        file = 'Lua/BaiqiFoodTileIntentGameplay.lua'
        names = {row['name'] for row in r['coverage'][file]['functions']}
        self.assertTrue({'InspectBatch', 'Observe', 'Persist', 'bridge.Inspect', 'bridge.InspectBatch'} <= names)
        text = (self.out / 'Baiqi' / file).read_text(encoding='utf-8')
        self.assertLess(text.index('bridge.Inspect=P6OwnWrap('), text.index('local canonicalInspect=bridge.Inspect'))
        self.assertTrue(r['coverage'][file]['top_level_chunk_wrapped'])

    def test_current_source_cannot_build_unbounded_or_overwrite_output(self):
        unbounded = self.base / 'unbounded'
        with self.assertRaisesRegex(ValueError, 'bounded_zero'):
            builder.build(unbounded)
        self.assertFalse(unbounded.exists())
        marker = self.out / 'owner.txt'
        marker.write_text('keep', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'new directory'):
            builder.build(self.out, bounded_zero=True)
        self.assertEqual(marker.read_text(encoding='utf-8'), 'keep')

    def test_unsupported_source_is_rejected_before_output(self):
        base = self.base / 'unsupported-fixture'
        source = base / 'mod/Baiqi'
        source.mkdir(parents=True)
        (source / 'empty.lua').write_text('return {}', encoding='utf-8')
        (source / 'Baiqi.modinfo').write_text(
            f'<Mod id="{MOD_ID}" version="999"><Files><File>empty.lua</File></Files></Mod>',
            encoding='utf-8')
        output = self.base / 'unsupported-output'
        with patch.object(builder, 'ROOT', base), self.assertRaisesRegex(ValueError, 'actual source67,139 or140'):
            builder.build(output, bounded_zero=True)
        self.assertFalse(output.exists())

    def test_actual_transformed_core_preserves_fast_path_and_deduplicates_roots(self):
        lua = rescue_fixture.FoodTileRescueTests().world()
        profile = lua.execute((ROOT / 'tools/lua/diagnostic_profile.lua').read_text(encoding='utf-8'))
        roots = lua.execute((ROOT / 'tools/lua/diagnostic_owned_roots.lua').read_text(encoding='utf-8'))
        lua.globals().NewTestProfile, lua.globals().NewTestRoots = profile, roots
        lua.execute('''
          local time=0
          P6TestRoots=NewTestRoots(NewTestProfile,function()time=time+1;return time/1000 end,4096)
          P6OwnDiag={marker='baiqi67-q19',Wrap=function(_,label,fn)return P6TestRoots:Wrap(label,fn)end,
            Leaves={Static=function(_,label,fn)return fn end,
              Method=function(_,label,native,name)return function(...)return native[name](native,...)end end}}
        ''')
        file = 'Lua/BaiqiFoodTileIntentGameplay.lua'
        lua.execute((self.out / 'Baiqi' / file).read_text(encoding='utf-8'))
        lua.execute('''
          P6TestRoots:SetEnabled(true)
          local b=ExposedMembers.BaiqiFoodTileRescueBridge;local get=Players[0].GetProperty;local reads=0
          Players[0].GetProperty=function(self,key)reads=reads+1;return get(self,key)end
          local status,rows=b.InspectBatch(0,{{cityID=458758},{cityID=65536}})
          assert(status=='READY' and rows['458758'].stage=='OPEN' and reads==2)
          assert(P6TestRoots.profile.totalCalls==1 and #P6TestRoots.profile.samples==1)
          local calls=0;b.Inspect=function(pid,id,token)calls=calls+1;return 'UNKNOWN',token,'override'end
          status,rows=b.InspectBatch(0,{{cityID=458758},{cityID=65536}})
          assert(status=='READY' and calls==2 and rows['458758'].stage=='UNKNOWN' and reads==2)
          assert(P6TestRoots.profile.totalCalls==2 and #P6TestRoots.profile.samples==2)
          assert(P6TestRoots.profile.dropped==0 and P6TestRoots.profile.invalidClock==0)
          assert(#W.requests==0 and (W.propertyWrites or 0)==0)
        ''')


if __name__ == '__main__':
    unittest.main()
