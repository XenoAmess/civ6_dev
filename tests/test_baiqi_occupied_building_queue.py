"""Use the actual city writer with an intact prerequisite occupied by an enemy."""
from pathlib import Path
from unittest import TestCase, mock
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
import test_baiqi_blocked_building_queue as blocked
import test_baiqi_prayer_production as prayer

ROOT = Path(__file__).resolve().parents[1]


class OccupiedQueueContract:
    def setUp(self):
        self.original = blocked.BlockedBuildingQueueTests(methodName='runTest')
        def quiet_vm(*args, **kwargs):
            vm = self.VM(*args, **kwargs)
            vm.globals().print = lambda *values: None
            return vm
        with mock.patch.object(prayer, 'LuaRuntime', quiet_vm):
            self.original.setUp()
        self.case = self.original.case
        self.case.change((ROOT/'tests/lua/mock_occupied_building.lua').read_text(encoding='utf-8'))
        self.w = self.case.w

    def test_prepend_preserves_unfinished_entry_and_investment(self):
        for progress in (0, 73):
            with self.subTest(progress=progress):
                self.setUp()
                self.w.blockedProgress = progress
                self.w.applyWriter = True
                self.assertEqual(self.case.chosen(), 901)
                self.case.change('assert(TestWorld.queues[66][2]==TestWorld.oldEntry)')
                self.assertEqual(self.w.blockedProgress, progress)
                self.assertEqual(len(self.w.unitRequests), 0)
                self.case.c.RunNow()
                self.assertEqual(len(self.w.cityRequests), 1)
                self.assertIn('queue_observed', self.original.logs())

    def test_missing_or_ineligible_occupancy_never_preempts(self):
        changes = (
            'TestWorld.occupiedVisible=false', 'TestWorld.occupiedVisible=nil',
            'TestWorld.occupiedRevealed=false', 'TestWorld.occupiedWar=false',
            'TestWorld.occupiedWar=nil', 'TestWorld.occupiedUnitsUnknown=true',
            'Units.GetUnitsInPlotLayerID=nil', 'TestWorld.occupiedComplete=false',
            'TestWorld.occupiedComplete=nil', 'TestWorld.occupiedDead=true',
            'TestWorld.occupiedDelayed=true', 'TestWorld.occupiedX=4',
            'TestWorld.occupiedID=-1', 'TestWorld.occupiedType=999',
            'TestWorld.occupiedPlotOwner=8', 'TestWorld.occupiedDuplicate=true',
            'TestWorld.throwOccupiedDistricts=true', 'TestWorld.blockedPillaged=nil',
            "TestWorld.occupiedDefinition.Domain='DOMAIN_RELIGIOUS'",
            'TestWorld.occupiedDefinition.Combat=0;TestWorld.occupiedDefinition.RangedCombat=0',
            'TestWorld.occupiedDefinition.RangedCombat=nil',
        )
        for change in changes:
            with self.subTest(change=change):
                self.setUp()
                self.case.change(change)
                self.case.c.RunNow()
                self.assertEqual(len(self.w.cityRequests), 0)
                self.assertEqual(len(self.w.unitRequests), 0)

    def test_active_multiple_buildable_and_complete_entries_remain_untouched(self):
        for change in ('TestWorld.current[66]=902',
                       'TestWorld.queues[66][2]={BuildingType=9}',
                       'TestWorld.blockedAllowed=true', 'TestWorld.blockedBuilt=true',
                       'TestWorld.blockedProgress=165'):
            with self.subTest(change=change):
                self.setUp()
                self.case.change(change)
                self.case.c.RunNow()
                self.assertEqual(len(self.w.cityRequests), 0)

    def test_boundary_changes_reject_the_write(self):
        for change in ('w.occupiedVisible=false', 'w.occupiedWar=false',
                       'w.occupiedID=502', 'w.occupiedDistrictID=9011',
                       'w.blockedProgress=w.blockedProgress+1',
                       'w.turn=w.turn+1', 'w.queues[66][2]={BuildingType=9}'):
            with self.subTest(change=change):
                self.setUp()
                self.case.change('local w=TestWorld;w.shock=function() '+change+'; end')
                self.case.c.RunNow()
                self.assertEqual(len(self.w.cityRequests), 0)
                self.assertEqual(len(self.w.unitRequests), 0)


class OccupiedBuildingQueueLua51Tests(OccupiedQueueContract, TestCase):
    VM = Lua51


class OccupiedBuildingQueueLua53Tests(OccupiedQueueContract, TestCase):
    VM = Lua53
