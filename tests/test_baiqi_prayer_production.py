"""Normal production goals never grant Prophet points or spend currency."""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class PrayerProductionTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('mock_world','mock_first_holy_site','mock_prayer_production'):
            self.lua.execute((ROOT/f'tests/lua/{name}.lua').read_text(encoding='utf-8'))
        for name in ('BaiqiConfig','BaiqiPolicy','BaiqiPlanner'):
            self.lua.execute((ROOT/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        source = Path(os.environ.get('BAIQI_PRAYER_CONTROLLER') or ROOT/'mod/Baiqi/Lua/BaiqiController.lua')
        self.lua.execute(source.read_text(encoding='utf-8'))
        self.w = self.lua.globals().TestWorld
        self.c = self.lua.globals().BaiqiController

    def chosen(self):
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests),1)
        self.assertEqual(len(self.w.unitRequests),0)
        params=self.w.cityRequests[1].params
        return params[5] or params[3] or params[2] or params[4]

    def change(self,code):
        self.lua.execute(code)

    def test_completed_holy_site_and_unrecruitable_unclaimed_prophet_choose_prayer(self):
        self.assertEqual(self.chosen(),910)

    def test_valid_zero_project_class_and_individual_indices_are_accepted(self):
        self.assertEqual(self.w.prayerDefinition.Index,0)
        self.assertEqual(self.chosen(),910)

    def test_missing_pillaged_or_unknown_holy_site_has_no_bonus(self):
        for change,expected in (('TestWorld.completed[66]=false;TestWorld.completed[67]=false',777),
                                ('TestWorld.holyPillaged=true',901),('TestWorld.holyPillaged=nil',901)):
            with self.subTest(change=change):
                self.setUp();self.change(change);self.assertEqual(self.chosen(),expected)

    def test_religion_capacity_or_owned_prophet_does_not_need_prayers(self):
        for key,value in (('created',0),('earned',1),('held',True)):
            with self.subTest(key=key):
                self.setUp();self.w[key]=value;self.assertEqual(self.chosen(),901)

    def test_direct_recruitment_and_unknown_recruitability_keep_normal_ranking(self):
        for value in (True,None,'unknown'):
            with self.subTest(value=value):
                self.setUp();self.w.canRecruit=value;self.assertEqual(self.chosen(),901)

    def test_claimant_zero_and_exhausted_public_pool_do_not_boost(self):
        for code in ('TestWorld.timeline[1].Claimant=0','TestWorld.timeline={}'): # No public unclaimed candidate.
            with self.subTest(code=code):
                self.setUp();self.change(code);self.assertEqual(self.chosen(),901)

    def test_malformed_or_ambiguous_timeline_keeps_ordinary_production(self):
        for code in ('TestWorld.timeline[3]={Class=1}', 'TestWorld.timeline.extra=true',
                     'TestWorld.timeline[2]={Class=0,Individual=0,Claimant=0}',
                     'TestWorld.timeline[1].Claimant=false',
                     'GameInfo.GreatPersonIndividuals[0].Index=1'):
            with self.subTest(code=code):
                self.setUp();self.change(code);self.assertEqual(self.chosen(),901)

    def test_native_exceptions_cannot_stop_ordinary_building_choice(self):
        for key in ('throwTimeline','throwRecruit','throwReligion'):
            with self.subTest(key=key):
                self.setUp();self.w[key]=True;self.assertEqual(self.chosen(),901)

    def test_another_city_current_or_entire_queue_suppresses_bonus(self):
        for code in ('TestWorld.current[67]=910','TestWorld.queues[67]={{ProjectType=0}}',
                     "TestWorld.queues[67]={{ProjectType='PROJECT_ENHANCE_DISTRICT_HOLY_SITE'}}",
                     'TestWorld.queues[67]={{BuildingType=9},{ProjectType=0}}'):
            with self.subTest(code=code):
                self.setUp();self.change(code);self.assertEqual(self.chosen(),901)

    def test_unknown_project_queue_definition_is_not_empty(self):
        self.change('TestWorld.queues[67]={{ProjectType=999}}')
        self.assertEqual(self.chosen(),901)

    def test_wrong_or_missing_prerequisite_definition_does_not_boost(self):
        for code in ("TestWorld.prayerDefinition.PrereqDistrict='WRONG'",
                     'TestWorld.prayerDefinition.Index=math.huge',
                     'GameInfo.GreatPersonClasses.GREAT_PERSON_CLASS_PROPHET=nil'):
            with self.subTest(code=code):
                self.setUp();self.change(code);self.assertEqual(self.chosen(),901)

    def test_existing_queue_is_preserved(self):
        self.change('TestWorld.queues[66]={{BuildingType=9}}')
        self.assertEqual(self.chosen(),910)
        self.assertEqual(self.w.cityRequests[1].city,67)
        self.assertEqual(len(self.w.queues[66]),1)

    def test_granary_monument_and_builder_priorities_remain_higher(self):
        for value in (100,101,202):
            with self.subTest(value=value):
                self.setUp();self.w.allowed[value]=True
                if value==202:
                    self.change('TestWorld.objects.player.GetTreasury=function()return {GetGoldBalance=function()return 1000 end,GetGoldYield=function()return 100 end,GetTotalMaintenance=function()return 0 end}end')
                self.assertEqual(self.chosen(),value)

    def test_repairs_still_rank_above_prayers(self):
        self.change('TestWorld.cities[1].GetBuildings=function()return {IsPillaged=function(_,index)return index==9 end}end')
        self.assertEqual(self.chosen(),901)

    def test_candidate_is_entered_before_ordinary_scan_budget_is_exhausted(self):
        self.change('''
GameInfo.Buildings=setmetatable({}, {__call=function()
 local i=0;return function()i=i+1;if i<=512 then return {Hash=2000+i,Index=2000+i,BuildingType='INELIGIBLE_'..i,Maintenance=0}end end
end})
''')
        self.assertEqual(self.chosen(),910)

    def test_known_unneeded_goal_keeps_ordinary_project_production(self):
        self.w.created=0
        self.change('TestWorld.allowed={[910]=true}')
        self.assertEqual(self.chosen(),910)

    def test_standby_keeps_its_negative_score(self):
        self.w.created=0
        self.change('TestWorld.allowed={[910]=true,[911]=true}')
        self.assertEqual(self.chosen(),910)

    def test_native_two_mode_and_operation_rejections_remain_authoritative(self):
        for key in ('nativeDisallow','noPrayerOperation'):
            with self.subTest(key=key):
                self.setUp()
                if key=='nativeDisallow':self.w.allowed[910]=False
                else:self.w[key]=True
                self.assertEqual(self.chosen(),901)

    def test_final_goal_changes_stop_prayer_and_replan_same_turn(self):
        for change in ('w.canRecruit=true','w.canRecruit=nil','w.created=0','w.earned=1',
                       'w.held=true','w.holyPillaged=true','w.completed[66]=false',
                       'w.queues[67]={{ProjectType=0}}','w.current[67]=910'):
            with self.subTest(change=change):
                self.setUp()
                self.change('TestWorld.queues[67]={{BuildingType=9}};TestWorld.prayerShock=function()local w=TestWorld;'+change+' end')
                self.c.RunNow();self.assertEqual(len(self.w.cityRequests),0)
                self.assertEqual(self.chosen(),901)

    def test_final_queue_change_is_preserved(self):
        self.change('''
TestWorld.queues[67]={{BuildingType=9}}
TestWorld.prayerShock=function()TestWorld.queues[66]={{BuildingType=9},{BuildingType=1}}end
''')
        self.c.RunNow();self.assertEqual(len(self.w.cityRequests),0)
        self.assertEqual(len(self.w.queues[66]),2)

    def test_qualification_lost_during_demand_check_is_read_again(self):
        self.change('TestWorld.queues[67]={{BuildingType=9}};TestWorld.prayerShock=function()TestWorld.allowed[910]=false end')
        self.c.RunNow();self.assertEqual(len(self.w.cityRequests),0)

    def test_second_city_does_not_duplicate_the_pending_goal(self):
        self.assertEqual(self.chosen(),910)
        self.c.RunNow();self.assertEqual(len(self.w.cityRequests),2)
        self.assertEqual(self.w.cityRequests[2].params[2],901)

    def test_unobserved_project_request_survives_timeout_and_new_turn(self):
        self.assertEqual(self.chosen(),910)
        self.c.Update(3);self.w.turn=2;self.c.RunNow();self.c.RunNow()
        self.assertEqual(sum(self.w.cityRequests[i].params[5]==910 for i in range(1,len(self.w.cityRequests)+1)),1)

    def test_unrelated_native_head_does_not_discard_unknown_project(self):
        self.assertEqual(self.chosen(),910)
        self.w.current[66]=901
        self.c.Update(3);self.w.turn=2;self.c.RunNow();self.c.RunNow()
        self.assertEqual(sum(self.w.cityRequests[i].params[5]==910 for i in range(1,len(self.w.cityRequests)+1)),1)

    def test_unknown_writer_result_cannot_be_replayed(self):
        self.w.throwWriter=True;self.c.RunNow();self.w.throwWriter=False
        self.c.Update(3);self.w.turn=2;self.c.RunNow();self.c.RunNow()
        self.assertEqual(sum(self.w.cityRequests[i].params[5]==910 for i in range(1,len(self.w.cityRequests)+1)),1)

    def test_observed_native_project_still_blocks_other_boost(self):
        self.assertEqual(self.chosen(),910)
        self.w.current[66]=910
        self.c.RunNow();self.assertEqual(len(self.w.cityRequests),2)
        self.assertEqual(self.w.cityRequests[2].params[2],901)


if __name__=='__main__':
    unittest.main()
