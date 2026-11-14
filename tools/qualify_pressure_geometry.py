"""Validate a complete, visible private fixture snapshot; no Native or file access.

No-site proof covers the Controller's necessary not-water/not-city geometry gates.
The MANY variant cannot certify the size of a real recommendation pool.
"""
from __future__ import annotations

WIDTH, HEIGHT = 44, 26
FIXTURE_ID = 'P6_PRESSURE_LAYOUT_V1'


def _object(value, keys):
    if type(value) is not dict or set(value) != set(keys.split()):
        raise ValueError('Unexpected object fields')


def _integer(value, maximum):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError('Invalid integer')
    return value


def _position(row):
    return _integer(row['x'], WIDTH - 1), _integer(row['y'], HEIGHT - 1)


def _layout(layout):
    _object(layout, 'schema fixture_id width height wrap_x slots')
    if (layout['schema'] != 'civ6.pressure-layout/v1' or layout['fixture_id'] != FIXTURE_ID
            or type(layout['width']) is not int or layout['width'] != WIDTH
            or type(layout['height']) is not int or layout['height'] != HEIGHT
            or layout['wrap_x'] is not False):
        raise ValueError('Unexpected layout')
    slots = layout['slots']
    if type(slots) is not list or len(slots) != 11:
        raise ValueError('Expected eleven slots')
    positions, counts, starts = {}, [0, 0], [0, 0]
    for slot in slots:
        _object(slot, 'owner x y start')
        owner, position = _integer(slot['owner'], 1), _position(slot)
        if type(slot['start']) is not bool or position in positions:
            raise ValueError('Invalid/duplicate slot')
        positions[position] = owner
        counts[owner] += 1
        starts[owner] += int(slot['start'])
    if counts != [10, 1] or starts != [1, 1]:
        raise ValueError('Invalid city/start counts')
    return positions


def qualify_pressure_geometry(data, layout):
    expected = _layout(layout)
    _object(data, 'source fixture_id variant setup_stage turn width height cities plots')
    if (data['source'] != 'baiqi-pressure-geometry-v1' or data['fixture_id'] != FIXTURE_ID
            or data['variant'] not in ('NO_SITE', 'MANY', 'MANY_WATER1') or data['setup_stage'] != 'READY'
            or type(data['width']) is not int or data['width'] != WIDTH
            or type(data['height']) is not int or data['height'] != HEIGHT):
        raise ValueError('Unexpected snapshot')
    if data['variant'] == 'MANY_WATER1' and (0, 0) in expected:
        raise ValueError('Water anchor cannot be a city slot')
    turn = _integer(data['turn'], 2147483647)
    cities = data['cities']
    if type(cities) is not list or len(cities) != 11:
        raise ValueError('Expected eleven cities')
    positions, identities = {}, set()
    for city in cities:
        _object(city, 'owner id x y')
        owner, cid = _integer(city['owner'], 1), _integer(city['id'], 2147483647)
        position = _position(city)
        if position in positions or (owner, cid) in identities or expected.get(position) != owner:
            raise ValueError('Invalid city identity/location/owner')
        positions[position] = owner
        identities.add((owner, cid))
    if positions != expected:
        raise ValueError('Missing city')
    plots = data['plots']
    if type(plots) is not list or len(plots) != WIDTH * HEIGHT:
        raise ValueError('Incomplete plot coverage')
    seen, water_tiles, city_tiles, bare_land_tiles = set(), 0, 0, 0
    water_at_zero = False
    for plot in plots:
        _object(plot, 'index x y water city visible owner')
        index, position = _integer(plot['index'], WIDTH * HEIGHT - 1), _position(plot)
        if index in seen or position != (index % WIDTH, index // WIDTH):
            raise ValueError('Duplicate/incoherent plot')
        seen.add(index)
        if any(type(plot[key]) is not bool for key in ('water', 'city', 'visible')):
            raise ValueError('Unknown plot flags')
        if plot['visible'] is not True or plot['city'] != (position in positions):
            raise ValueError('Invisible plot or inconsistent city footprint')
        if plot['city']:
            if plot['water'] or _integer(plot['owner'], 1) != positions[position]:
                raise ValueError('Invalid city plot')
            city_tiles += 1
        else:
            if plot['owner'] is not None:
                raise ValueError('Noncity plot owner must be omitted as null')
            if plot['water']:
                water_tiles += 1
                if index == 0:
                    water_at_zero = True
            else:
                bare_land_tiles += 1
    variant, status, no_geometry = data['variant'], 'NOT_QUALIFIED', None
    if variant == 'NO_SITE' and bare_land_tiles == 0:
        status, no_geometry = 'QUALIFIED_NO_ADMISSIBLE_GEOMETRY', True
    elif variant == 'MANY' and water_tiles == 0:
        status = 'READY_MANY_GEOMETRY_ONLY'
    elif variant == 'MANY_WATER1' and water_tiles == 1 and water_at_zero:
        status = 'READY_MANY_GEOMETRY_ONLY'
    return {'status': status, 'variant': variant, 'turn': turn, 'inspected_plots': len(seen),
            'water_tiles': water_tiles, 'city_tiles': city_tiles, 'bare_land_tiles': bare_land_tiles,
            'global_no_admissible_geometry': no_geometry, 'many_candidate_pressure': None}
