"""Actual city ranking, empire commitments and final religious demand checks."""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class FirstHolySiteTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for path in ('tests/lua/mock_world.lua', 'tests/lua/mock_first_holy_site.lua'):
            self.lua.execute((ROOT/path).read_text(encoding='utf-8'))
        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner'):
            self.lua.execute((ROOT/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        override = os.environ.get('BAIQI_FIRST_HOLY_CONTROLLER')
        source = Path(override) if override else ROOT/'mod/Baiqi/Lua/BaiqiController.lua'
        self.lua.execute(source.read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController

    def execute(self, source):
        self.lua.execute(source)

    def chosen(self):
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 1)
        self.assertEqual(len(self.w.unitRequests), 0)
        params = self.w.cityRequests[1].params
        return params[3] or params[2] or params[4]

    def test_unclaimed_prophet_and_zero_indices_prioritize_first_site_over_workshop(self):
        self.assertEqual(self.chosen(), 777)

    def test_owned_prophet_does_not_require_public_pool(self):
        self.w.held = True
        self.w.throwTimeline = True
        self.assertEqual(self.chosen(), 777)

    def test_claimant_zero_and_exhausted_pool_keep_normal_ranking(self):
        for value in ('TestWorld.timeline[1].Claimant=0', 'TestWorld.timeline={}'): # Both states have no unclaimed candidate.
            with self.subTest(value=value):
                self.setUp(); self.execute(value)
                self.assertEqual(self.chosen(), 901)

    def test_owned_religion_or_already_earned_founding_capacity_does_not_boost(self):
        for key in ('created', 'earned'):
            with self.subTest(key=key):
                self.setUp(); self.w[key] = 1
                self.assertEqual(self.chosen(), 901)

    def test_other_city_completed_or_placed_site_suppresses_empire_boost(self):
        for key in ('completed', 'placed'):
            with self.subTest(key=key):
                self.setUp(); self.w[key][67] = True
                self.assertEqual(self.chosen(), 901)

    def test_other_city_queue_or_current_hash_suppresses_boost(self):
        for source in ('TestWorld.queues[67]={{DistrictType=3}}',
                       "TestWorld.queues[67]={{DistrictType='DISTRICT_HOLY_SITE'}}",
                       'TestWorld.current[67]=777'):
            with self.subTest(source=source):
                self.setUp(); self.execute(source)
                self.assertEqual(self.chosen(), 901)

    def test_unknown_native_reads_keep_ordinary_production_running(self):
        for key in ('throwReligion', 'throwTimeline', 'districtUnknown'):
            with self.subTest(key=key):
                self.setUp(); self.w[key] = True
                self.assertEqual(self.chosen(), 901)

    def test_malformed_timeline_does_not_gain_boost(self):
        values = ("{[1]={Class=0,Individual=0},[3]={Class=0,Individual=0}}",
                  "{[1]={Class=0,Individual=0},extra=true}",
                  "{{Class=0,Individual=99}}", "{{Class=0,Individual=0,Claimant=-1}}",
                  "{{Class=0,Individual=0},{Class=0,Individual=0}}",
                  "setmetatable({}, {__index={[1]={Class=0,Individual=0}}})",
                  "{{Class=0,Individual=0},{Class=math.huge}}")
        for value in values:
            with self.subTest(value=value):
                self.setUp(); self.execute('TestWorld.timeline='+value)
                self.assertEqual(self.chosen(), 901)

    def test_unknown_definitions_or_capacity_observations_do_not_gain_boost(self):
        for source in ("GameInfo.GreatPersonIndividuals[0]=nil",
                       "GameInfo.GreatPersonIndividuals[0].GreatPersonClassType='WRONG'",
                       'GameInfo.GreatPersonClasses.GREAT_PERSON_CLASS_PROPHET.Index=math.huge',
                       'TestWorld.held=nil', 'TestWorld.earned=nil'):
            with self.subTest(source=source):
                self.setUp(); self.execute(source)
                self.assertEqual(self.chosen(), 901)

    def test_oversize_pool_and_ambiguous_city_inventory_do_not_gain_boost(self):
        for source in ('for i=1,129 do TestWorld.timeline[i]={Class=1}end',
                       'TestWorld.cities[3]=TestWorld.cities[2]',
                       'TestWorld.current[67]=math.huge',
                       'TestWorld.queues[67]={{DistrictType=999}}'):
            with self.subTest(source=source):
                self.setUp(); self.execute(source)
                self.assertEqual(self.chosen(), 901)

    def test_higher_domestic_priorities_and_builder_demand_are_retained(self):
        for hash_value in (100, 101, 202):
            with self.subTest(hash=hash_value):
                self.setUp(); self.w.allowed[hash_value] = True
                if hash_value == 202:
                    self.w.objects.player.GetTreasury = self.lua.eval('function() return {GetGoldBalance=function()return 1000 end,GetGoldYield=function()return 100 end,GetTotalMaintenance=function()return 0 end}end')
                self.assertEqual(self.chosen(), hash_value)

    def test_repairs_keep_priority_above_first_site(self):
        self.execute('''
TestWorld.cities[1].GetBuildings=function()return {IsPillaged=function(_,index)return index==9 end}end
''')
        self.assertEqual(self.chosen(), 901)

    def test_no_opportunity_does_not_disable_ordinary_holy_site(self):
        self.w.timeline = self.lua.table()
        self.w.allowed[901] = False; self.w.allowed[778] = False
        self.assertEqual(self.chosen(), 777)

    def test_existing_queue_is_preserved_and_other_city_can_plan(self):
        self.execute('TestWorld.queues[66]={{BuildingType=9}}')
        self.assertEqual(self.chosen(), 777)
        self.assertEqual(self.w.cityRequests[1].city, 67)
        self.assertEqual(len(self.w.queues[66]), 1)

    def test_first_site_still_requires_native_placement_and_production(self):
        for key in ('noPlacement', 'noOperation'):
            with self.subTest(key=key):
                self.setUp(); self.w[key] = True
                self.assertEqual(self.chosen(), 901)
        self.setUp(); self.w.allowed[777] = False
        self.assertEqual(self.chosen(), 901)

    def test_final_opportunity_change_stops_write_and_replans_same_turn(self):
        for change in ('w.timeline[1].Claimant=0', 'w.created=0', 'w.completed[67]=true',
                       'w.placed[67]=true', 'w.queues[67]={{DistrictType=3}}'):
            with self.subTest(change=change):
                self.setUp()
                self.execute('TestWorld.queues[67]={{BuildingType=9}};TestWorld.shock=function()local w=TestWorld;'+change+' end')
                self.c.RunNow()
                self.assertEqual(len(self.w.cityRequests), 0)
                self.assertEqual(self.w.qualification[777], 2)
                self.assertEqual(self.chosen(), 901)

    def test_final_unknown_demand_does_not_write(self):
        self.execute('TestWorld.queues[67]={{BuildingType=9}};TestWorld.shock=function()TestWorld.throwTimeline=true end')
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)
        self.assertEqual(self.chosen(), 901)

    def test_final_queue_change_is_preserved_without_a_new_request(self):
        self.execute('''
TestWorld.queues[67]={{BuildingType=9}}
TestWorld.shock=function()TestWorld.queues[66]={{BuildingType=9},{BuildingType=1}}end
''')
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)
        self.assertEqual(len(self.w.queues[66]), 2)

    def test_same_turn_second_city_does_not_repeat_first_boost(self):
        self.assertEqual(self.chosen(), 777)
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 2)
        self.assertEqual(self.w.cityRequests[2].params[2], 901)

    def test_unobserved_first_request_survives_empty_queue_timeout_and_turn_change(self):
        self.assertEqual(self.chosen(), 777)
        self.c.Update(3)
        self.w.turn = 2
        self.c.RunNow(); self.c.RunNow()
        holy = [self.w.cityRequests[i] for i in range(1,len(self.w.cityRequests)+1)
                if self.w.cityRequests[i].params[3] == 777]
        self.assertEqual(len(holy), 1)

    def test_unknown_writer_result_cannot_create_second_boost(self):
        self.w.throwWriter = True
        self.c.RunNow()
        self.w.throwWriter = False
        self.c.Update(3)
        self.w.turn = 2; self.c.RunNow(); self.c.RunNow()
        holy = [self.w.cityRequests[i] for i in range(1,len(self.w.cityRequests)+1)
                if self.w.cityRequests[i].params[3] == 777]
        self.assertEqual(len(holy), 1)

    def test_an_unrelated_native_head_does_not_discard_first_request(self):
        self.assertEqual(self.chosen(), 777)
        self.w.current[66] = 901
        self.c.Update(3)
        self.w.turn = 2; self.c.RunNow(); self.c.RunNow()
        holy = [self.w.cityRequests[i] for i in range(1,len(self.w.cityRequests)+1)
                if self.w.cityRequests[i].params[3] == 777]
        self.assertEqual(len(holy), 1)

    def test_background_does_not_gain_control_in_non_baiqi_or_inactive_context(self):
        for change in ("PlayerConfigurations[7].GetLeaderTypeName=function()return 'LEADER_TRAJAN'end",
                       'TestWorld.strategic=false', 'TestWorld.busy=true'):
            with self.subTest(change=change):
                self.setUp(); self.execute(change); self.c.RunNow()
                self.assertEqual(len(self.w.cityRequests), 0)
                self.assertEqual(len(self.w.unitRequests), 0)


if __name__ == '__main__':
    unittest.main()
