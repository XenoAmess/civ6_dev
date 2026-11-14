"""Independent water-anchor fixture: software only, no Native pool claims."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from tools import build_pressure_map_mod as builder
from tools.qualify_pressure_geometry import qualify_pressure_geometry
from tests import test_pressure_fixture_geometry as geometry_tests
from tests.test_qualify_pressure_geometry import snapshot
from tests import test_pressure_fixture_snapshot as snapshot_tests
from tests import test_build_pressure_map_mod as builder_tests

LAYOUT=geometry_tests.LAYOUT
SNAP_PORTS=snapshot_tests.PORTS


def water_snapshot():
    data=snapshot('MANY');data['variant']='MANY_WATER1';data['plots'][0]['water']=True
    return data


class PressureManyWater1Tests(unittest.TestCase):
    def test_geometry_exact_anchor_and_flat_city_slots_dual_lua(self):
        slots={s['x']+44*s['y'] for s in LAYOUT['slots']}
        for version in ('lua51','lua53'):
            lua,generate,env=geometry_tests.PressureFixtureGeometryTests().ports(version)
            result=generate(env,lua.table_from(LAYOUT,recursive=True),'MANY_WATER1')
            self.assertEqual((result.land_tiles,result.city_setup_complete,len(env.log)),(1143,False,1149))
            for i in range(1144):
                self.assertEqual(env.log[i+1][3],1 if i==0 else 0 if i in slots else 2)
            self.assertEqual([row[1] for row in list(env.log.values())[-5:]],['area','chokes','continents','start','start'])

    def test_qualifier_uses_physical_index_and_does_not_mutate(self):
        data=water_snapshot();data['plots'].reverse();before=copy.deepcopy(data)
        result=qualify_pressure_geometry(data,LAYOUT)
        self.assertEqual((result['status'],result['water_tiles'],result['bare_land_tiles']),('READY_MANY_GEOMETRY_ONLY',1,1132))
        self.assertIsNone(result['many_candidate_pressure']);self.assertIsNone(result['global_no_admissible_geometry'])
        self.assertEqual(data,before)
        for wet in ([],[1],[0,1]):
            data=snapshot('MANY');data['variant']='MANY_WATER1'
            for i in wet:data['plots'][i]['water']=True
            if wet==[1]:data['plots'][0],data['plots'][1]=data['plots'][1],data['plots'][0]
            self.assertEqual(qualify_pressure_geometry(data,LAYOUT)['status'],'NOT_QUALIFIED')
        data=water_snapshot();data['variant']='MANY'
        self.assertEqual(qualify_pressure_geometry(data,LAYOUT)['status'],'NOT_QUALIFIED')

    def test_anchor_city_slot_rejected_before_any_write(self):
        layout=copy.deepcopy(LAYOUT);layout['slots'][0].update(x=0,y=0)
        lua,generate,env=geometry_tests.PressureFixtureGeometryTests().ports()
        with self.assertRaisesRegex(Exception,'Water anchor'):generate(env,lua.table_from(layout,recursive=True),'MANY_WATER1')
        self.assertEqual((env.reads,len(env.log)),(0,0))
        with self.assertRaisesRegex(ValueError,'Water anchor'):qualify_pressure_geometry(water_snapshot(),layout)

    def test_actual_snapshot_module_and_strict_consumer_dual_lua(self):
        helper=snapshot_tests.PressureFixtureSnapshotTests()
        for version in ('lua51','lua53'):
            lua,collect,_,layout=helper.ports(version)
            ports=SNAP_PORTS.replace("E.variant~='MANY' and E.bareAt~=i and slots[i]==nil",
                                     "(E.variant=='MANY_WATER1' and i==0) or (E.variant=='NO_SITE' and slots[i]==nil)")
            self.assertNotEqual(ports,SNAP_PORTS)
            env=lua.eval(ports)(layout);env.variant='MANY_WATER1'
            env.MapConfiguration.GetValue=lua.eval("function()return '{e8b15363-c9b9-4dcb-b575-117d9308d426}Maps/P6PressureManyWater1.lua'end")
            result=qualify_pressure_geometry(helper.python_snapshot(collect(env,layout)),LAYOUT)
            self.assertEqual(result['status'],'READY_MANY_GEOMETRY_ONLY')
            self.assertIsNone(result['many_candidate_pressure'])
            env.invisibleAt=1143
            with self.assertRaisesRegex(Exception,'Entire map'):collect(env,layout)

    def test_builder_five_files_actual_xml_hashes_and_entry(self):
        original=dict(builder.MAPS)
        with tempfile.TemporaryDirectory() as temp:
            for trace in (False,True):
                out=Path(temp)/str(trace);result=builder.build(out,trace_generation=trace,many_water_anchor=True)
                package=out/'PressureMaps'
                self.assertEqual((result['mode'],result['files']),('baiqi-pressure-map-water1-v1',5))
                self.assertEqual(result['map_scripts']['MANY_WATER1'],'{'+builder.UUID+'}'+builder.MANY_WATER1_PATH)
                self.assertEqual(result.get('generation_trace',False),trace)
                for path,digest in result['package_file_sha256'].items():
                    self.assertEqual(hashlib.sha256((package/path).read_bytes()).hexdigest(),digest)
                root=ET.parse(package/'PressureMaps.modinfo').getroot()
                payload={p.text for p in root.findall('Files/File')}
                self.assertEqual(payload,{'Config/PressureMaps.xml',*builder.MAPS.values(),builder.MANY_WATER1_PATH})
                self.assertEqual({p.findtext('File') for p in root.findall('FrontEndActions/AddMap')},payload-{'Config/PressureMaps.xml'})
                self.assertIsNone(root.find('InGameActions'))
                config=ET.parse(package/'Config/PressureMaps.xml').getroot()
                self.assertEqual({p.get('Domain') for p in config.findall('MapSizes/Row')},set(result['map_scripts'].values()))
                for version in ('lua51','lua53'):
                    lua,env=builder_tests.BuildPressureMapTests().runtime((package/builder.MANY_WATER1_PATH).read_text(encoding='utf-8'),version)
                    self.assertEqual(len(env.log),0)
                    generated=lua.globals().GenerateMap()
                    self.assertEqual((generated.variant,generated.land_tiles,len(env.log)),('MANY_WATER1',1143,1149))
        self.assertEqual(builder.MAPS,original)

    def test_bad_flags_or_invisible_snapshot_never_qualify(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'bad'
            with self.assertRaises(ValueError):builder.build(target,many_water_anchor=1)
            self.assertFalse(target.exists())
            result=builder.build(Path(temp)/'default')
            self.assertEqual(result['files'],4);self.assertNotIn('MANY_WATER1',result['map_scripts'])
        data=water_snapshot();data['plots'][0]['visible']=False
        with self.assertRaises(ValueError):qualify_pressure_geometry(data,LAYOUT)
