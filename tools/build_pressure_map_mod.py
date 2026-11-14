"""Assemble a separate private map addon; never install or execute a game."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''):
    sys.path.insert(0, str(ROOT))
from tools.qualify_pressure_geometry import _layout

UUID = 'e8b15363-c9b9-4dcb-b575-117d9308d426'
MAPS = {'NO_SITE': 'Maps/P6PressureNoSite.lua', 'MANY': 'Maps/P6PressureMany.lua'}
MANY_WATER1_PATH = 'Maps/P6PressureManyWater1.lua'


def _lua(value):
    if type(value) is dict:
        return '{' + ','.join('[' + _lua(k) + ']=' + _lua(v) for k, v in value.items()) + '}'
    if type(value) is list:
        return '{' + ','.join(_lua(v) for v in value) + '}'
    if type(value) is bool:
        return 'true' if value else 'false'
    if type(value) is int:
        return str(value)
    if type(value) is str and all(32 <= ord(c) < 127 for c in value):
        return json.dumps(value)
    raise ValueError('Unsupported layout literal')


def _entry(core, layout, variant, *, trace=None):
    text = '''-- PRIVATE artificial initial geometry, never an AI construction claim.
include "MapEnums"
local GenerateGeometry=(function()
''' + core + '\nend)()\nlocal layout=' + _lua(layout) + '''
local generated=false
function GetMapInitData(mapSize)
  return {Width=44,Height=26,WrapX=false}
end
function GenerateMap()
  assert(not generated,'Private map generation already attempted')
  generated=true
  local result=GenerateGeometry({in_generation=true,Map=Map,TerrainBuilder=TerrainBuilder,
    AreaBuilder=AreaBuilder,Players=Players,grass=g_TERRAIN_TYPE_GRASS,
    ocean=g_TERRAIN_TYPE_OCEAN,hills=g_TERRAIN_TYPE_GRASS_HILLS},layout,"''' + variant + '''")
  print('P6_PRESSURE_MAP_GEOMETRY_READY',layout.fixture_id,result.variant,
    result.width,result.height,result.land_tiles)
  return result
end
'''
    if trace is not None:
        emit = "print('P6_PRESSURE_MAP_TRACE','" + variant + "',stage,n)"
        text = text.replace('include "MapEnums"', "pcall(print,'P6_PRESSURE_MAP_TRACE','" + variant + "','ENTRY_LOADED',0)\ninclude \"MapEnums\"", 1)
        text = text.replace('local generated=false', 'local MakeTrace=(function()\n' + trace + '\nend)()\nlocal generated=false', 1)
        text = text.replace('function GetMapInitData(mapSize)', 'function GetMapInitData(mapSize)\n  ' + emit.replace('print(', 'pcall(print,', 1).replace('stage,n', "'INITDATA',mapSize"), 1)
        old = '''  local result=GenerateGeometry({in_generation=true,Map=Map,TerrainBuilder=TerrainBuilder,
    AreaBuilder=AreaBuilder,Players=Players,grass=g_TERRAIN_TYPE_GRASS,
    ocean=g_TERRAIN_TYPE_OCEAN,hills=g_TERRAIN_TYPE_GRASS_HILLS},layout,"''' + variant + '''")'''
        new = '''  local Emit=function(stage,n) ''' + emit + ''' end
  pcall(Emit,'GENERATE_BEGIN',0)
  local env,Snapshot=MakeTrace({in_generation=true,Map=Map,TerrainBuilder=TerrainBuilder,
    AreaBuilder=AreaBuilder,Players=Players,grass=g_TERRAIN_TYPE_GRASS,
    ocean=g_TERRAIN_TYPE_OCEAN,hills=g_TERRAIN_TYPE_GRASS_HILLS},Emit)
  local result=GenerateGeometry(env,layout,"''' + variant + '''")
  local trace=Snapshot()
  pcall(Emit,'GENERATE_END',trace.terrain_completed)
  pcall(Emit,'LOGGING_ERRORS',trace.logging_errors)'''
        if text.count(old) != 1:
            raise ValueError('Unknown generation trace binding')
        text = text.replace(old, new, 1)
        text = text.replace("  print('P6_PRESSURE_MAP_GEOMETRY_READY',", "  pcall(print,'P6_PRESSURE_MAP_GEOMETRY_READY',", 1)
    return text


def _xml(root):
    return ET.tostring(root, encoding='utf-8', xml_declaration=True) + b'\n'


def _manifest(maps=None):
    maps = MAPS if maps is None else maps
    root = ET.Element('Mod', id=UUID, version='1')
    properties = ET.SubElement(root, 'Properties')
    for key, value in {'Name': 'PRIVATE P6 pressure maps', 'Description': 'Artificial private fixture geometry',
                       'Authors': 'Codex', 'CompatibleVersions': '2.0', 'EnabledByDefault': '0'}.items():
        ET.SubElement(properties, key).text = value
    frontend = ET.SubElement(root, 'FrontEndActions')
    ET.SubElement(ET.SubElement(frontend, 'UpdateDatabase', id='PressureMapConfig'), 'File').text = 'Config/PressureMaps.xml'
    for variant, path in maps.items():
        action = ET.SubElement(frontend, 'AddMap', id='PressureMap' + variant)
        p = ET.SubElement(action, 'Properties')
        for key, value in {'Name': 'PRIVATE P6 ' + variant, 'Description': 'Artificial pressure geometry ' + variant,
                           'Group': 'StandardMaps'}.items():
            ET.SubElement(p, key).text = value
        ET.SubElement(action, 'File').text = path
    payload = ET.SubElement(root, 'Files')
    for path in ['Config/PressureMaps.xml', *maps.values()]:
        ET.SubElement(payload, 'File').text = path
    return _xml(root)


def _config(maps=None):
    maps = MAPS if maps is None else maps
    root = ET.Element('GameInfo')
    overrides, sizes = ET.SubElement(root, 'MapDomainOverrides'), ET.SubElement(root, 'MapSizes')
    for path in maps.values():
        key = '{' + UUID + '}' + path
        ET.SubElement(overrides, 'Row', Map=key, ParameterId='MapSize', Domain=key)
        ET.SubElement(sizes, 'Row', Domain=key, MapSizeType='MAPSIZE_TINY', Name='LOC_MAPSIZE_TINY_NAME',
                      Description='LOC_MAPSIZE_TINY_DESCRIPTION', MinPlayers='2', MaxPlayers='2', DefaultPlayers='2',
                      MinCityStates='0', MaxCityStates='0', DefaultCityStates='0', SortIndex='10')
    return _xml(root)


def build(output_dir: Path, *, trace_generation: bool = False, many_water_anchor: bool = False) -> dict:
    if type(trace_generation) is not bool:
        raise ValueError('Trace mode must be a boolean')
    if type(many_water_anchor) is not bool:
        raise ValueError('Many water anchor mode must be a boolean')
    output_dir = Path(output_dir).resolve()
    if output_dir.exists() or any(output_dir.is_relative_to(ROOT / p) for p in ('mod', 'tools', 'tests', 'docs')):
        raise ValueError('New separate output directory required')
    layout_bytes = (ROOT / 'tools/fixtures/pressure_layout_v1.json').read_bytes()
    core_bytes = (ROOT / 'tools/lua/pressure_fixture_geometry.lua').read_bytes()
    layout = json.loads(layout_bytes.decode('utf-8'))
    _layout(layout)
    trace_bytes = (ROOT / 'tools/lua/pressure_generation_trace.lua').read_bytes() if trace_generation else None
    maps = dict(MAPS)
    if many_water_anchor:
        maps['MANY_WATER1'] = MANY_WATER1_PATH
    files = {'PressureMaps.modinfo': _manifest(maps), 'Config/PressureMaps.xml': _config(maps)}
    for variant, path in maps.items():
        files[path] = _entry(core_bytes.decode('utf-8'), layout, variant,
                             trace=trace_bytes.decode('utf-8') if trace_bytes is not None else None).encode('utf-8')
    from lupa.lua51 import LuaRuntime as Lua51
    from lupa.lua53 import LuaRuntime as Lua53
    for runtime in (Lua51(), Lua53()):
        for path in maps.values():
            runtime.compile(files[path].decode('utf-8'))
    output_dir.mkdir(parents=True, exist_ok=False)
    package = output_dir / 'PressureMaps'
    for path, data in files.items():
        target = package / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    sha = lambda data: hashlib.sha256(data).hexdigest()
    result = dict(mode='baiqi-pressure-map-v1', installed=False, native_generated=False, files=len(files),
                  package_file_sha256={p: sha((package / p).read_bytes()) for p in files},
                  map_scripts={v: '{' + UUID + '}' + p for v, p in maps.items()},
                  layout_sha256=sha(layout_bytes), geometry_sha256=sha(core_bytes))
    if trace_generation:
        result.update(mode='baiqi-pressure-map-trace-v1', generation_trace=True, trace_sha256=sha(trace_bytes))
    if many_water_anchor:
        result.update(mode='baiqi-pressure-map-water1-v1', many_water_anchor=True)
    (output_dir / 'pressure-map-build.json').write_bytes((json.dumps(result, indent=2) + '\n').encode('utf-8'))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--trace-generation', action='store_true')
    parser.add_argument('--many-water-anchor', action='store_true')
    args = parser.parse_args()
    result = build(args.output_dir, trace_generation=args.trace_generation, many_water_anchor=args.many_water_anchor)
    print(json.dumps({k: result[k] for k in ('mode', 'files', 'installed', 'native_generated')}))
