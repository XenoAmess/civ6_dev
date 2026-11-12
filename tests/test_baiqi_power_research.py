"""Renewable unlock research uses the existing path/pending protocol."""
from pathlib import Path
import os
import unittest
import test_baiqi_flood as flood


class PowerResearchTests(unittest.TestCase):
    def setUp(self):
        f=flood.FloodResearchTests(methodName='runTest');f.setUp()
        self.lua,self.w,self.a=f.lua,f.w,f.a
        self.lua.execute('''
local w=TestAdmin;TestFlood.flooded=false
w.power={free=6,required=8,fuel=0,can={[70]=true,[71]=false,[72]=false,[73]=false},owned={},costs={[70]=100,[71]=120,[72]=140,[73]=160}}
local p=Players[7];p.GetResources=function()return {GetResourceAmount=function()return w.power.fuel end}end
for _,c in ipairs(TestFlood.cities)do c.GetPower=function()
 if w.power.throw then error('native power unavailable')end
 return {GetFreePower=function()return w.power.free end,GetRequiredPower=function()return w.power.required end,
  IsFullyPowered=function()return true end,IsFullyPoweredByActiveProject=function()return true end}
end end
local names={'IMPROVEMENT_SOLAR_FARM','IMPROVEMENT_WIND_FARM','IMPROVEMENT_GEOTHERMAL_PLANT','IMPROVEMENT_OFFSHORE_WIND_FARM'}
GameInfo.Improvements={};local extra={};local old=GameInfo.Technologies
for i,name in ipairs(names)do
 local typ='TECH_POWER_'..i;local ix=69+i;local r={Index=ix,Hash=769+i,TechnologyType=typ}
 extra[ix]=r;extra[typ]=r;GameInfo.Improvements[name]={ImprovementType=name,PrereqTech=typ}
end
GameInfo.Technologies=setmetatable(extra,{__index=old,__call=function()return old()end})
local t=p:GetTechs();local has=t.HasTech;local can=t.CanResearch;local cost=t.GetResearchCost
t.HasTech=function(self,i)if i>=70 and i<=73 then return w.power.owned[i]==true end;return has(self,i)end
t.CanResearch=function(self,i)if i>=70 and i<=73 then return w.power.can[i]end;return can(self,i)end
t.GetResearchCost=function(self,i)if i>=70 and i<=73 then return w.power.costs[i]end;return cost(self,i)end
local oldPath=t.GetResearchPath
t.GetResearchPath=function(self,h)if h>=770 and h<=773 then if w.pathShock then w.pathShock()end;return {h-700}end;return oldPath(self,h)end
Map.GetCityPlots=function()return {GetPurchasedPlots=function()return {100}end}end
local plot={GetIndex=function()return 100 end,GetOwner=function()return TestFlood.owner end,
 GetX=function()return 8 end,GetY=function()return 3 end,
 GetImprovementType=function()return -1 end,GetDistrictType=function()return -1 end}
Map.GetPlotByIndex=function(id)if id==100 then return plot end end
ExposedMembers={BaiqiPowerSitesBridge={marker='baiqi-power-sites-v1',version=1,
 CanHave=function(pid,turn,id,city,kind)return pid==7 and turn==w.turn and id==100 and city==66 end}}
''')
        override=os.environ.get('BAIQI_POWER_RESEARCH_ADMIN')
        if override:
            self.lua.execute(Path(override).read_text(encoding='utf-8'))
            self.a=self.lua.globals().BaiqiAdmin

    def test_active_project_does_not_hide_gap_and_original_exclusive_path_is_used_once(self):
        for current in (-1,0):
            with self.subTest(current=current):
                self.setUp();self.w.tech=current;self.a.Run();self.a.Run()
                self.assertEqual(len(self.w.requests),1)
                r=self.w.requests[1];self.assertEqual((r.pid,r.op,r.params.tech[1],r.params.mode),(7,1,70,3))

    def test_positive_unknown_and_invalid_current_progress_is_preserved(self):
        for value in (1,None,-1,float('inf'),float('nan')):
            with self.subTest(value=value):
                self.setUp();self.w.progress=value;self.a.Run();self.assertEqual(len(self.w.requests),0)

    def test_unknown_no_gap_fuel_or_illegal_goal_keeps_current_research(self):
        for change in ('w.power.free=8','w.power.free=nil','w.power.required=0/0',
                       'w.power.throw=true','w.power.fuel=1','w.power.fuel=nil',
                       'w.power.can[70]=false','w.power.can[70]=nil','w.power.owned[70]=true',
                       'TestFlood.owner=8','TestFlood.visible=false',
                       'w.power.costs[70]=nil','w.power.costs[70]=0',
                       'w.power.costs[70]=math.huge','w.power.costs[70]=0/0',
                       'GameInfo.Technologies.TECH_POWER_1.Hash=math.huge'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute('local w=TestAdmin;'+change)
                self.a.Run();self.assertEqual(len(self.w.requests),0)

    def test_idle_without_qualified_power_goal_preserves_ordinary_fallback(self):
        self.w.tech=-1;self.lua.execute('TestAdmin.power.fuel=nil');self.a.Run()
        self.assertEqual(self.w.requests[1].params.tech[1],100)

    def test_current_metadata_and_actual_cost_choose_goal_without_fixed_tech_names(self):
        self.lua.execute("GameInfo.Improvements.IMPROVEMENT_SOLAR_FARM.PrereqTech='TECH_POWER_2';TestAdmin.power.can[71]=true")
        self.a.Run();self.assertEqual(len(self.w.requests),1);self.assertEqual(self.w.requests[1].params.tech[1],71)
        self.setUp();self.lua.execute('TestAdmin.power.can[71]=true;TestAdmin.power.costs[71]=50')
        self.a.Run();self.assertEqual(len(self.w.requests),1);self.assertEqual(self.w.requests[1].params.tech[1],71)

    def test_city_iteration_without_any_demand_is_bounded(self):
        self.lua.execute('''local w=TestAdmin;w.can=false;w.power.free=8;w.visits=0;local c=TestFlood.cities[1]
Players[7].GetCities=function()return {FindID=function()return c end,Members=function()return function()w.visits=w.visits+1;return w.visits,c end end}end''')
        self.a.Run();self.assertEqual(len(self.w.requests),0);self.assertEqual(self.w.visits,257)

    def test_emergency_flood_research_has_priority_over_renewables(self):
        self.lua.execute('TestFlood.flooded=true');self.a.Run()
        self.assertEqual(len(self.w.requests),1);self.assertEqual(self.w.requests[1].params.tech[1],555)

    def test_last_read_rejects_demand_fuel_ownership_metadata_turn_or_progress_drift(self):
        for change in ('TestAdmin.power.free=8','TestAdmin.power.fuel=1',
                       'TestAdmin.power.can[70]=false','TestFlood.owner=8','TestFlood.visible=false',
                       'GameInfo.Technologies.TECH_POWER_1.Hash=999',
                       'TestAdmin.turn=2','TestAdmin.progress=1','TestAdmin.tech=1',
                       'UI.IsGameCoreBusy=function()return true end'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute('TestAdmin.pathShock=function()'+change+' end')
                self.a.Run();self.assertEqual(len(self.w.requests),0)

    def test_unknown_writer_outcome_survives_turns_without_replay(self):
        for throws in (False,True):
            with self.subTest(throws=throws):
                self.setUp();self.w.throwWriter=throws;self.a.Run();self.w.throwWriter=False
                self.w.turn=2;self.a.Run();self.a.Run();self.assertEqual(len(self.w.requests),1)

    def test_observed_current_goal_is_not_reissued_and_later_idle_can_fallback(self):
        self.a.Run();self.w.tech=70;self.a.Run();self.assertEqual(len(self.w.requests),1)
        self.lua.execute('TestAdmin.power.owned[70]=true;TestAdmin.tech=-1;TestAdmin.turn=2')
        self.a.Run();self.assertEqual(len(self.w.requests),2);self.assertEqual(self.w.requests[2].params.tech[1],100)


if __name__=='__main__':unittest.main()
