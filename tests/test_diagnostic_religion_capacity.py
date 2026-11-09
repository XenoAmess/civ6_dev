"""Native-shaped read ports, including zero IDs, unknowns and iterator state."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'tools/lua/diagnostic_religion_capacity.lua').read_text(encoding='utf-8')
FIXTURE = '''
rows={{MapSizeType='MAPSIZE_SMALL',GreatPersonClassType='GREAT_PERSON_CLASS_PROPHET',MaxWorldInstances=4}}
religions={{Religion=0},{Religion=1},{Religion=2}};founded={[1]=true,[2]=true}
religion={GetReligions=function()return religions end,HasBeenFounded=function(_,id)return founded[id]end}
E={Map={GetMapSize=function()return 2 end},Game={GetReligion=function()return religion end},
 GameInfo={Maps={[2]={MapSizeType='MAPSIZE_SMALL'}},Religions={[0]={Pantheon=true},[1]={Pantheon=false},[2]={Pantheon=false}}}}
E.GameInfo.Map_GreatPersonClasses=function()local i=0;return function()i=i+1;return rows[i]end end
'''


class ReligionCapacityTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().M = self.lua.execute(SOURCE)
        self.lua.execute(FIXTURE)

    def result(self, change='', ports='E'):
        if change:
            self.lua.execute(change)
        return self.lua.eval('M.Read(' + ports + ')')

    def unknown(self, change='', ports='E'):
        r = self.result(change, ports)
        self.assertEqual(r.status, 'UNKNOWN')
        self.assertIsNone(r.arithmeticDifference)

    def test_valid_counts_are_only_an_arithmetic_bound(self):
        r = self.result()
        self.assertEqual((r.status, r.mapClassCap, r.foundedCount, r.arithmeticDifference), ('OK', 4, 2, 2))

    def test_map_index_zero_is_valid(self):
        r = self.result('E.GameInfo.Maps[0]=E.GameInfo.Maps[2];E.Map.GetMapSize=function()return 0 end')
        self.assertEqual((r.status, r.mapSizeIndex, r.mapClassCap), ('OK', 0, 4))

    def test_religion_id_zero_can_be_non_pantheon(self):
        r = self.result('E.GameInfo.Religions[0].Pantheon=false;founded[0]=true')
        self.assertEqual((r.status, r.foundedCount), ('OK', 3))

    def test_known_cap_zero_is_not_unknown(self):
        r = self.result('rows[1].MaxWorldInstances=0;religions={}')
        self.assertEqual((r.status, r.mapClassCap, r.foundedCount, r.arithmeticDifference), ('OK', 0, 0, 0))

    def test_negative_difference_is_not_clamped_to_zero(self):
        r = self.result('rows[1].MaxWorldInstances=1')
        self.assertEqual((r.status, r.arithmeticDifference), ('OK', -1))

    def test_sparse_list_is_unknown(self):
        self.unknown('religions={[1]={Religion=1},[3]={Religion=2}}')

    def test_non_array_key_is_unknown(self):
        self.unknown("religions.extra={Religion=3}")

    def test_zero_array_key_is_not_a_zero_religion_id(self):
        self.unknown('religions={[0]={Religion=1}}')

    def test_duplicate_matching_rows_are_unknown_even_if_identical(self):
        self.unknown('rows[2]=rows[1]')

    def test_infinite_cap_is_unknown(self):
        self.unknown('rows[1].MaxWorldInstances=math.huge')

    def test_fractional_cap_is_unknown(self):
        self.unknown('rows[1].MaxWorldInstances=1.5')

    def test_missing_map_row_does_not_report_zero(self):
        self.unknown('E.GameInfo.Maps={}')

    def test_native_throw_is_unknown(self):
        self.unknown("E.Map.GetMapSize=function()error('native')end")

    def test_founded_throw_is_unknown(self):
        self.unknown("religion.HasBeenFounded=function()error('native')end")

    def test_unknown_founded_boolean_is_unknown(self):
        self.unknown('founded[1]=nil')

    def test_generic_for_preserves_state_and_control(self):
        r = self.result('''rows[1].ordinal=1
          E.GameInfo.Map_GreatPersonClasses=function()
            return function(state,last)return state[(last and last.ordinal or 0)+1]end,rows,nil
          end''')
        self.assertEqual((r.status, r.mapClassCap), ('OK', 4))

    def test_unbounded_iterator_stops(self):
        self.unknown('''E.GameInfo.Map_GreatPersonClasses=function()return function()
          return {MapSizeType='OTHER',GreatPersonClassType='OTHER'}end end''')

    def test_nil_ports_are_unknown(self):
        self.unknown(ports='nil')

    def test_metatable_record_cannot_fake_a_religion(self):
        self.unknown("religions={setmetatable({},{__index={Religion=1}})}")

    def test_more_than_64_religions_is_unknown(self):
        self.unknown('''religions={};for i=1,65 do religions[i]={Religion=i};
          E.GameInfo.Religions[i]={Pantheon=false};founded[i]=true end''')

    def test_native_object_metatables_are_allowed(self):
        r = self.result('E.Map=setmetatable({},{__index={GetMapSize=function()return 2 end}})')
        self.assertEqual(r.status, 'OK')

    def test_result_does_not_alias_sources_or_later_results(self):
        self.lua.execute('local a=M.Read(E);a.mapClassCap=99;local b=M.Read(E);assert(b.mapClassCap==4 and rows[1].MaxWorldInstances==4)')


if __name__ == '__main__':
    unittest.main()
