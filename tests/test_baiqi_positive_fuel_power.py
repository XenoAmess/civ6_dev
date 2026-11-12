"""Positive reserves must not hide a city's observed shortage or project dependency."""
from pathlib import Path
import os
import unittest
import test_baiqi_power_paths as paths
import test_baiqi_power_project as projects


class PositiveFuelResearchTests(unittest.TestCase):
    def setUp(self):
        f=paths.PowerPathTests(methodName='runTest');f.setUp();self.lua,self.w,self.a=f.lua,f.w,f.a
        self.change('''w.routeOwned[56]=true;w.routeCan[61]=true;w.paths[611924100]={61};w.tech=57
Players[7].GetResources=function()return {GetResourceAmount=function(_,kind)if kind=='RESOURCE_COAL'then return 2 end;return 0 end}end''')
        override=os.environ.get('BAIQI_POSITIVE_FUEL_ADMIN')
        if override:
            self.lua.execute(Path(override).read_text(encoding='utf-8'));self.a=self.lua.globals().BaiqiAdmin

    def change(self,s):self.lua.execute('local w=TestAdmin;'+s)

    def test_coal2_and_project_dependency_continue_to_actual_next_laser_step(self):
        self.a.Run();self.a.Run();self.assertEqual(len(self.w.requests),1)
        self.assertEqual(self.w.requests[1].params.tech[1],61)

    def test_actually_unpowered_city_can_research_with_positive_reserves(self):
        self.change('w.power.full=false;w.power.project=false');self.a.Run()
        self.assertEqual(len(self.w.requests),1);self.assertEqual(self.w.requests[1].params.tech[1],61)

    def test_fuel_powered_city_unknown_flags_or_no_gap_preserve_current(self):
        for change in ('w.power.full=true;w.power.project=false','w.power.full=nil',
                       'w.power.full=false;w.power.project=nil','w.power.project=0',
                       'w.power.free=8','w.power.free=-1'):
            with self.subTest(change=change):
                self.setUp();self.change(change);self.a.Run();self.assertEqual(len(self.w.requests),0)

    def test_any_fuel_unknown_negative_or_nonfinite_blocks_proposal(self):
        for value in ('nil','-1','math.huge','0/0','true'):
            for kind in ('RESOURCE_COAL','RESOURCE_OIL','RESOURCE_URANIUM'):
                with self.subTest(value=value,kind=kind):
                    self.setUp();self.change("Players[7].GetResources=function()return {GetResourceAmount=function(_,kind)if kind=='"+kind+"'then return "+value+" end;return 2 end}end")
                    self.a.Run();self.assertEqual(len(self.w.requests),0)

    def test_last_power_phase_or_fuel_validity_change_blocks_submission(self):
        for change in ('w.power.project=false','w.power.full=nil','w.power.project=nil',
                       "Players[7].GetResources=function()return {GetResourceAmount=function()return math.huge end}end"):
            with self.subTest(change=change):
                self.setUp();self.change('w.pathShock=function(h)if h==611924100 then '+change+' end end')
                self.a.Run();self.assertEqual(len(self.w.requests),0)

    def test_positive_current_progress_and_unknown_writer_keep_original_protocol(self):
        self.w.progress=1;self.a.Run();self.assertEqual(len(self.w.requests),0)
        self.setUp();self.w.throwWriter=True;self.a.Run();self.w.throwWriter=False
        self.w.turn=2;self.a.Run();self.a.Run();self.assertEqual(len(self.w.requests),1)

    def test_real_powered_first_city_does_not_hide_later_project_dependent_city(self):
        self.change('''local first=TestFlood.cities[1];local originalPower=first.GetPower
local second={GetID=function()return 67 end,GetOwner=first.GetOwner,GetX=function()return 20 end,
 GetY=function()return 3 end,GetPower=originalPower}
first.GetPower=function()return {GetFreePower=function()return 6 end,GetRequiredPower=function()return 9 end,
 IsFullyPowered=function()return true end,IsFullyPoweredByActiveProject=function()return false end}end
Players[7].GetCities=function()return {Members=function()return ipairs({first,second})end,
 FindID=function(_,id)if id==66 then return first elseif id==67 then return second end end}end
Map.GetCityPlots=function()return {GetPurchasedPlots=function(_,c)if c:GetID()==67 then return {100}end;return {}end}end
ExposedMembers.BaiqiPowerSitesBridge.CanHave=function(pid,turn,id,city,kind)return city==67 and kind=='IMPROVEMENT_OFFSHORE_WIND_FARM'end''')
        self.a.Run();self.assertEqual(len(self.w.requests),1);self.assertEqual(self.w.requests[1].params.tech[1],61)


class PositiveFuelProjectTests(unittest.TestCase):
    def setUp(self):
        f=projects.PowerProjectTests(methodName='runTest');f.setUp();self.case=f.case
        override=os.environ.get('BAIQI_POSITIVE_FUEL_PLANNER')
        if override:self.case.lua.execute(Path(override).read_text(encoding='utf-8'))

    def test_positive_coal_oil_or_uranium_does_not_remove_actual_unpowered_project_hint(self):
        for kind in ('RESOURCE_COAL','RESOURCE_OIL','RESOURCE_URANIUM'):
            with self.subTest(kind=kind):
                self.setUp();self.case.change('TestWorld.fuel.'+kind+'=2');self.assertEqual(self.case.chosen(),927)

    def test_positive_fuel_arriving_during_final_check_remains_known_and_eligible(self):
        self.case.change('TestWorld.queues[67]={{BuildingType=9}};TestWorld.powerShock=function()TestWorld.fuel.RESOURCE_COAL=2 end')
        self.case.c.RunNow();self.assertEqual(len(self.case.w.cityRequests),1)
        self.assertEqual(self.case.w.cityRequests[1].params[5],927)

    def test_positive_fuel_does_not_cancel_existing_queue_or_repeat_unknown_write(self):
        self.case.change('TestWorld.fuel.RESOURCE_COAL=2;TestWorld.queues[66]={{ProjectType=2}};TestWorld.queues[67]={{BuildingType=9}}')
        self.case.c.RunNow();self.assertEqual(len(self.case.w.cityRequests),0);self.assertEqual(self.case.w.powerReads,0)
        self.setUp();self.case.change('TestWorld.fuel.RESOURCE_COAL=2');self.case.w.throwWriter=True
        self.case.c.RunNow();self.case.w.throwWriter=False;self.case.w.turn=2;self.case.c.Update(3);self.case.c.RunNow()
        self.assertEqual(sum(self.case.w.cityRequests[i].params[5]==927 for i in range(1,len(self.case.w.cityRequests)+1)),1)


if __name__=='__main__':unittest.main()
