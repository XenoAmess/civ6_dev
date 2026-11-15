"""A legal barrier can precede invested work whose flooded district cannot repair."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
import test_baiqi_blocked_project_queue as project
import test_baiqi_blocked_repair_queue as repair

ROOT = Path(__file__).resolve().parents[1]


class BlockedFloodQueueTests(unittest.TestCase):
    def fixture(self, runtime, kind):
        # Both inherited fixtures use the actual PrayerProductionTests loader.
        loader = project.building.prayer
        previous = loader.LuaRuntime
        loader.LuaRuntime = runtime
        try:
            fixture = (project.BlockedProjectQueueTests if kind == 'project'
                       else repair.BlockedRepairQueueTests)(methodName='runTest')
            fixture.setUp()
        finally:
            loader.LuaRuntime = previous
        case = fixture.case
        for path in ('tests/lua/mock_flood.lua', 'mod/Baiqi/Lua/BaiqiFlood.lua'):
            case.change((ROOT / path).read_text(encoding='utf-8'))
        case.change('''
local w=TestWorld
InstallFlood(w.cities,7)
w.allowed[913]=true;w.allowed[w.repairHash]=false
local can=CityManager.CanStartOperation
CityManager.CanStartOperation=function(city,op,p,...)
 local result=can(city,op,p,...)
 if p[CityOperationTypes.PARAM_BUILDING_TYPE]==913 then
  local n=w.qualification[913]
  if n==2 and w.barrierShock then w.barrierShock()end
  if n==3 and w.barrierLateShock then w.barrierLateShock()end
  if w.rejectBarrierOperation then return false end
 end
 return result
end
for _,city in ipairs(w.cities)do
 local gq=city.GetBuildQueue
 city.GetBuildQueue=function(c)
  local q=gq(c);local canProduce=q.CanProduce
  q.CanProduce=function(self,hash,mode,...)
   if hash==913 and ((mode==true and w.rejectBarrierVisible)or(mode==false and w.rejectBarrierFull))then return false end
   return canProduce(self,hash,mode,...)
  end
  return q
 end
end
-- Model native PREPEND and optional engine pruning, never barrier drainage.
CityManager.RequestOperation=function(city,op,p)
 w.cityRequests[#w.cityRequests+1]={city=city:GetID(),op=op,params=p}
 assert(p[CityOperationTypes.PARAM_INSERT_MODE]==CityOperationTypes.VALUE_PREPEND)
 if w.throwWriter then error('unknown after native dispatch')end
 if w.applyWriter then
  local entry,hash
  if p[CityOperationTypes.PARAM_BUILDING_TYPE] then
   hash=p[CityOperationTypes.PARAM_BUILDING_TYPE];assert(hash==913)
   entry={BuildingType=113,Directive=1,Modifiers=0}
  else
   hash=p[CityOperationTypes.PARAM_DISTRICT_TYPE];assert(hash==w.repairHash)
   entry={DistrictType=9,Directive=2,Modifiers=0,Location={x=2,y=3}}
  end
  table.insert(w.queues[city:GetID()],1,entry);w.current[city:GetID()]=hash
  if w.pruneWriter then table.remove(w.queues[city:GetID()],2)end
 end
end
''')
        return case

    def cases(self):
        for runtime in (Lua51, Lua53):
            for kind in ('project', 'building_repair'):
                yield runtime, kind

    @staticmethod
    def logs(case):
        return '\n'.join(case.w.logs.values())

    def test_barrier_prepend_retains_entry_and_stored_investment(self):
        for runtime, kind in self.cases():
            with self.subTest(lua=runtime, kind=kind):
                case = self.fixture(runtime, kind)
                before = case.w.blockedProgress
                self.assertEqual(case.chosen(), 913)
                case.change('assert(TestWorld.queues[66][2]==TestWorld.oldEntry)')
                self.assertIsNone(case.w.cityRequests[1].params[3])
                case.c.Update(3)
                self.assertIn('queue_observed', self.logs(case))
                self.assertEqual(case.w.blockedProgress, before)
                self.assertFalse(case.lua.globals().TestFlood.has)
                self.assertEqual(len(case.w.cityRequests), 1)

    def test_native_pruning_acknowledges_only_preserved_unfinished_investment(self):
        for runtime, kind in self.cases():
            case = self.fixture(runtime, kind)
            case.w.pruneWriter = True
            before = case.w.blockedProgress
            self.assertEqual(case.chosen(), 913)
            case.c.Update(3)
            self.assertEqual(len(case.w.queues[66]), 1)
            self.assertIn('queue_observed', self.logs(case))
            self.assertEqual(case.w.blockedProgress, before)

    def test_unknown_resolved_or_submerged_demand_never_authorizes_barrier(self):
        for runtime, kind in self.cases():
            for change in ('TestFlood.flooded=false', 'TestFlood.flooded=nil',
                           'TestFlood.submerged=true', 'TestFlood.low=nil',
                           'TestFlood.has=true', 'TestFlood.throwTerrain=true'):
                with self.subTest(lua=runtime, kind=kind, change=change):
                    case = self.fixture(runtime, kind)
                    case.change(change); case.c.RunNow()
                    self.assertEqual(len(case.w.cityRequests), 0)

    def test_legal_prerequisite_repair_remains_available_without_flood_demand(self):
        for runtime, kind in self.cases():
            case = self.fixture(runtime, kind)
            case.change('TestFlood.flooded=false;TestWorld.allowed[TestWorld.repairHash]=true')
            self.assertEqual(case.chosen(), -1698135861)
            case.c.Update(3)
            self.assertIn('queue_observed', self.logs(case))

    def test_native_legality_and_pending_purchase_still_block_barrier(self):
        for runtime, kind in self.cases():
            for change in ('TestWorld.rejectBarrierVisible=true', 'TestWorld.rejectBarrierFull=true',
                           'TestWorld.rejectBarrierOperation=true',
                           'BaiqiFloodPurchase={Holds=function()return true end}'):
                case = self.fixture(runtime, kind)
                case.change(change); case.c.RunNow()
                self.assertEqual(len(case.w.cityRequests), 0)

    def test_final_demand_and_retained_work_changes_stop_write(self):
        for runtime, kind in self.cases():
            for hook in ('barrierShock', 'barrierLateShock'):
                for change in ('TestFlood.flooded=false', 'TestFlood.submerged=true',
                               'w.oldEntry.Modifiers=1', 'w.blockedProgress=w.blockedProgress-1',
                               'w.blockedCost=w.blockedCost+1', 'w.current[66]=901',
                               'w.turn=2', 'w.blockedPillaged=false',
                               'TestFlood.definition.Hash=914', 'TestFlood.definition.Index=114',
                               'TestFlood.definition.BuildingType="OTHER"',
                               'w.cities[1].GetOwner=function()return 8 end'):
                    with self.subTest(lua=runtime, kind=kind, hook=hook, change=change):
                        case = self.fixture(runtime, kind)
                        case.change('TestWorld.'+hook+'=function()local w=TestWorld;'+change+' end')
                        case.c.RunNow()
                        self.assertEqual(len(case.w.cityRequests), 0)

    def test_readback_rejects_lost_unknown_or_completed_investment(self):
        for runtime, kind in self.cases():
            for prune in (False, True):
                for change in ('w.blockedProgress=w.blockedProgress-1', 'w.blockedProgress=nil',
                               'w.blockedProgress=w.blockedCost', 'w.throwProgress=true',
                               'w.blockedCost=nil'):
                    case = self.fixture(runtime, kind)
                    case.w.pruneWriter = prune
                    self.assertEqual(case.chosen(), 913)
                    case.change('local w=TestWorld;'+change); case.c.Update(3)
                    self.assertNotIn('queue_observed', self.logs(case))
                    self.assertIn('queue_prepend_unresolved', self.logs(case))

    def test_readback_rejects_wrong_barrier_identity_head_or_old_entry(self):
        for runtime, kind in self.cases():
            for change in ('w.current[66]=901', 'w.oldEntry.Modifiers=1',
                           'w.queues[66][1]={BuildingType=9,Directive=1,Modifiers=0}',
                           'w.queues[66][3]={BuildingType=9}',
                           'TestFlood.definition.Hash=914', 'TestFlood.definition.Index=114',
                           'TestFlood.definition.BuildingType="OTHER"'):
                case = self.fixture(runtime, kind)
                self.assertEqual(case.chosen(), 913)
                case.change('local w=TestWorld;'+change); case.c.Update(3)
                self.assertNotIn('queue_observed', self.logs(case))
                self.assertIn('queue_prepend_unresolved', self.logs(case))

    def test_unobserved_or_throwing_request_is_not_replayed(self):
        for runtime, kind in self.cases():
            for throws in (False, True):
                case = self.fixture(runtime, kind)
                case.w.applyWriter = False; case.w.throwWriter = throws
                case.c.RunNow(); case.w.throwWriter = False
                case.c.Update(3); case.w.turn = 2; case.c.RunNow(); case.c.RunNow()
                self.assertEqual(len(case.w.cityRequests), 1)
                self.assertNotIn('queue_observed', self.logs(case))

    def test_active_or_multiple_queue_is_preserved(self):
        for runtime, kind in self.cases():
            for change in ('TestWorld.current[66]=901',
                           'TestWorld.queues[66][2]={BuildingType=9}'):
                case = self.fixture(runtime, kind)
                case.change(change); case.c.RunNow()
                self.assertEqual(len(case.w.cityRequests), 0)


if __name__ == '__main__':
    unittest.main()
