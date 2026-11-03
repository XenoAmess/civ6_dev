"""Pure metadata consumers; this port never grants or executes game operations."""
from pathlib import Path
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


def load_archaeology_journal():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiArchaeologyJournal.lua').read_text(encoding='utf-8'))
    return lua, lua.globals().BaiqiArchaeologyJournal


def excavation_state():
    return {
        'version': 1, 'owner': 7, 'serial': 1,
        'operations': {'4': {
            'token': 'archaeology:7:1', 'sequence': 1, 'unitID': 4,
            'unitType': 'UNIT_ARCHAEOLOGIST', 'homeCityID': 66,
            'cityX': 2, 'cityY': 3, 'buildingIndex': 24,
            'x': 4, 'y': 3, 'resourceIndex': 9,
            'resourceType': 'RESOURCE_ANTIQUITY_SITE', 'turn': 92,
            'stage': 'EXCAVATE_ARMED', 'baselineWorkIDs': [], 'works': {},
        }},
    }


def to_lua(lua, value):
    if isinstance(value, dict):
        return lua.table_from({key: to_lua(lua, item) for key, item in value.items()})
    if isinstance(value, list):
        return lua.table_from([to_lua(lua, item) for item in value])
    return value
