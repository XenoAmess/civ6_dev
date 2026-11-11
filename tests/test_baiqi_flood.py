"""Native flood demand, original research requests and actual city writer gates."""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime
import test_baiqi_power_project as power

ROOT=Path(__file__).resolve().parents[1]
def load(lua,path):lua.execute((ROOT/path).read_text(encoding='utf-8'))
def module(lua,name):load(lua,f'mod/Baiqi/Lua/{name}.lua')

class FloodDemandTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        load(self.lua,'tests/lua/mock_world.lua');load(self.lua,'tests/lua/mock_flood.lua')
        self.lua.execute('InstallFlood(nil,7)');module(self.lua,'BaiqiFlood')
        self.w=self.lua.globals().TestFlood
    def read(self):return self.lua.eval('BaiqiFlood.City({Game=Game,Players=Players,GameInfo=GameInfo,Map=Map,PlayersVisibility=PlayersVisibility,TerrainManager=TerrainManager},7,66,1)')
    def test_native_flooded_intact_and_no_demand_states(self):
        self.assertIs(self.read(),True)
        for change in ('TestFlood.has=true','TestFlood.pillaged=false','TestFlood.complete=false',
                       'TestFlood.low=-1','TestFlood.flooded=false','TestFlood.submerged=true','TestFlood.count=0'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.assertIs(self.read(),False)
    def test_all_native_lowlands_including_zero_and_pillaged_barrier(self):
        for low in (0,1,2):
            self.w.low=low;self.w.has=True;self.w.barrierPillaged=True;self.assertIs(self.read(),True)
    def test_unknown_and_exceptions_never_become_known_false(self):
        for change in ('TestFlood.has=nil','TestFlood.barrierPillaged=nil','TestFlood.complete=nil',
                       'TestFlood.pillaged=nil','TestFlood.low=nil','TestFlood.low=0/0','TestFlood.low=math.huge',
                       'TestFlood.low=3','TestFlood.flooded=nil','TestFlood.submerged=nil','TestFlood.throwTerrain=true',
                       'TerrainManager=nil','TestFlood.has=false;TestFlood.barrierPillaged=true'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.assertIsNone(self.read())
    def test_metadata_identity_and_visibility_reject_before_terrain(self):
        for change in ('TestFlood.owner=8','TestFlood.visible=false','TestFlood.revealed=false',
                       "TestFlood.definition.PrereqTech=''",'TestFlood.definition.Hash=math.huge',
                       'TestFlood.definition.Index=nil','Players[7].GetCities=function()return {FindID=function()return nil end}end',
                       'Map.GetPlot=function()return {GetX=function()return 99 end,GetY=function()return 3 end,GetOwner=function()return 7 end}end'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.assertIsNone(self.read());self.assertEqual(self.w.terrainReads,0)
    def test_iteration_is_bounded_and_final_turn_owner_or_barrier_change_matters(self):
        for change,expected in (('TestFlood.count=65',None),('TestFlood.shock=function()TestWorld.turn=2 end',None),
                                ('TestFlood.shock=function()TestFlood.owner=8 end',None),
                                ('TestFlood.shock=function()TestFlood.has=true end',False)):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.assertIs(self.read(),expected)
    def test_known_intact_barrier_false_still_checks_final_turn(self):
        self.lua.execute('TestFlood.has=true;local f=TestFlood.cities[1].GetBuildings;local n=0;TestFlood.cities[1].GetBuildings=function(c)n=n+1;if n==2 then TestWorld.turn=2 end;return f(c)end')
        self.assertIsNone(self.read())

class FloodResearchTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        load(self.lua,'tests/lua/mock_admin.lua');load(self.lua,'tests/lua/mock_flood.lua')
        self.lua.execute('''InstallFlood(nil,7);local w=TestAdmin;w.tech=0;w.civic=0;w.policyChanged=true;w.progress=0;w.owned=false;w.can=true
local old=GameInfo.Technologies;local r={Index=55,Hash=555,TechnologyType='TECH_COMPUTERS'}
GameInfo.Technologies=setmetatable({TECH_COMPUTERS=r,[55]=r},{__index=old,__call=function()return old()end})
local t=Players[7]:GetTechs();t.GetResearchProgress=function()if w.progressShock then w.progressShock()end;return w.progress end
t.HasTech=function(_,i)if i==55 then return w.owned end;return false end
t.CanResearch=function(_,i)if i==55 then return w.can end;return true end
t.GetResearchPath=function(_,h)if w.pathShock then w.pathShock()end;return {h}end
local send=UI.RequestPlayerOperation;UI.RequestPlayerOperation=function(...)
 send(...);if w.throwWriter then error('unknown after native dispatch')end end
''')
        module(self.lua,'BaiqiConfig');module(self.lua,'BaiqiFlood')
        override=os.environ.get('BAIQI_FLOOD_ADMIN')
        if override:self.lua.execute(Path(override).read_text(encoding='utf-8'))
        else:module(self.lua,'BaiqiAdmin')
        self.w=self.lua.globals().TestAdmin;self.a=self.lua.globals().BaiqiAdmin
    def test_idle_or_zero_progress_research_uses_original_path_and_exclusive_operation(self):
        for current in (-1,0):
            self.setUp();self.w.tech=current;self.a.Run();self.a.Run()
            self.assertEqual(len(self.w.requests),1);r=self.w.requests[1]
            self.assertEqual((r.pid,r.op,r.params.tech[1],r.params.mode),(7,1,555,3))
    def test_positive_unknown_and_nonzero_progress_are_preserved(self):
        for value in (1,None,-1,float('inf')):
            with self.subTest(value=value):
                self.setUp();self.w.progress=value;self.a.Run();self.assertEqual(len(self.w.requests),0)
    def test_unknown_flood_unavailable_technology_and_existing_target_keep_research(self):
        for change in ('TestFlood.flooded=false','TestFlood.flooded=nil','TestAdmin.owned=true',
                       'TestAdmin.can=false','TestAdmin.can=nil','TestAdmin.tech=55','TerrainManager=nil'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.a.Run();self.assertEqual(len(self.w.requests),0)
    def test_idle_unknown_flood_falls_back_to_existing_ordinary_research(self):
        self.w.tech=-1;self.lua.execute('TestFlood.flooded=nil');self.a.Run()
        self.assertEqual(self.w.requests[1].params.tech[1],100)
    def test_pending_request_and_throw_after_dispatch_never_replay_next_turn(self):
        for throws in (False,True):
            with self.subTest(throws=throws):
                self.setUp();self.w.throwWriter=throws;self.a.Run();self.w.throwWriter=False
                self.w.turn=2;self.a.Run();self.a.Run();self.assertEqual(len(self.w.requests),1)
    def test_native_observation_releases_pending_for_later_research(self):
        self.a.Run();self.w.tech=55;self.a.Run();self.w.tech=-1;self.w.owned=True;self.w.turn=2;self.a.Run()
        self.assertEqual(len(self.w.requests),2);self.assertEqual(self.w.requests[2].params.tech[1],100)
    def test_path_read_cannot_cover_flood_progress_turn_queue_owner_or_busy_change(self):
        for change in ('TestFlood.flooded=false','TestFlood.owner=8','TestAdmin.progress=1',
                       'TestAdmin.tech=1','TestAdmin.turn=2','TestAdmin.can=false',
                       'TestAdmin.leader="OTHER"','UI.IsGameCoreBusy=function()return true end'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute('TestAdmin.pathShock=function()'+change+' end');self.a.Run()
                self.assertEqual(len(self.w.requests),0)

class FloodProductionTests(unittest.TestCase):
    def setUp(self):
        p=power.PowerProjectTests(methodName='runTest');p.setUp();self.case=p.case
        load(self.case.lua,'tests/lua/mock_flood.lua')
        self.case.change('InstallFlood(TestWorld.cities,7);TestWorld.allowed[913]=true;TestWorld.queues[67]={{BuildingType=9}}')
        module(self.case.lua,'BaiqiFlood')
        self.case.change('''local old=CityManager.CanStartOperation
CityManager.CanStartOperation=function(c,op,p,...)
 local result=old(c,op,p,...)
 if p[2]==913 then
  local n=TestWorld.qualification[913]
  if n==2 and TestWorld.floodShock then TestWorld.floodShock()end
  if n==3 and TestWorld.floodLateShock then TestWorld.floodLateShock()end
  if TestWorld.noBarrierOperation then return false end
 end;return result end''')
        override=os.environ.get('BAIQI_FLOOD_CONTROLLER')
        if override:
            self.case.lua.execute(Path(override).read_text(encoding='utf-8'));self.case.c=self.case.lua.globals().BaiqiController
    def test_emergency_barrier_beats_repeat_power_project(self):self.assertEqual(self.case.chosen(),913)
    def test_native_tech_and_operation_eligibility_are_required(self):
        for change in ('TestWorld.allowed[913]=false','TestWorld.noBarrierOperation=true',
                       'local c=TestWorld.cities[1];local f=c.GetBuildQueue;c.GetBuildQueue=function(self)local q=f(self);local can=q.CanProduce;q.CanProduce=function(o,h,m,...)if h==913 and m==true then return false end;return can(o,h,m,...)end;return q end'):
            with self.subTest(change=change):
                self.setUp();self.case.change(change);self.assertEqual(self.case.chosen(),927)
    def test_unknown_or_resolved_flood_keeps_existing_power_strategy(self):
        for change in ('TestFlood.flooded=false','TestFlood.submerged=true','TestFlood.low=nil','TestFlood.has=true'):
            with self.subTest(change=change):
                self.setUp();self.case.change(change);self.assertEqual(self.case.chosen(),927)
    def test_existing_active_queue_is_preserved_without_terrain_scan(self):
        self.case.change('TestWorld.queues[66]={{BuildingType=9}}');self.case.c.RunNow()
        self.assertEqual(len(self.case.w.cityRequests),0);self.assertEqual(self.case.lua.globals().TestFlood.terrainReads,0)
    def test_final_demand_change_replans_same_turn(self):
        self.case.change('TestWorld.floodShock=function()TestFlood.flooded=false end')
        self.case.c.RunNow();self.assertEqual(len(self.case.w.cityRequests),0);self.assertEqual(self.case.chosen(),927)
    def test_final_native_legality_read_cannot_cover_queue_turn_or_owner_change(self):
        for change in ('TestWorld.queues[66]={{BuildingType=9},{BuildingType=0}}','TestWorld.turn=2',
                       'TestWorld.cities[1].GetOwner=function()return 8 end'):
            with self.subTest(change=change):
                self.setUp();self.case.change('TestWorld.floodLateShock=function()'+change+' end')
                self.case.c.RunNow();self.assertEqual(len(self.case.w.cityRequests),0)
    def test_unconfirmed_native_writer_is_not_replayed(self):
        self.case.w.throwWriter=True;self.case.c.RunNow();self.case.w.throwWriter=False
        self.case.w.turn=2;self.case.c.Update(3);self.case.c.RunNow()
        self.assertEqual(sum(self.case.w.cityRequests[i].params[2]==913 for i in range(1,len(self.case.w.cityRequests)+1)),1)
    def test_reservation_survives_large_ordinary_scan(self):
        self.case.change("local b=TestFlood.definition;GameInfo.Buildings=setmetatable({BUILDING_FLOOD_BARRIER=b,[913]=b},{__call=function()local i=0;return function()i=i+1;if i<=512 then return {Index=i,Hash=3000+i,BuildingType='OTHER_'..i,Maintenance=0}end end end})")
        self.assertEqual(self.case.chosen(),913)
    def test_essential_granary_monument_and_repairs_still_win(self):
        for change,expected in (('TestWorld.allowed[100]=true',100),('TestWorld.allowed[101]=true',101),
                                ('local c=TestWorld.cities[1];local f=c.GetBuildings;c.GetBuildings=function(self)local b=f(self);local old=b.IsPillaged;b.IsPillaged=function(o,i)return i==9 or old(o,i)end;return b end',901)):
            with self.subTest(change=change):
                self.setUp();self.case.change(change);self.assertEqual(self.case.chosen(),expected)

if __name__=='__main__':unittest.main()
