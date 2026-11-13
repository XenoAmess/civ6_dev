"""Qualify raw hint snapshots without claiming controller or map legality."""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class SettlementHintDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.probe = self.lua.execute(
            (ROOT / 'tools/lua/diagnostic_settlement_hints.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
          calls=0; raw={}; player={}
          function player:GetGrandStrategicAI()
            assert(self==player)
            return {GetSettlementRecommendations=function(self,n)
              assert(n==12); calls=calls+1;return raw
            end}
          end
        ''')

    def probe_current(self, limit=128):
        return self.probe(self.lua.globals().player, limit)

    def test_empty_is_complete_but_nil_and_non_table_are_unknown(self):
        result = self.probe_current()
        self.assertTrue(result.complete)
        self.assertEqual((result.status, result.inspected), ('COMPLETE', 0))
        for raw in ('nil', 'false', '7', '"not a table"'):
            with self.subTest(raw=raw):
                self.lua.execute('raw=' + raw)
                result = self.probe_current()
                self.assertEqual(result.status, 'UNKNOWN_RETURN')
                self.assertFalse(result.complete)

    def test_sparse_ranks_and_duplicates_do_not_hide_valid_indices(self):
        self.lua.execute('''
          raw={[0]={SettlingLocation=7},["2"]={SettlingLocation=7},
            [20]={SettlingLocation=9},[false]={SettlingLocation=11}}
        ''')
        result = self.probe_current()
        self.assertEqual((result.inspected, result.unique, result.duplicates), (4, 3, 1))
        self.assertEqual((result.nonnumericRanks, result.invalidEntries, result.invalidIndices), (1, 0, 0))
        self.assertEqual({r.index for r in result.rows.values()}, {7, 9, 11})
        self.assertTrue(result.complete)

    def test_bad_entry_and_index_counts_are_independent_of_rank(self):
        self.lua.execute('''
          raw={false,{},{SettlingLocation=-1},{SettlingLocation=0/0},
            {SettlingLocation=math.huge},{SettlingLocation=1.5},
            {SettlingLocation="5"},{SettlingLocation=0}}
        ''')
        result = self.probe_current()
        self.assertEqual((result.inspected, result.unique, result.invalidEntries, result.invalidIndices),
                         (8, 1, 1, 6))
        self.assertTrue(result.complete)  # Complete inspection can contain invalid data.

    def test_exact_limit_is_complete_but_extra_entry_is_partial(self):
        self.lua.execute('raw={{SettlingLocation=1},{SettlingLocation=2}}')
        self.assertEqual(self.probe_current(2).status, 'COMPLETE')
        self.lua.execute('raw[3]={SettlingLocation=3}')
        result = self.probe_current(2)
        self.assertEqual((result.status, result.inspected, len(result.rows)), ('PARTIAL_LIMIT', 2, 2))
        self.assertFalse(result.complete)

    def test_throwing_field_is_partial_and_other_rows_are_still_inspected(self):
        self.lua.execute('''
          raw={setmetatable({}, {__index=function() error('field') end}),
            {SettlingLocation=2}}
        ''')
        result = self.probe_current()
        self.assertEqual((result.status, result.inspected, result.fieldErrors, result.unique),
                         ('PARTIAL_FIELD_ERROR', 2, 1, 1))
        self.assertFalse(result.complete)

    def test_reader_failure_is_not_retried_or_called_empty(self):
        self.lua.execute('''
          function player:GetGrandStrategicAI()
            return {GetSettlementRecommendations=function() calls=calls+1;error('reader') end}
          end
        ''')
        result = self.probe_current()
        self.assertEqual(result.status, 'UNKNOWN_READER')
        self.assertEqual(self.lua.globals().calls, 1)
        self.assertFalse(result.complete)
        self.lua.execute("player.GetGrandStrategicAI=function() error('ai') end")
        self.assertEqual(self.probe_current().status, 'UNKNOWN_AI')

    def test_invalid_limit_does_not_invoke_native_reader(self):
        for limit in (0, -1, 4097, 1.5, float('nan'), float('inf'), '2', False):
            with self.subTest(limit=limit):
                self.assertEqual(self.probe_current(limit).status, 'UNKNOWN_LIMIT')
        self.assertEqual(self.lua.globals().calls, 0)

    def test_cap_bounds_rows_for_large_input_and_preserves_original_table(self):
        self.lua.execute('''
          raw={};for i=1,4097 do raw[i]={SettlingLocation=i} end
          savedRaw=raw;savedFirst=raw[1]
          setmetatable(raw,{__newindex=function()error('mutation')end})
        ''')
        result = self.probe_current(4096)
        self.assertEqual((result.status, result.inspected, len(result.rows)), ('PARTIAL_LIMIT', 4096, 4096))
        self.lua.execute('assert(raw==savedRaw and raw[1]==savedFirst and #raw==4097)')
        self.assertEqual(self.lua.globals().calls, 1)


if __name__ == '__main__':
    unittest.main()
