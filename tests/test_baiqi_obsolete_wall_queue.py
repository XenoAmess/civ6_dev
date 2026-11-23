"""Run the complete Controller against a wall invalidated by urban defenses."""
from pathlib import Path
from unittest import TestCase, mock

from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
import test_baiqi_blocked_building_queue as blocked
import test_baiqi_prayer_production as prayer

ROOT = Path(__file__).resolve().parents[1]


class ObsoleteWallContract:
    def setUp(self):
        def quiet_vm(*args, **kwargs):
            vm = self.VM(*args, **kwargs)
            vm.globals().print = lambda *values: None
            return vm
        self.original = blocked.BlockedBuildingQueueTests(methodName='runTest')
        with mock.patch.object(prayer, 'LuaRuntime', quiet_vm):
            self.original.setUp()
        self.case = self.original.case
        self.case.change((ROOT/'tests/lua/mock_obsolete_wall.lua').read_text(encoding='utf-8'))
        self.w = self.case.w

    def no_write(self, change):
        self.case.change(change)
        self.case.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_legal_prepend_preserves_each_wall_and_investment(self):
        for name in ('BUILDING_WALLS', 'BUILDING_CASTLE', 'BUILDING_STAR_FORT'):
            for progress in (0, 73):
                with self.subTest(name=name, progress=progress):
                    self.setUp()
                    self.w.wallDefinition.BuildingType = name
                    self.w.blockedProgress = progress
                    self.w.applyWriter = True
                    self.assertEqual(self.case.chosen(), 901)
                    self.case.change('assert(TestWorld.queues[66][2]==TestWorld.oldEntry)')
                    self.assertEqual(self.w.blockedProgress, progress)
                    self.case.c.RunNow()
                    self.assertEqual(len(self.w.cityRequests), 1)
                    self.assertIn('queue_observed', self.original.logs())

    def test_missing_technology_mapping_or_known_center_never_authorizes(self):
        changes = (
            'TestWorld.steelKnown=false', 'TestWorld.steelKnown=nil',
            'TestWorld.wallTechKnown=false', 'TestWorld.throwWallTech=true',
            'GameInfo.Technologies.TECH_STEEL=nil',
            'TestWorld.steelDefinition.Hash=0',
            "TestWorld.steelDefinition.TechnologyType='OTHER'",
            'GameInfo.TechnologyModifiers=nil',
            'GameInfo.TechnologyModifiers=function()return ipairs({TestWorld.steelLink,TestWorld.steelLink})end',
            "TestWorld.steelLink.ModifierId='OTHER'",
            "TestWorld.steelModifier.ModifierType='OTHER'",
            "TestWorld.steelDynamic.EffectType='OTHER'",
            "TestWorld.steelDynamic.CollectionType='OTHER'",
            "TestWorld.steelModifier.SubjectRequirementSetId='CONDITIONAL'",
            'TestWorld.centerKnown=false', 'TestWorld.centerKnown=nil',
            'TestWorld.centerPillaged=true', 'TestWorld.centerPillaged=nil',
            'TestWorld.centerComplete=false', 'TestWorld.centerID=-1',
            'TestWorld.centerOwner=8', 'TestWorld.centerType=3',
            'TestWorld.duplicateCenter=true',
        )
        for change in changes:
            with self.subTest(change=change):
                self.setUp()
                self.no_write(change)

    def test_unknown_or_changed_wall_and_native_queue_are_preserved(self):
        changes = (
            "TestWorld.wallDefinition.BuildingType='BUILDING_FACTORY'",
            "TestWorld.wallDefinition.PrereqDistrict='DISTRICT_CAMPUS'",
            'TestWorld.wallDefinition.OuterDefenseHitPoints=0',
            'TestWorld.wallDefinition.OuterDefenseStrength=nil',
            'TestWorld.wallDefinition.IsWonder=true',
            'TestWorld.wallDefinition.MustPurchase=true',
            'TestWorld.wallDefinition.RequiresPlacement=true',
            'TestWorld.wallDefinition.Hash=0',
            'GameInfo.Technologies.TECH_SIEGE_TACTICS.Hash=nil',
            'TestWorld.blockedBuilt=true', 'TestWorld.blockedBuilt=nil',
            'TestWorld.blockedAllowed=true', 'TestWorld.blockedKnown=true',
            'TestWorld.blockedProgress=165', 'TestWorld.blockedProgress=-1',
            'TestWorld.blockedCost=0/0', 'TestWorld.throwProgress=true',
            'TestWorld.current[66]=902',
            'TestWorld.queues[66][2]={BuildingType=9}',
            'TestWorld.oldEntry.UnitType=0',
            'CityOperationTypes.VALUE_PREPEND=CityOperationTypes.VALUE_APPEND',
        )
        for change in changes:
            with self.subTest(change=change):
                self.setUp()
                self.no_write(change)

    def test_boundary_changes_reject_without_native_writer_or_army_command(self):
        for change in (
            'w.steelKnown=false', 'w.wallTechKnown=false',
            "w.steelDynamic.EffectType='OTHER'", 'w.centerID=809',
            'w.wallDefinition.OuterDefenseHitPoints=101',
            'w.steelDefinition.Hash=-1438095362',
            'w.centerOwner=8', 'w.centerComplete=false',
            'w.blockedProgress=w.blockedProgress+1',
            'w.oldEntry.Modifiers=1', 'w.turn=w.turn+1',
            'w.strategic=false', 'w.busy=true',
            'w.queues[66][2]={BuildingType=9}',
        ):
            with self.subTest(change=change):
                self.setUp()
                self.no_write('TestWorld.shock=function()local w=TestWorld;' + change + ' end')

    def test_native_rejection_and_unknown_writer_are_not_replayed(self):
        for flag in ('rejectFirst', 'rejectSecond', 'rejectFinal', 'rejectOperation'):
            with self.subTest(flag=flag):
                self.setUp()
                self.no_write('TestWorld.' + flag + '=true')
        for throws in (False, True):
            with self.subTest(throws=throws):
                self.setUp()
                self.w.throwWriter = throws
                self.case.c.RunNow()
                self.w.throwWriter = False
                self.case.c.Update(3)
                self.w.turn = 2
                self.case.c.RunNow()
                self.case.c.RunNow()
                self.assertEqual(len(self.w.cityRequests), 1)

    def test_no_candidate_wait_is_bounded_and_reconsiders_without_queue_edits(self):
        self.w.allowed[901] = False
        for _ in range(20):
            self.case.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)
        self.assertEqual(self.original.logs().count('城市等待合法生产或预算'), 1)
        self.w.allowed[901] = True
        self.case.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)
        self.case.c.Update(10.1)
        self.assertEqual(self.case.chosen(), 901)
        self.assertEqual(len(self.w.cityRequests), 1)

    def test_retained_investment_is_required_if_engine_prunes_or_changes_old_row(self):
        for prune in (False, True):
            with self.subTest(prune=prune):
                self.setUp()
                self.w.applyWriter = True
                self.w.pruneWriter = prune
                self.assertEqual(self.case.chosen(), 901)
                self.w.blockedProgress = 72
                self.case.c.Update(3)
                self.assertNotIn('queue_observed', self.original.logs())
                self.assertIn('queue_prepend_unresolved', self.original.logs())
                self.case.c.RunNow()
                self.assertEqual(len(self.w.cityRequests), 1)


class ObsoleteWallLua51Tests(ObsoleteWallContract, TestCase):
    VM = Lua51


class ObsoleteWallLua53Tests(ObsoleteWallContract, TestCase):
    VM = Lua53
