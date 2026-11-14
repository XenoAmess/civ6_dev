"""Private addon assembly and fake engine callback ABI; never installs a mod."""
import hashlib
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from tools import build_pressure_map_mod as builder
from tests.test_pressure_fixture_geometry import PORTS


class BuildPressureMapTests(unittest.TestCase):
    def runtime(self, script, version='lua51', fail=None):
        lua = importlib.import_module('lupa.' + version).LuaRuntime(unpack_returned_tuples=True)
        env = lua.eval(PORTS)();env.failAt = fail
        for name in ('Map', 'TerrainBuilder', 'AreaBuilder', 'Players'):lua.globals()[name] = env[name]
        lua.execute('''function include(name)
          assert(name=='MapEnums');g_TERRAIN_TYPE_GRASS=0;g_TERRAIN_TYPE_OCEAN=1;g_TERRAIN_TYPE_GRASS_HILLS=2
        end
        function print(...) end''')
        lua.execute(script)
        return lua, env

    def test_manifest_configuration_references_and_byte_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'out';result = builder.build(out);package = out/'PressureMaps'
            files = {p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()}
            self.assertEqual(files, {'PressureMaps.modinfo', 'Config/PressureMaps.xml', *builder.MAPS.values()})
            self.assertEqual(result, json.loads((out/'pressure-map-build.json').read_text(encoding='utf-8')))
            for path in files:
                self.assertEqual(result['package_file_sha256'][path], hashlib.sha256((package/path).read_bytes()).hexdigest())
            for key, path in [('layout_sha256','tools/fixtures/pressure_layout_v1.json'),
                              ('geometry_sha256','tools/lua/pressure_fixture_geometry.lua')]:
                self.assertEqual(result[key], hashlib.sha256((builder.ROOT/path).read_bytes()).hexdigest())
            self.assertEqual((result['installed'], result['native_generated'], result['files']), (False,False,4))
            root = ET.parse(package/'PressureMaps.modinfo').getroot()
            self.assertEqual(root.attrib, {'id':builder.UUID, 'version':'1'})
            self.assertIsNone(root.find('InGameActions'))
            self.assertEqual(root.findtext('Properties/EnabledByDefault'), '0')
            self.assertEqual({p.text for p in root.findall('Files/File')}, files-{'PressureMaps.modinfo'})
            self.assertEqual(root.findtext('FrontEndActions/UpdateDatabase/File'), 'Config/PressureMaps.xml')
            maps = root.findall('FrontEndActions/AddMap')
            self.assertEqual({p.findtext('File') for p in maps}, set(builder.MAPS.values()))
            self.assertTrue(all(p.findtext('Properties/Group')=='StandardMaps' for p in maps))
            config = ET.parse(package/'Config/PressureMaps.xml').getroot()
            self.assertEqual({p.tag for p in config}, {'MapDomainOverrides','MapSizes'})
            keys = set(result['map_scripts'].values())
            self.assertEqual({p.get('Map') for p in config.findall('MapDomainOverrides/Row')}, keys)
            self.assertEqual({p.get('Domain') for p in config.findall('MapSizes/Row')}, keys)
            for row in config.findall('MapSizes/Row'):
                self.assertEqual([row.get(k) for k in ('MinPlayers','MaxPlayers','DefaultPlayers')], ['2']*3)
                self.assertEqual([row.get(k) for k in ('MinCityStates','MaxCityStates','DefaultCityStates')], ['0']*3)

    def test_engine_zero_argument_callbacks_on_both_versions(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'out';builder.build(out)
            for version in ('lua51','lua53'):
                for variant, path in builder.MAPS.items():
                    lua, env = self.runtime((out/'PressureMaps'/path).read_text(encoding='utf-8'), version)
                    self.assertEqual((len(env.log),env.reads), (0,0))
                    self.assertEqual(dict(lua.globals().GetMapInitData('MAPSIZE_TINY')), dict(Width=44,Height=26,WrapX=False))
                    self.assertEqual((len(env.log),env.reads), (0,0))
                    result = lua.globals().GenerateMap()
                    self.assertEqual((result.variant,result.land_tiles,result.city_setup_complete),
                                     (variant,11 if variant=='NO_SITE' else 1144,False))
                    self.assertEqual(len(env.log),1149)
                    self.assertEqual([list(env.log[i].values()) for i in (1148,1149)],
                                     [['start',0,180],['start',1,1076]])

    def test_success_or_failure_cannot_replay_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'out';builder.build(out)
            script=(out/'PressureMaps'/builder.MAPS['NO_SITE']).read_text(encoding='utf-8')
            for fail in (None,17):
                lua, env=self.runtime(script,fail=fail)
                if fail is None:lua.globals().GenerateMap()
                else:
                    with self.assertRaisesRegex(Exception,'fixture setter failure'):lua.globals().GenerateMap()
                count=len(env.log)
                with self.assertRaisesRegex(Exception,'already attempted'):lua.globals().GenerateMap()
                self.assertEqual(len(env.log),count)
                self.assertEqual(count,1149 if fail is None else 18)

    def test_existing_output_and_release_paths_are_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'out';target.mkdir();(target/'keep').write_bytes(b'keep')
            with self.assertRaises(ValueError):builder.build(target)
            self.assertEqual(list(target.iterdir()), [target/'keep'])
            self.assertEqual((target/'keep').read_bytes(), b'keep')
        with self.assertRaises(ValueError):builder.build(builder.ROOT/'mod/pressure-unwanted-test-output')
        self.assertFalse((builder.ROOT/'mod/pressure-unwanted-test-output').exists())

    def test_invalid_inputs_fail_before_any_output(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);(base/'tools/fixtures').mkdir(parents=True);(base/'tools/lua').mkdir()
            layout=(builder.ROOT/'tools/fixtures/pressure_layout_v1.json').read_bytes()
            core=(builder.ROOT/'tools/lua/pressure_fixture_geometry.lua').read_bytes()
            for bad in ('layout','core'):
                data=json.loads(layout);data['width']=45
                (base/'tools/fixtures/pressure_layout_v1.json').write_bytes(json.dumps(data).encode() if bad=='layout' else layout)
                (base/'tools/lua/pressure_fixture_geometry.lua').write_bytes(b'not valid lua' if bad=='core' else core)
                with patch.object(builder,'ROOT',base), self.assertRaises(Exception):builder.build(base/'out')
                self.assertFalse((base/'out').exists())
