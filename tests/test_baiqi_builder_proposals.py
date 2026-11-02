"""Native proposal shapes, Index/Hash consumers and real builder write guards."""
from pathlib import Path
import unittest

from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class BuilderProposalTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua', 'mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua', 'mod/Baiqi/Lua/BaiqiPlanner.lua'):
            self.lua.execute((ROOT / name).read_text(encoding='utf-8'))
        self.private = self.lua.execute(
            (ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
            + '\nreturn {Candidates=BuilderImprovementCandidates,Builder=ProcessBuilder}\n')
        self.w = self.lua.globals().TestWorld
        self.lua.globals().BaiqiController.RunNow(False)
        self.lua.execute('''
            local w=TestWorld
            w.builderRecommendations={};w.genericQueries=0;w.specificQueries={};w.metadataScans=0
            w.genericCan=true;w.proposals={[99]={8,2,8}};w.allowedHashes={[202]=true,[808]=true}
            UnitOperationResults={IMPROVEMENTS=99}
            local r0={Index=0,Hash=101};local r2={Index=2,Hash=202};local r8={Index=8,Hash=808}
            GameInfo.Improvements=setmetatable({[0]=r0,[2]=r2,[8]=r8,[101]=r0,[202]=r2,[808]=r8},
              {__call=function()
                w.metadataScans=w.metadataScans+1
                local rows={r8,r2,r0};local i=0
                return function() i=i+1;return rows[i] end
              end})
            local original=UnitManager.CanStartOperation
            UnitManager.CanStartOperation=function(unit,op,mode,params,wantResults)
              if op~=UnitOperationTypes.BUILD_IMPROVEMENT then return original(unit,op,mode,params) end
              assert(unit==w.objects.builder and mode==nil and params[14]==2 and params[15]==3)
              if wantResults==true then
                assert(params[16]==nil)
                w.genericQueries=w.genericQueries+1
                if w.genericError then error('native query unavailable') end
                return w.genericCan,w.proposals
              end
              assert(wantResults==nil and params[16]~=nil)
              local hash=params[16]
              w.specificQueries[#w.specificQueries+1]=hash
              if w.rejectFinal and #w.specificQueries==2 then return false end
              return w.allowedHashes[hash]==true
            end
        ''')

    def candidates(self):
        g = self.lua.globals()
        result = self.private.Candidates(self.w.objects.builder, g.Map.GetPlotByIndex(42))
        self.assertEqual(len(self.w.unitRequests), 0)
        return result

    def unknown(self, setup):
        self.lua.execute(setup)
        self.assertIsNone(self.candidates())

    def builder(self):
        ctx = self.lua.table_from(dict(player=7, localPlayer=7, isBaiqi=True,
                                       activeTurn=True, enabled=True))
        return self.private.Builder(ctx, self.w.objects.player, self.lua.table(), self.w.objects.builder)

    def hashes(self):
        return list(self.w.specificQueries.values())

    def test_sorted_deduplicated_actual_rows_from_native_indices(self):
        result = self.candidates()
        self.assertIsNotNone(result)
        self.assertEqual([r.Hash for r in result.values()], [202, 808])
        self.assertEqual(self.w.genericQueries, 1)
        self.assertEqual(self.w.metadataScans, 0)

    def test_metadata_hash_alias_also_resolves_actual_row(self):
        self.lua.execute('TestWorld.proposals={[99]={808,202,808}}')
        self.assertEqual([r.Index for r in self.candidates().values()], [2, 8])

    def test_known_empty_table_is_distinct_from_unknown(self):
        self.lua.execute('TestWorld.proposals={[99]={}}')
        result = self.candidates()
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 0)

    def test_false_nil_is_unknown_not_empty(self):
        self.unknown('TestWorld.genericCan=false;TestWorld.proposals=nil')

    def test_false_with_result_table_is_still_unknown(self):
        self.unknown('TestWorld.genericCan=false')

    def test_missing_result_list_is_unknown(self):
        self.unknown('TestWorld.proposals={}')

    def test_non_table_results_are_unknown(self):
        self.unknown('TestWorld.proposals=42')

    def test_sparse_array_is_unknown(self):
        self.unknown('TestWorld.proposals={[99]={[1]=2,[3]=8}}')

    def test_zero_array_key_is_unknown(self):
        self.unknown('TestWorld.proposals={[99]={[0]=2,[1]=8}}')

    def test_string_array_key_is_unknown(self):
        self.unknown('TestWorld.proposals={[99]={unexpected=2}}')

    def test_fractional_array_key_is_unknown(self):
        self.unknown('TestWorld.proposals={[99]={[1.5]=2}}')

    def test_missing_row_is_unknown(self):
        self.unknown('TestWorld.proposals={[99]={99}}')

    def test_non_table_row_is_unknown(self):
        self.unknown('GameInfo.Improvements[2]=42')

    def test_nonfinite_hash_is_unknown(self):
        self.unknown('GameInfo.Improvements[2].Hash=math.huge')

    def test_fractional_index_is_unknown(self):
        self.unknown('GameInfo.Improvements[2].Index=0.5')

    def test_negative_hash_and_zero_index_are_valid(self):
        self.lua.execute('GameInfo.Improvements[0].Hash=-101;TestWorld.proposals={[99]={0}}')
        self.assertEqual(self.candidates()[1].Hash, -101)

    def test_missing_binding_does_not_query(self):
        self.unknown('UnitManager.CanStartOperation=nil')
        self.assertEqual(self.w.genericQueries, 0)

    def test_missing_enum_does_not_query(self):
        self.unknown('UnitOperationResults.IMPROVEMENTS=nil')
        self.assertEqual(self.w.genericQueries, 0)

    def test_native_error_returns_unknown(self):
        self.unknown('TestWorld.genericError=true')

    def test_builder_qualifies_hash_and_rechecks_at_write(self):
        self.builder()
        self.assertEqual(self.hashes(), [202, 202])
        request = self.w.unitRequests[1]
        self.assertEqual((request.unit, request.op, request.params[16]), (3, 12, 202))
        self.assertEqual(self.w.metadataScans, 0)

    def test_illegal_first_proposal_tries_next_sorted_proposal(self):
        self.lua.execute('TestWorld.allowedHashes[202]=false')
        self.builder()
        self.assertEqual(self.hashes(), [202, 808, 808])
        self.assertEqual(self.w.unitRequests[1].params[16], 808)

    def test_unknown_query_falls_back_to_full_scan_and_lowest_index(self):
        self.lua.execute('TestWorld.proposals=nil;TestWorld.allowedHashes[101]=true')
        self.builder()
        self.assertEqual(self.hashes(), [808, 202, 101, 101])
        self.assertEqual(self.w.metadataScans, 1)
        self.assertEqual(self.w.unitRequests[1].params[16], 101)

    def test_known_empty_does_not_query_each_metadata_row(self):
        self.lua.execute('TestWorld.proposals={[99]={}};TestWorld.allowedHashes={}')
        self.builder()
        self.assertEqual(self.hashes(), [])
        self.assertEqual(self.w.metadataScans, 0)
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_write_rejection_does_not_choose_another_improvement(self):
        self.w.rejectFinal = True
        self.builder()
        self.assertEqual(self.hashes(), [202, 202])
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_proposals_are_refreshed_between_invocations(self):
        self.assertEqual(self.candidates()[1].Hash, 202)
        self.lua.execute('TestWorld.proposals={[99]={8}}')
        self.assertEqual(self.candidates()[1].Hash, 808)
        self.assertEqual(self.w.genericQueries, 2)


if __name__ == '__main__':
    unittest.main()
