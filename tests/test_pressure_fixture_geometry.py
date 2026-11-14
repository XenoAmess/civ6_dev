"""Synthetic generation ports only; no installed game or Native mutations."""
import copy
import importlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = json.loads((ROOT / 'tools/fixtures/pressure_layout_v1.json').read_text(encoding='utf-8'))
SOURCE = (ROOT / 'tools/lua/pressure_fixture_geometry.lua').read_text(encoding='utf-8')
PORTS = '''function()
 local E={in_generation=true,grass=0,ocean=1,hills=2,log={},reads=0}
 local function log(row) E.log[#E.log+1]=row end
 E.Map={GetGridSize=function()return 44,26 end,GetPlotByIndex=function(i)
  E.reads=E.reads+1;if i==E.missingAt then return nil end
  return {GetIndex=function()return i==E.badAt and -1 or i end,
   GetX=function()return i%44 end,GetY=function()return math.floor(i/44) end}
 end}
 E.TerrainBuilder={SetTerrainType=function(p,t)
  assert(E.reads==1144,'Write before complete preflight');local i=p:GetIndex()
  log({'terrain',i,t});if i==E.failAt then error('fixture setter failure') end
 end,AnalyzeChokepoints=function()log({'chokes'})end,StampContinents=function()log({'continents'})end}
 E.AreaBuilder={Recalculate=function()log({'area'})end};E.Players={}
 for owner=0,1 do local id=owner;E.Players[id]={SetStartingPlot=function(self,p)
  assert(self==E.Players[id]);log({'start',id,p:GetIndex()}) end} end
 return E
end'''


class PressureFixtureGeometryTests(unittest.TestCase):
    def ports(self, version='lua51'):
        runtime = importlib.import_module('lupa.' + version).LuaRuntime(unpack_returned_tuples=True)
        return runtime, runtime.execute(SOURCE), runtime.eval(PORTS)()

    def test_variants_and_order_on_both_lua_versions(self):
        slots = {p['x'] + 44 * p['y'] for p in LAYOUT['slots']}
        for version in ('lua51', 'lua53'):
            for variant in ('NO_SITE', 'MANY'):
                lua, generate, env = self.ports(version)
                layout = lua.table_from(LAYOUT, recursive=True)
                result = generate(env, layout, variant)
                self.assertEqual(dict(result), dict(status='MAP_GEOMETRY_READY', variant=variant,
                                 width=44, height=26, land_tiles=11 if variant=='NO_SITE' else 1144,
                                 city_setup_complete=False))
                self.assertEqual(len(env.log), 1149)
                for index in range(1144):
                    self.assertEqual(list(env.log[index+1].values()),
                                     ['terrain', index, 0 if index in slots else 1 if variant=='NO_SITE' else 2])
                self.assertEqual([env.log[i][1] for i in range(1145, 1150)],
                                 ['area', 'chokes', 'continents', 'start', 'start'])
                self.assertEqual([list(env.log[i].values()) for i in (1148, 1149)],
                                 [['start', 0, 180], ['start', 1, 1076]])
                self.assertEqual([dict(layout.slots[i]) for i in range(1, 12)], LAYOUT['slots'])
                self.assertEqual({k:v for k,v in layout.items() if k!='slots'},
                                 {k:v for k,v in LAYOUT.items() if k!='slots'})

    def test_invalid_ports_and_enums_precede_any_write(self):
        changes = ['e.in_generation=false', 'e.grass=0/0', 'e.grass=math.huge', 'e.grass=0.5',
                   'e.grass=-1', 'e.grass=e.ocean', 'e.Map=nil', 'e.TerrainBuilder.StampContinents=nil',
                   'e.TerrainBuilder.SetTerrainType=nil', 'e.AreaBuilder.Recalculate=nil',
                   'e.Players[1].SetStartingPlot=nil', 'e.Map.GetGridSize=function()return 45,26 end']
        for change in changes:
            lua, generate, env = self.ports()
            lua.eval('function(e) ' + change + ' end')(env)
            with self.subTest(change=change), self.assertRaises(Exception):
                generate(env, lua.table_from(LAYOUT, recursive=True), 'NO_SITE')
            self.assertEqual(len(env.log), 0)

    def test_invalid_layout_before_any_write(self):
        cases = []
        for key, value in [('extra', 1), ('fixture_id', 'other'), ('width', 45), ('wrap_x', True)]:
            bad = copy.deepcopy(LAYOUT);bad[key] = value;cases.append(bad)
        for key, value in [('x', 4.5), ('x', float('nan')), ('x', 44), ('owner', False), ('start', 1), ('extra', 0)]:
            bad = copy.deepcopy(LAYOUT);bad['slots'][0][key] = value;cases.append(bad)
        bad = copy.deepcopy(LAYOUT);bad['slots'][1] = bad['slots'][0].copy();cases.append(bad)
        bad = copy.deepcopy(LAYOUT);bad['slots'][0]['start'] = False;cases.append(bad)
        for bad in cases:
            lua, generate, env = self.ports()
            with self.assertRaises(Exception):generate(env, lua.table_from(bad, recursive=True), 'NO_SITE')
            self.assertEqual(len(env.log), 0)

    def test_last_plot_preflight_and_invalid_variant(self):
        for alteration in ('e.missingAt=1143', 'e.badAt=1143'):
            lua, generate, env = self.ports();lua.eval('function(e) '+alteration+' end')(env)
            with self.assertRaises(Exception):generate(env, lua.table_from(LAYOUT, recursive=True), 'NO_SITE')
            self.assertEqual(len(env.log), 0)
        lua, generate, env = self.ports()
        with self.assertRaises(Exception):generate(env, lua.table_from(LAYOUT, recursive=True), 'other')
        self.assertEqual(len(env.log), 0)

    def test_setter_exception_stops_without_retry(self):
        lua, generate, env = self.ports();env.failAt = 17
        with self.assertRaisesRegex(Exception, 'fixture setter failure'):
            generate(env, lua.table_from(LAYOUT, recursive=True), 'NO_SITE')
        self.assertEqual(len(env.log), 18)
        self.assertTrue(all(row[1]=='terrain' for row in env.log.values()))
