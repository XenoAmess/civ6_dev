"""Repair a known pillaged prerequisite without spending the stranded project twice."""
import unittest
import test_baiqi_blocked_building_queue as building


class BlockedProjectQueueTests(unittest.TestCase):
    def setUp(self):
        fixture = building.BlockedBuildingQueueTests(methodName='runTest')
        fixture.setUp()
        self.case = fixture.case
        self.case.change('''
local w=TestWorld
w.applyWriter=true;w.blockedProgress=143;w.blockedCost=154
w.repairHash=-1698135861;w.projectHash=-1205325871
w.oldEntry={ProjectType=10,Directive=3,Modifiers=0,Location={x=-9999,y=-9999}}
w.queues[66]={w.oldEntry};w.queues[67]={{BuildingType=9}}
CityProductionDirectives={TRAIN=0,CONSTRUCT=1,ZONE=2,PROJECT=3}
local project={Index=10,Hash=w.projectHash,ProjectType='PROJECT_ENHANCE_DISTRICT_INDUSTRIAL_ZONE',PrereqDistrict='DISTRICT_INDUSTRIAL_ZONE'}
local district={Index=9,Hash=w.repairHash,DistrictType='DISTRICT_INDUSTRIAL_ZONE'}
w.project=project;w.district=district
GameInfo.Projects[10]=project;GameInfo.Projects[w.projectHash]=project;GameInfo.Projects[project.ProjectType]=project
local oldDistricts={GameInfo.Districts[3],GameInfo.Districts[4]}
GameInfo.Districts[9]=district;GameInfo.Districts[w.repairHash]=district;GameInfo.Districts[district.DistrictType]=district
setmetatable(GameInfo.Districts,{__call=function()
 local list={oldDistricts[1],oldDistricts[2],district};local i=0;return function()i=i+1;return list[i]end
end})
w.allowed={[901]=true,[w.repairHash]=true}
for _,city in ipairs(w.cities)do
 local gd=city.GetDistricts
 city.GetDistricts=function()
  local d=gd();local has,pill=d.HasDistrict,d.IsPillaged
  d.HasDistrict=function(self,index,...)
   if index==9 then if w.throwPrereq then error('prerequisite unknown')end;return w.blockedKnown end
   return has(self,index,...)
  end
  d.IsPillaged=function(self,index)if index==9 then return w.blockedPillaged end;return pill(self,index)end
  return d
 end
 local gq=city.GetBuildQueue
 city.GetBuildQueue=function()
  local q=gq();local can,placed=q.CanProduce,q.HasBeenPlaced
  q.CanProduce=function(self,hash,mode,...)
   if hash==w.projectHash then if mode==true then return w.blockedKnown end;return w.blockedAllowed end
   if hash==w.repairHash then
    if w.blockedPillaged~=true then return false end
    if (mode==true and w.rejectFirst)or(mode==false and w.rejectSecond)then return false end
    return w.allowed[hash]==true
   end
   return can(self,hash,mode,...)
  end
  q.HasBeenPlaced=function(self,hash)if hash==w.repairHash then return true end;return placed(self,hash)end
  q.GetProjectProgress=function(_,index)assert(index==10);if w.throwProgress then error('project progress unknown')end;return w.blockedProgress end
  q.GetProjectCost=function(_,index)assert(index==10);return w.blockedCost end
  q.GetDistrictProgress=function()return 90 end
  q.GetDistrictCost=function()return 121 end
  return q
 end
end
local nativeCan=CityManager.CanStartOperation
CityManager.CanStartOperation=function(city,op,params,...)
 local ok=nativeCan(city,op,params,...)
 if params[CityOperationTypes.PARAM_DISTRICT_TYPE]==w.repairHash then
  if w.qualification[w.repairHash]==2 and w.projectShock then w.projectShock()end
  if w.rejectFinal and w.qualification[w.repairHash]>=2 then return false end
 end
 return ok
end
CityManager.RequestOperation=function(city,op,params)
 w.cityRequests[#w.cityRequests+1]={city=city:GetID(),op=op,params=params}
 if w.throwWriter then error('unknown after request')end
 if w.applyWriter then
  assert(params[CityOperationTypes.PARAM_INSERT_MODE]==CityOperationTypes.VALUE_PREPEND)
  assert(params[CityOperationTypes.PARAM_DISTRICT_TYPE]==w.repairHash and params[CityOperationTypes.PARAM_BUILDING_TYPE]==nil)
  table.insert(w.queues[city:GetID()],1,{DistrictType=9,Directive=2,Modifiers=0,Location={x=2,y=3}})
  w.current[city:GetID()]=w.repairHash
  if w.pruneWriter then table.remove(w.queues[city:GetID()],2)end
 end
end
''')

    def logs(self):
        return '\n'.join(self.case.w.logs.values())

    def test_exact_prerequisite_repair_preserves_project_and_investment(self):
        self.assertEqual(self.case.chosen(), -1698135861)
        self.case.change('assert(TestWorld.queues[66][2]==TestWorld.oldEntry)')
        self.case.c.Update(3)
        self.assertEqual(self.case.w.blockedProgress, 143)
        self.assertIn('queue_observed', self.logs())
        self.assertEqual(len(self.case.w.cityRequests), 1)
        self.assertIsNone(self.case.w.cityRequests[1].params[2])

    def test_irrelevant_candidates_do_not_exhaust_repair_budget(self):
        self.case.change('BaiqiConfig.candidatesPerCity=1')
        self.assertEqual(self.case.chosen(), -1698135861)

    def test_active_multiple_or_zero_investment_is_preserved(self):
        for change in ('TestWorld.current[66]=TestWorld.projectHash',
                       'TestWorld.queues[66][2]={BuildingType=9}',
                       'TestWorld.blockedProgress=0'):
            with self.subTest(change=change):
                self.setUp(); self.case.change(change); self.case.c.RunNow()
                self.assertEqual(len(self.case.w.cityRequests), 0)

    def test_buildable_missing_or_unpillaged_prerequisite_is_preserved(self):
        for change in ('TestWorld.blockedAllowed=true', 'TestWorld.blockedKnown=false',
                       'TestWorld.blockedPillaged=false', 'TestWorld.blockedProgress=154'):
            with self.subTest(change=change):
                self.setUp(); self.case.change(change); self.case.c.RunNow()
                self.assertEqual(len(self.case.w.cityRequests), 0)

    def test_unknown_or_malformed_inputs_never_authorize_repair(self):
        for change in ('TestWorld.blockedKnown=nil', 'TestWorld.blockedPillaged=nil',
                       'TestWorld.blockedAllowed=nil', 'TestWorld.throwPrereq=true',
                       'TestWorld.throwProgress=true', 'TestWorld.blockedCost=0/0',
                       'TestWorld.blockedProgress=-1', 'TestWorld.oldEntry.UnitType=0',
                       'TestWorld.oldEntry.Modifiers=nil', 'TestWorld.oldEntry.Directive=1',
                       'CityProductionDirectives=nil', 'TestWorld.oldEntry.Location.x=math.huge',
                       'TestWorld.project.PrereqDistrict=nil', 'TestWorld.project.Hash=0',
                       'TestWorld.project.Index=10.5', 'TestWorld.district.Hash=math.huge'):
            with self.subTest(change=change):
                self.setUp(); self.case.change(change); self.case.c.RunNow()
                self.assertEqual(len(self.case.w.cityRequests), 0)

    def test_every_final_work_or_prerequisite_drift_stops_write(self):
        for shock in ('w.oldEntry.Modifiers=1', 'w.oldEntry.Location.x=3',
                      'w.blockedProgress=142', 'w.blockedCost=155',
                      'w.blockedPillaged=false', 'w.blockedAllowed=true',
                      'w.current[66]=w.projectHash', 'w.project.Hash=123',
                      'w.queues[66][2]={BuildingType=9}'):
            with self.subTest(shock=shock):
                self.setUp(); self.case.change('TestWorld.projectShock=function()local w=TestWorld;'+shock+' end')
                self.case.c.RunNow(); self.assertEqual(len(self.case.w.cityRequests), 0)

    def test_both_native_modes_and_operation_remain_authoritative(self):
        for flag in ('rejectFirst','rejectSecond','rejectFinal','rejectOperation'):
            with self.subTest(flag=flag):
                self.setUp(); self.case.w[flag]=True; self.case.c.RunNow()
                self.assertEqual(len(self.case.w.cityRequests), 0)

    def test_native_prune_requires_stored_unfinished_investment(self):
        self.case.w.pruneWriter=True
        self.assertEqual(self.case.chosen(), -1698135861)
        self.case.c.Update(3)
        self.assertIn('queue_observed', self.logs())
        self.assertEqual(self.case.w.blockedProgress, 143)

    def test_progress_loss_or_unknown_or_completion_keeps_pending(self):
        for prune in (False, True):
            for change in ('TestWorld.blockedProgress=142', 'TestWorld.blockedProgress=nil',
                           'TestWorld.blockedProgress=0/0', 'TestWorld.throwProgress=true',
                           'TestWorld.blockedProgress=154', 'TestWorld.blockedCost=nil',
                           'TestWorld.project.Hash=123'):
                with self.subTest(prune=prune, change=change):
                    self.setUp(); self.case.w.pruneWriter=prune
                    self.assertEqual(self.case.chosen(), -1698135861)
                    self.case.change(change); self.case.c.Update(3)
                    self.assertNotIn('queue_observed', self.logs())
                    self.assertIn('queue_prepend_unresolved', self.logs())

    def test_wrong_head_or_changed_retained_entry_never_acknowledges(self):
        for change in ('TestWorld.current[66]=901',
                       'TestWorld.queues[66][1]={BuildingType=9,Directive=1,Modifiers=0}',
                       'TestWorld.oldEntry.Modifiers=1',
                       'TestWorld.queues[66][3]={BuildingType=9}'):
            with self.subTest(change=change):
                self.setUp(); self.assertEqual(self.case.chosen(), -1698135861)
                self.case.change(change); self.case.c.Update(3)
                self.assertNotIn('queue_observed', self.logs())
                self.assertIn('queue_prepend_unresolved', self.logs())

    def test_unobserved_or_throwing_writer_is_never_replayed(self):
        for throws in (False, True):
            with self.subTest(throws=throws):
                self.setUp(); self.case.w.applyWriter=False; self.case.w.throwWriter=throws
                self.case.c.RunNow(); self.case.w.throwWriter=False
                self.case.c.Update(3); self.case.w.turn=2; self.case.c.RunNow(); self.case.c.RunNow()
                self.assertEqual(len(self.case.w.cityRequests), 1)
                self.assertNotIn('queue_observed', self.logs())


if __name__ == '__main__':
    unittest.main()
