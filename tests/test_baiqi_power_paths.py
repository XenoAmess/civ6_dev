"""Run the real admin consumer through site-aware actual prerequisite paths."""
from pathlib import Path
import os
import unittest
import test_baiqi_power_research as base

class PowerPathTests(unittest.TestCase):
    def setUp(self):
        f=base.PowerResearchTests(methodName='runTest');f.setUp();self.lua,self.w,self.a=f.lua,f.w,f.a
        self.lua.execute('''
local w=TestAdmin;w.routeOwned={[59]=true};w.routeCan={};w.routeProgress={};w.routeCosts={};w.routeRows={};w.bridgeCalls=0
local defs={{54,-2122571700,'TECH_PLASTICS',592},{57,1915613645,'TECH_SYNTHETIC_MATERIALS',664},
 {59,2138319163,'TECH_SATELLITES',740},{62,-1574004523,'TECH_COMPOSITES',740},
 {56,840424027,'TECH_NUCLEAR_FISSION',664},{61,611924100,'TECH_LASERS',740},
 {66,1514828631,'TECH_NUCLEAR_FUSION',862},{72,-96279613,'TECH_CYBERNETICS',1100},
 {74,1049470971,'TECH_PREDICTIVE_SYSTEMS',1150}}
for _,d in ipairs(defs)do local r={Index=d[1],Hash=d[2],TechnologyType=d[3]}
 GameInfo.Technologies[d[1]]=r;GameInfo.Technologies[d[3]]=r;w.routeRows[d[1]]=r
 w.routeCan[d[1]]=false;w.routeProgress[d[1]]=0;w.routeCosts[d[1]]=d[4]end
w.routeCan[54]=true;w.routeCan[56]=true
local names={'IMPROVEMENT_SOLAR_FARM','IMPROVEMENT_WIND_FARM','IMPROVEMENT_GEOTHERMAL_PLANT','IMPROVEMENT_OFFSHORE_WIND_FARM'}
local goals={59,62,57,74};for i,k in ipairs(names)do GameInfo.Improvements[k].PrereqTech=w.routeRows[goals[i]].TechnologyType end
w.paths={[-1574004523]={54,57,62},[1915613645]={54,57},[1049470971]={56,61,66,72,74},[840424027]={56},[-2122571700]={54}}
local t=Players[7]:GetTechs();local oldHas,oldCan,oldProgress,oldCost,oldPath=t.HasTech,t.CanResearch,t.GetResearchProgress,t.GetResearchCost,t.GetResearchPath
t.HasTech=function(self,i)if w.routeRows[i]then return w.routeOwned[i]==true end;return oldHas(self,i)end
t.CanResearch=function(self,i)if w.routeRows[i]then return w.routeCan[i]end;return oldCan(self,i)end
t.GetResearchProgress=function(self,i)if i==w.tech then return w.progress end;if w.routeRows[i]then return w.routeProgress[i]end;return oldProgress(self,i)end
t.GetResearchCost=function(self,i)if w.routeRows[i]then return w.routeCosts[i]end;return oldCost(self,i)end
t.GetResearchPath=function(self,h)if w.pathShock then w.pathShock(h)end;if w.paths[h]then return w.paths[h]end;return oldPath(self,h)end
w.siteImprovement=-1;w.siteDistrict=-1;w.siteOwner=7;w.siteX=8
local plot={GetIndex=function()return 100 end,GetOwner=function()return w.siteOwner end,
 GetX=function()return w.siteX end,GetY=function()return 3 end,
 GetImprovementType=function()return w.siteImprovement end,GetDistrictType=function()return w.siteDistrict end}
Map.GetPlotByIndex=function(id)if id==100 then return plot end end
ExposedMembers.BaiqiPowerSitesBridge.CanHave=function(pid,turn,id,city,kind)
 w.bridgeCalls=w.bridgeCalls+1
 assert(pid==7 and turn==w.turn and id==100 and city==66)
 if w.bridgeThrow then error('Core read unavailable')end
 if w.bridgeUnknown then return nil end
 return kind==(w.suitableKind or 'IMPROVEMENT_OFFSHORE_WIND_FARM') and not w.bridgeFalse
end
''')
        override=os.environ.get('BAIQI_POWER_PATH_ADMIN')
        if override:
            self.lua.execute(Path(override).read_text(encoding='utf-8'));self.a=self.lua.globals().BaiqiAdmin

    def change(self,text):self.lua.execute('local w=TestAdmin;'+text)

    def test_locked_offshore_goal_selects_only_first_actual_researchable_step_once(self):
        self.a.Run();self.a.Run();self.assertEqual(len(self.w.requests),1)
        r=self.w.requests[1];self.assertEqual((r.params.tech[1],len(r.params.tech),r.params.mode),(56,1,3))
        self.assertGreater(self.w.bridgeCalls,0)

    def test_positive_and_unknown_current_progress_remain_untouched(self):
        for progress in (533.61328125,None,-1,float('nan')):
            with self.subTest(progress=progress):
                self.setUp();self.w.tech=54;self.w.progress=progress;self.a.Run()
                self.assertEqual(len(self.w.requests),0);self.assertEqual(self.w.bridgeCalls,0)

    def test_idle_or_exact_zero_progress_can_choose_offshore_prerequisite(self):
        for index in (-1,54):
            with self.subTest(index=index):
                self.setUp();self.w.tech=index;self.w.progress=0;self.a.Run()
                self.assertEqual(len(self.w.requests),1)
                self.assertEqual(self.w.requests[1].params.tech[1],56)

    def test_missing_foreign_false_unknown_or_throwing_bridge_keeps_zero_progress_current(self):
        for change in ('ExposedMembers=nil','ExposedMembers.BaiqiPowerSitesBridge=nil',
                       'ExposedMembers.BaiqiPowerSitesBridge.marker="foreign"','w.bridgeFalse=true',
                       'w.bridgeUnknown=true','w.bridgeThrow=true'):
            with self.subTest(change=change):
                self.setUp();self.change(change);self.a.Run();self.assertEqual(len(self.w.requests),0)

    def test_empty_visible_owned_site_is_required_and_actual_purchase_bridge_can_reject(self):
        for change in ('w.siteImprovement=1','w.siteDistrict=2','w.siteOwner=8','TestFlood.visible=false',
                       'Map.GetCityPlots=function()return {GetPurchasedPlots=function()return {}end}end',
                       'ExposedMembers.BaiqiPowerSitesBridge.CanHave=function()return false end'):
            with self.subTest(change=change):
                self.setUp();self.change(change);self.a.Run();self.assertEqual(len(self.w.requests),0)

    def test_malformed_sparse_duplicate_wrong_goal_unknown_and_oversized_paths_reject(self):
        for value in ('{[1]=56,[3]=74}','{56,61,66,72,74,74}','{56,61,66,72}',
                      '{56,true,74}','{56,999,74}','{}','false'):
            with self.subTest(value=value):
                self.setUp();self.change('w.paths[1049470971]='+value);self.a.Run();self.assertEqual(len(self.w.requests),0)
        self.setUp();self.change('local p={};for i=1,129 do p[i]=56 end;p[129]=74;w.paths[1049470971]=p')
        self.a.Run();self.assertEqual(len(self.w.requests),0)

    def test_blocked_first_unowned_step_cannot_skip_to_later_researchable_node(self):
        self.change('w.routeCan[56]=false;w.routeCan[61]=true');self.a.Run();self.assertEqual(len(self.w.requests),0)

    def test_submitted_next_step_path_cannot_smuggle_another_or_future_tech(self):
        for value in ('{61}','{56,61}','{[2]=56}','{wrong=56}'):
            with self.subTest(value=value):
                self.setUp();self.change('w.paths[840424027]='+value);self.a.Run();self.assertEqual(len(self.w.requests),0)

    def test_owned_prefix_uses_next_step_and_remaining_path_ranking(self):
        self.change('w.routeOwned[56]=true;w.routeCan[61]=true;w.paths[611924100]={61}')
        self.a.Run();self.assertEqual(self.w.requests[1].params.tech[1],61)
        self.setUp();self.change("w.suitableKind='IMPROVEMENT_GEOTHERMAL_PLANT'")
        self.a.Run();self.assertEqual(self.w.requests[1].params.tech[1],54)

    def test_final_actual_path_site_and_bridge_identity_changes_block_writer(self):
        for change in ('w.routeCosts[61]=741','w.paths[1049470971]={56,66,61,72,74}',
                       'w.siteImprovement=1','w.siteOwner=8','w.siteX=9','w.power.fuel=1',
                       'ExposedMembers.BaiqiPowerSitesBridge.CanHave=function()return true end'):
            with self.subTest(change=change):
                self.setUp();self.change('w.pathShock=function(h)if h==840424027 then '+change+' end end')
                self.a.Run();self.assertEqual(len(self.w.requests),0)

    def test_unknown_writer_is_pending_across_turn_and_observation_allows_later_step(self):
        for throws in (False,True):
            with self.subTest(throws=throws):
                self.setUp();self.w.throwWriter=throws;self.a.Run();self.w.throwWriter=False
                self.w.turn=2;self.a.Run();self.a.Run();self.assertEqual(len(self.w.requests),1)
                self.w.tech=56;self.a.Run();self.assertEqual(len(self.w.requests),1)
                self.change('w.routeOwned[56]=true;w.routeCan[61]=true;w.paths[611924100]={61};w.tech=-1;w.turn=3')
                self.a.Run();self.assertEqual(len(self.w.requests),2);self.assertEqual(self.w.requests[2].params.tech[1],61)

    def test_flood_emergency_still_wins(self):
        self.change('TestFlood.flooded=true');self.a.Run()
        self.assertEqual(self.w.requests[1].params.tech[1],555);self.assertEqual(self.w.bridgeCalls,0)

    def test_raw_plot_scan_bound_is_shared_across_goals(self):
        self.change('w.plotReads=0;Map.GetCityPlots=function()local t={};for i=1,129 do t[i]=100 end;return {GetPurchasedPlots=function()return t end}end;local old=Map.GetPlotByIndex;Map.GetPlotByIndex=function(i)w.plotReads=w.plotReads+1;return old(i)end')
        self.a.Run();self.assertEqual(len(self.w.requests),0);self.assertEqual(self.w.plotReads,128)

    def test_later_demand_city_with_site_is_considered(self):
        self.change('''local first=TestFlood.cities[1];local second={GetID=function()return 67 end,
GetOwner=first.GetOwner,GetX=function()return 20 end,GetY=function()return 3 end,GetPower=first.GetPower}
Players[7].GetCities=function()return {Members=function()return ipairs({first,second})end,
 FindID=function(_,id)if id==66 then return first elseif id==67 then return second end end}end
Map.GetCityPlots=function()return {GetPurchasedPlots=function(_,c)if c:GetID()==67 then return {100}end;return {}end}end
ExposedMembers.BaiqiPowerSitesBridge.CanHave=function(pid,turn,id,city,kind)return city==67 and kind=='IMPROVEMENT_OFFSHORE_WIND_FARM'end''')
        self.a.Run();self.assertEqual(len(self.w.requests),1);self.assertEqual(self.w.requests[1].params.tech[1],56)

if __name__=='__main__':unittest.main()
