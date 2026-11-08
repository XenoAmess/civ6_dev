from pathlib import Path
import json,unittest
from lupa.lua51 import LuaRuntime
from missionary_purchase_fixtures import guard_fixture
ROOT=Path(__file__).resolve().parents[1]


class FaithPurchaseAuditTests(unittest.TestCase):
    def test_absence_unknown_consistent_state_and_no_write_cases(self):
        data=json.loads((ROOT/'tests/fixtures/faith_purchase_audit_cases.json').read_text(encoding='utf-8'))
        source=(ROOT/'tools/lua/diagnostic_faith_purchase_journals.lua').read_text(encoding='utf-8')
        for name,code in data['cases'].items():
            with self.subTest(case=name):
                lua=LuaRuntime(unpack_returned_tuples=True)
                for file in ('BaiqiNaturalistPurchaseJournal','BaiqiMissionaryPurchaseJournal','BaiqiReligiousJournal'):
                    lua.execute((ROOT/f'mod/Baiqi/Lua/{file}.lua').read_text(encoding='utf-8'))
                lua.execute(guard_fixture+data['fixture_suffix'])
                lua.globals().M=lua.execute(source)
                lua.execute(code)
                self.assertEqual(lua.globals().H.writes,0)
