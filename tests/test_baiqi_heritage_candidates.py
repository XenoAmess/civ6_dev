"""Proposal filtering only; these tests do not grant a native special action."""
from pathlib import Path
import unittest
from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'mod/Baiqi/Lua/BaiqiHeritageCandidates.lua'


class HeritageCandidatesTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.collect = self.lua.execute(SOURCE.read_text(encoding='utf-8'))

    def indices(self, value):
        return [value[i] for i in range(1, len(value) + 1)]

    def fixture(self):
        return self.lua.execute('''
          local trace={lookups=0,owners=0,providers=0}
          local provider={}
          function provider:GetPossibleParkTiles(pid)
            assert(self==provider and pid==4);trace.providers=trace.providers+1
            return {9,2,9,6,3,7,5,8,1,false,-1,1.5,math.huge,'2'}
          end
          function provider:GetActivationHighlightPlots()
            assert(self==provider);trace.providers=trace.providers+1
            return {9,2,9,6,3,7,5,8,1,false,-1,1.5,math.huge,'2'}
          end
          local game={GetNationalParks=function(...)
            assert(select('#',...)==0);return provider
          end}
          local unit={}
          function unit:GetArchaeology() assert(self==unit);return provider end
          local map={GetPlotByIndex=function(...)
            assert(select('#',...)==1)
            local index=...;trace.lookups=trace.lookups+1
            if index==8 then return false end
            if trace.throwIndex==index then error('native failure') end
            local plot={}
            function plot:GetIndex() assert(self==plot);return index==7 and 70 or index end
            function plot:GetX() assert(self==plot);return index==5 and -1 or index end
            function plot:GetY() assert(self==plot);return 0 end
            function plot:GetOwner()
              assert(self==plot and index~=6 and index~=3)
              trace.owners=trace.owners+1
              return index==1 and 8 or 4
            end
            return plot
          end}
          local visibility={}
          function visibility:IsRevealed(x,y) assert(self==visibility);return x~=6 end
          function visibility:IsVisible(x,y) assert(self==visibility and x~=6);return x~=3 end
          return game,map,visibility,unit,trace,provider
        ''')

    def test_both_actual_providers_sorted_visible_domestic_only(self):
        for kind in ('UNIT_NATURALIST', 'UNIT_ARCHAEOLOGIST'):
            with self.subTest(kind=kind):
                game, map_, visibility, unit, trace, _ = self.fixture()
                result, status = self.collect(kind, 4, unit, game, map_, visibility)
                self.assertEqual((self.indices(result), status), ([2, 9], 'ok'))
                self.assertEqual((trace.lookups, trace.owners, trace.providers), (8, 3, 1))

    def test_hidden_ownership_is_never_read(self):
        game, map_, visibility, unit, trace, _ = self.fixture()
        result, status = self.collect('UNIT_NATURALIST', 4, unit, game, map_, visibility)
        self.assertEqual(status, 'ok')
        self.assertEqual(self.indices(result), [2, 9])
        self.assertEqual(trace.owners, 3)  # Hidden/revealed-only plot getters assert if called.

    def test_native_error_discards_already_accepted_results(self):
        game, map_, visibility, unit, trace, _ = self.fixture()
        trace.throwIndex = 1  # Two valid results were visited before this provider error.
        result, status = self.collect('UNIT_NATURALIST', 4, unit, game, map_, visibility)
        self.assertEqual((self.indices(result), status), ([], 'unavailable'))
        self.assertEqual(trace.owners, 2)

    def test_unsupported_and_invalid_owner_do_not_touch_dependencies(self):
        poison = self.lua.execute("return setmetatable({}, {__index=function() error('dependency touched') end})")
        for kind in ('UNIT_APOSTLE', 'UNIT_INQUISITOR', 'UNIT_GURU', 'UNIT_WARRIOR', 'UNIT_MISSIONARY'):
            result, status = self.collect(kind, 4, poison, poison, poison, poison)
            self.assertEqual((self.indices(result), status), ([], 'unsupported'))
        for pid in (-1, 0.5, True, None, float('inf'), float('nan'), 2147483648):
            result, status = self.collect('UNIT_NATURALIST', pid, poison, poison, poison, poison)
            self.assertEqual((self.indices(result), status), ([], 'invalid'))

    def test_missing_malformed_and_throwing_dependencies_fail_closed(self):
        for expression in (
                'nil', 'false', '{}', '{GetNationalParks=true}',
                '{GetNationalParks=function() error("provider") end}',
                '{GetNationalParks=function() return {} end}',
                '{GetNationalParks=function() return {GetPossibleParkTiles=function() return false end} end}',
                'setmetatable({}, {__index=function() error("lookup") end})'):
            with self.subTest(expression=expression):
                game, map_, visibility, unit, _, _ = self.fixture()
                game = self.lua.execute('return ' + expression)
                result, status = self.collect('UNIT_NATURALIST', 4, unit, game, map_, visibility)
                self.assertEqual((self.indices(result), status), ([], 'unavailable'))

    def test_each_provider_ignores_unrelated_component(self):
        game, map_, visibility, unit, _, _ = self.fixture()
        result, status = self.collect('UNIT_NATURALIST', 4, None, game, map_, visibility)
        self.assertEqual((self.indices(result), status), ([2, 9], 'ok'))
        result, status = self.collect('UNIT_ARCHAEOLOGIST', 4, unit, None, map_, visibility)
        self.assertEqual((self.indices(result), status), ([2, 9], 'ok'))

    def test_missing_methods_and_nonboolean_visibility_are_not_permission(self):
        for altered in ('map.GetPlotByIndex=nil', 'visibility.IsVisible=nil',
                        'function visibility:IsVisible() return 1 end',
                        'function visibility:IsRevealed() error("visibility") end'):
            game, map_, visibility, unit, _, _ = self.fixture()
            self.lua.globals().map, self.lua.globals().visibility = map_, visibility
            self.lua.execute(altered)
            result, status = self.collect('UNIT_NATURALIST', 4, unit, game, map_, visibility)
            expected = 'ok' if 'return 1' in altered else 'unavailable'
            self.assertEqual((self.indices(result), status), ([], expected))


if __name__ == '__main__':
    unittest.main()
