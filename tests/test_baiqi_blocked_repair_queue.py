"""An invested building repair can be stranded by its damaged prerequisite."""
import unittest
import test_baiqi_blocked_project_queue as project


class BlockedRepairQueueTests(unittest.TestCase):
    def setUp(self):
        fixture = project.BlockedProjectQueueTests(methodName='runTest')
        fixture.setUp()
        self.case = fixture.case
        self.case.change('''
local w=TestWorld
w.blockedProgress=72;w.blockedCost=97;w.repairOwned=true;w.repairPillaged=true
w.oldEntry={BuildingType=18,Directive=1,Modifiers=0,Location={x=-9999,y=-9999}}
w.queues[66]={w.oldEntry}
local workshop={Index=18,Hash=1738306535,BuildingType='BUILDING_WORKSHOP',PrereqDistrict='DISTRICT_INDUSTRIAL_ZONE',Maintenance=0}
w.workshop=workshop
local list={};for row in GameInfo.Buildings()do list[#list+1]=row end;list[#list+1]=workshop
GameInfo.Buildings[18]=workshop;GameInfo.Buildings[workshop.Hash]=workshop;GameInfo.Buildings[workshop.BuildingType]=workshop
setmetatable(GameInfo.Buildings,{__call=function()local i=0;return function()i=i+1;return list[i]end end})
for _,city in ipairs(w.cities)do
 local gb=city.GetBuildings
 city.GetBuildings=function()
  local b=gb();local has,pill=b.HasBuilding,b.IsPillaged
  b.HasBuilding=function(self,index)if index==18 then return w.repairOwned end;return has(self,index)end
  b.IsPillaged=function(self,index)
   if index==18 then if w.throwBuilding then error('repair state unknown')end;return w.repairPillaged end
   return pill(self,index)
  end
  return b
 end
 local gq=city.GetBuildQueue
 city.GetBuildQueue=function()
  local q=gq();local can,progress,cost=q.CanProduce,q.GetBuildingProgress,q.GetBuildingCost
  q.CanProduce=function(self,hash,mode,...)
   if hash==1738306535 then if mode==true then return w.blockedKnown end;return w.blockedAllowed end
   return can(self,hash,mode,...)
  end
  q.GetBuildingProgress=function(self,index)
   if index==18 then if w.throwProgress then error('repair progress unknown')end;return w.blockedProgress end
   return progress(self,index)
  end
  q.GetBuildingCost=function(self,index)if index==18 then return w.blockedCost end;return cost(self,index)end
  return q
 end
end
''')

    def logs(self):
        return '\n'.join(self.case.w.logs.values())

    def test_exact_prerequisite_repair_preserves_existing_building_investment(self):
        self.assertEqual(self.case.chosen(), -1698135861)
        self.case.change('assert(TestWorld.queues[66][2]==TestWorld.oldEntry)')
        self.case.c.Update(3)
        self.assertEqual(self.case.w.blockedProgress, 72)
        self.assertIn('queue_observed', self.logs())
        self.assertEqual(len(self.case.w.cityRequests), 1)

    def test_unrelated_candidates_do_not_spend_the_repair_budget(self):
        self.case.change('BaiqiConfig.candidatesPerCity=1')
        self.assertEqual(self.case.chosen(), -1698135861)

    def test_active_buildable_or_unpillaged_work_is_preserved(self):
        for change in ('TestWorld.current[66]=1738306535',
                       'TestWorld.queues[66][2]={BuildingType=9}',
                       'TestWorld.blockedProgress=0', 'TestWorld.blockedProgress=97',
                       'TestWorld.blockedAllowed=true', 'TestWorld.repairPillaged=false',
                       'TestWorld.blockedPillaged=false', 'TestWorld.blockedKnown=false'):
            with self.subTest(change=change):
                self.setUp(); self.case.change(change); self.case.c.RunNow()
                self.assertEqual(len(self.case.w.cityRequests), 0)

    def test_unknown_and_invalid_metadata_never_authorize_repair(self):
        for change in ('TestWorld.repairOwned=nil', 'TestWorld.repairPillaged=nil',
                       'TestWorld.blockedKnown=nil', 'TestWorld.blockedPillaged=nil',
                       'TestWorld.blockedAllowed=nil', 'TestWorld.throwBuilding=true',
                       'TestWorld.throwProgress=true', 'TestWorld.blockedCost=0/0',
                       'TestWorld.blockedProgress=math.huge', 'TestWorld.blockedProgress=-1',
                       'TestWorld.workshop.Hash=0', 'TestWorld.workshop.BuildingType=nil',
                       'TestWorld.workshop.PrereqDistrict=nil', 'TestWorld.workshop.Index=18.5',
                       'TestWorld.district.Hash=0', 'TestWorld.district.Hash=math.huge',
                       'TestWorld.oldEntry.ProjectType=10', 'TestWorld.oldEntry.Modifiers=nil',
                       'TestWorld.oldEntry.Location.x=math.huge'):
            with self.subTest(change=change):
                self.setUp(); self.case.change(change); self.case.c.RunNow()
                self.assertEqual(len(self.case.w.cityRequests), 0)

    def test_every_final_repair_identity_or_progress_drift_stops_write(self):
        for shock in ('w.repairOwned=false', 'w.repairPillaged=false',
                      'w.blockedProgress=71', 'w.blockedCost=98',
                      'w.blockedPillaged=false', 'w.blockedAllowed=true',
                      'w.oldEntry.Modifiers=1', 'w.current[66]=1738306535',
                      'w.workshop.Hash=123', 'w.workshop.BuildingType="OTHER"',
                      'w.district.Hash=123', 'w.queues[66][2]={BuildingType=9}'):
            with self.subTest(shock=shock):
                self.setUp(); self.case.change('TestWorld.projectShock=function()local w=TestWorld;'+shock+' end')
                self.case.c.RunNow(); self.assertEqual(len(self.case.w.cityRequests), 0)

    def test_native_modes_and_operation_are_still_required(self):
        for flag in ('rejectFirst', 'rejectSecond', 'rejectFinal', 'rejectOperation'):
            with self.subTest(flag=flag):
                self.setUp(); self.case.w[flag]=True; self.case.c.RunNow()
                self.assertEqual(len(self.case.w.cityRequests), 0)

    def test_native_prune_preserves_unfinished_owned_repair(self):
        self.case.w.pruneWriter=True
        self.assertEqual(self.case.chosen(), -1698135861)
        self.case.c.Update(3)
        self.assertIn('queue_observed', self.logs())
        self.assertEqual(self.case.w.blockedProgress, 72)
        self.assertTrue(self.case.w.repairOwned)
        self.assertEqual(len(self.case.w.queues[66]), 1)

    def test_lost_unknown_completed_or_no_longer_pillaged_work_stays_pending(self):
        for prune in (False, True):
            for change in ('TestWorld.blockedProgress=71', 'TestWorld.blockedProgress=nil',
                           'TestWorld.blockedProgress=0/0', 'TestWorld.blockedProgress=97',
                           'TestWorld.blockedCost=nil', 'TestWorld.throwProgress=true',
                           'TestWorld.repairOwned=false', 'TestWorld.repairPillaged=false',
                           'TestWorld.repairOwned=nil', 'TestWorld.workshop.Hash=123'):
                with self.subTest(prune=prune, change=change):
                    self.setUp(); self.case.w.pruneWriter=prune
                    self.assertEqual(self.case.chosen(), -1698135861)
                    self.case.change(change); self.case.c.Update(3)
                    self.assertNotIn('queue_observed', self.logs())
                    self.assertIn('queue_prepend_unresolved', self.logs())

    def test_wrong_head_or_retained_entry_cannot_acknowledge(self):
        for change in ('TestWorld.current[66]=901',
                       'TestWorld.queues[66][1]={BuildingType=9,Directive=1,Modifiers=0}',
                       'TestWorld.oldEntry.Modifiers=1', 'TestWorld.queues[66][3]={BuildingType=9}'):
            with self.subTest(change=change):
                self.setUp(); self.assertEqual(self.case.chosen(), -1698135861)
                self.case.change(change); self.case.c.Update(3)
                self.assertNotIn('queue_observed', self.logs())
                self.assertIn('queue_prepend_unresolved', self.logs())

    def test_unknown_or_throwing_writer_is_not_replayed(self):
        for throws in (False, True):
            with self.subTest(throws=throws):
                self.setUp(); self.case.w.applyWriter=False; self.case.w.throwWriter=throws
                self.case.c.RunNow(); self.case.w.throwWriter=False
                self.case.c.Update(3); self.case.w.turn=2; self.case.c.RunNow(); self.case.c.RunNow()
                self.assertEqual(len(self.case.w.cityRequests), 1)
                self.assertNotIn('queue_observed', self.logs())


if __name__ == '__main__':
    unittest.main()
