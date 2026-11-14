"""Wholly synthetic snapshots; software checks grant no Native pressure evidence."""
import copy
import json
from pathlib import Path
import unittest
from tools.qualify_pressure_geometry import qualify_pressure_geometry

LAYOUT = json.loads((Path(__file__).resolve().parents[1] / 'tools/fixtures/pressure_layout_v1.json').read_text(encoding='utf-8'))


def snapshot(variant='NO_SITE'):
    cities = [dict(owner=p['owner'], id=i, x=p['x'], y=p['y']) for i, p in enumerate(LAYOUT['slots'])]
    slots = {(p['x'], p['y']): p['owner'] for p in cities}
    plots = []
    for i in range(1144):
        position = (i % 44, i // 44);city = position in slots
        plots.append(dict(index=i, x=position[0], y=position[1], water=not city and variant=='NO_SITE',
                          city=city, visible=True, owner=slots.get(position)))
    return dict(source='baiqi-pressure-geometry-v1', fixture_id=LAYOUT['fixture_id'], variant=variant,
                setup_stage='READY', turn=0, width=44, height=26, cities=cities, plots=plots)


def change(data, path, value):
    for key in path[:-1]:data = data[key]
    data[path[-1]] = value


class QualifyPressureGeometryTests(unittest.TestCase):
    def test_variants_and_exact_output(self):
        for variant, status, water, bare, absent in [('NO_SITE','QUALIFIED_NO_ADMISSIBLE_GEOMETRY',1133,0,True),
                                                   ('MANY','READY_MANY_GEOMETRY_ONLY',0,1133,None)]:
            data = snapshot(variant)
            self.assertEqual(qualify_pressure_geometry(data, LAYOUT), dict(status=status, variant=variant,
                             turn=0, inspected_plots=1144, water_tiles=water, city_tiles=11,
                             bare_land_tiles=bare, global_no_admissible_geometry=absent,
                             many_candidate_pressure=None))

    def test_valid_terrain_mismatch_has_no_qualification(self):
        for variant in ('NO_SITE', 'MANY'):
            data = snapshot(variant);data['plots'][0]['water'] = variant=='MANY'
            result = qualify_pressure_geometry(data, LAYOUT)
            self.assertEqual(result['status'], 'NOT_QUALIFIED')
            self.assertIsNone(result['global_no_admissible_geometry'])
            self.assertIsNone(result['many_candidate_pressure'])

    def test_per_owner_ids_and_input_immutability(self):
        data = snapshot();data['cities'][-1]['id'] = 0
        data['plots'].reverse();data['cities'].reverse()
        original, layout_original = copy.deepcopy(data), copy.deepcopy(LAYOUT)
        self.assertEqual(qualify_pressure_geometry(data, LAYOUT)['city_tiles'], 11)
        self.assertEqual(data, original);self.assertEqual(LAYOUT, layout_original)

    def test_root_schema_and_types(self):
        for key, value in [('source','other'), ('fixture_id','other'), ('variant',[]), ('setup_stage','PREP'),
                           ('turn',True), ('turn',-1), ('turn',2147483648), ('width',44.0), ('height',True),
                           ('cities',{}), ('plots',[]), ('extra',1)]:
            data = snapshot();data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):qualify_pressure_geometry(data, LAYOUT)
        data = snapshot();del data['turn']
        with self.assertRaises(ValueError):qualify_pressure_geometry(data, LAYOUT)

    def test_layout_validation(self):
        for path, value in [(('extra',),1), (('width',),44.0), (('fixture_id',),'other'), (('wrap_x',),0),
                            (('slots',0,'owner'),False), (('slots',0,'x'),4.0), (('slots',0,'start'),1),
                            (('slots',0,'extra'),0), (('slots',0,'start'),False), (('slots',1),LAYOUT['slots'][0])]:
            layout = copy.deepcopy(LAYOUT);change(layout, path, value)
            with self.subTest(path=path), self.assertRaises(ValueError):qualify_pressure_geometry(snapshot(), layout)

    def test_city_schema_owner_ids_and_footprint(self):
        for path, value in [(('cities',0,'owner'),False), (('cities',0,'id'),True), (('cities',0,'id'),-1),
                            (('cities',1,'id'),0), (('cities',0,'x'),4.0), (('cities',0,'x'),5),
                            (('cities',0,'extra'),0), (('cities',0,'owner'),1),
                            (('cities',1),snapshot()['cities'][0])]:
            data = snapshot();change(data, path, value)
            with self.subTest(path=path), self.assertRaises(ValueError):qualify_pressure_geometry(data, LAYOUT)

    def test_plot_coverage_flags_and_city_owner(self):
        for index, key, value in [(0,'index',True), (0,'index',1), (0,'x',False), (0,'y',1),
                                  (0,'water',1), (0,'visible',None), (0,'visible',False), (0,'city',True),
                                  (0,'owner',0), (0,'extra',0), (180,'city',False), (180,'water',True),
                                  (180,'owner',1), (180,'owner',False), (180,'owner',None)]:
            data = snapshot();data['plots'][index][key] = value
            with self.subTest(index=index,key=key), self.assertRaises(ValueError):qualify_pressure_geometry(data, LAYOUT)
        data = snapshot();data['plots'].pop()
        with self.assertRaises(ValueError):qualify_pressure_geometry(data, LAYOUT)
