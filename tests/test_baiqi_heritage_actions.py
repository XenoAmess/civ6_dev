from pathlib import Path
import json
import unittest
from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class HeritageActionsTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.resolve = self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiHeritageActions.lua').read_text(encoding='utf-8'))

    def test_fourteen_reviewed_model_data_cases(self):
        cases = json.loads((ROOT / 'tests/data/heritage-operation-cases.json').read_text(encoding='utf-8'))
        self.assertEqual(len(cases), 14)
        for case in cases:
            with self.subTest(case=case['name']):
                provider = self.lua.table()
                provider['UNITOPERATION_' + case['operation']] = self.lua.table_from(case['row']) if case['row'] is not None else None
                self.assertEqual(self.resolve(case['unitType'], case['operation'], provider),
                                 (case['expected_hash'], case['expected_status']))

    def test_primitive_provider_cannot_borrow_string_library_rows(self):
        provider = self.lua.execute("getmetatable('').__index.UNITOPERATION_DESIGNATE_PARK={OperationType='UNITOPERATION_DESIGNATE_PARK',Hash=123}; return 'primitive-provider'")
        for value in (provider, None, False, True, 0, 1):
            self.assertEqual(self.resolve('UNIT_NATURALIST', 'DESIGNATE_PARK', value), (None, 'unavailable'))

    def test_index_is_never_a_hash_fallback(self):
        for row in ({'OperationType': 'UNITOPERATION_EXCAVATE', 'Index': 11},
                    {'OperationType': 'UNITOPERATION_EXCAVATE', 'Hash': False, 'Index': 11},
                    {'OperationType': 'UNITOPERATION_WRONG', 'Hash': 1548958412, 'Index': 11}):
            provider = self.lua.table()
            provider.UNITOPERATION_EXCAVATE = self.lua.table_from(row)
            self.assertEqual(self.resolve('UNIT_ARCHAEOLOGIST', 'EXCAVATE', provider), (None, 'unavailable'))

    def test_lookup_row_name_and_hash_errors_fail_closed(self):
        for expression in (
                "setmetatable({}, {__index=function() error('provider') end})",
                "{UNITOPERATION_EXCAVATE=setmetatable({}, {__index=function() error('row') end})}",
                "{UNITOPERATION_EXCAVATE=setmetatable({OperationType='UNITOPERATION_EXCAVATE'}, {__index=function() error('hash') end})}"):
            provider = self.lua.execute('return ' + expression)
            self.assertEqual(self.resolve('UNIT_ARCHAEOLOGIST', 'EXCAVATE', provider), (None, 'unavailable'))

    def test_unsupported_pairs_never_read_the_provider(self):
        poison = self.lua.execute("return setmetatable({}, {__index=function() error('touched') end})")
        for kind, operation in (('UNIT_APOSTLE', 'EXCAVATE'), ('UNIT_INQUISITOR', 'DESIGNATE_PARK'),
                                ('UNIT_GURU', 'DESIGNATE_PARK'), ('UNIT_WARRIOR', 'MOVE_TO'),
                                ('UNIT_MISSIONARY', 'SPREAD_RELIGION'), ('UNIT_ARCHAEOLOGIST', 'DESIGNATE_PARK')):
            self.assertEqual(self.resolve(kind, operation, poison), (None, 'unsupported'))

    def test_nonfinite_and_out_of_range_hashes_rejected(self):
        for value in (float('nan'), float('inf'), -float('inf'), -2147483649, 4294967296, 0.25):
            provider = self.lua.table()
            provider.UNITOPERATION_EXCAVATE = self.lua.table_from({'OperationType': 'UNITOPERATION_EXCAVATE', 'Hash': value})
            self.assertEqual(self.resolve('UNIT_ARCHAEOLOGIST', 'EXCAVATE', provider), (None, 'unavailable'))


if __name__ == '__main__':
    unittest.main()
