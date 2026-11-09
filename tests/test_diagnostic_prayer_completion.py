"""Actual project event module; callback snapshots are not reward attribution."""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=r'''
W={turn=111,player=0,human=true,leader='LEADER_BAIQI',owner=0,points=44,rate=4,faith=171,
 held=false,created=-1,earned=0,reads=0,writes=0,callbacks={},removeCalls=0}
local function inspect()W.reads=W.reads+1;if W.throw then error('snapshot unavailable')end end
local city={GetID=function()return 196610 end,GetOwner=function()return W.owner end}
local r={GetReligionTypeCreated=function()inspect();return W.created end,GetNumBeliefsEarned=function()return W.earned end,
 HasReligiousFoundingUnit=function()return W.held end,GetFaithBalance=function()return W.faith end}
local pts={GetPointsTotal=function(_,cls)assert(cls==4);if W.changePoints then W.points=W.points+1 end;return W.points end,
 GetPointsPerTurn=function(_,cls)assert(cls==4);return W.rate end}
local p={GetCities=function()return {FindID=function(_,id)assert(id==196610);if not W.noCity then return city end end}end,
 GetReligion=function()return r end,GetGreatPeoplePoints=function()return pts end,
 SetProperty=function()W.writes=W.writes+1;error('forbidden property write')end}
local event={Add=function(...)
 assert(select('#',...)==1,'static Add');local f=...;W.callbacks[#W.callbacks+1]=f;W.added=f
 if W.addThrow then error('Add failed after native attachment')end
end,Remove=function(...)
 assert(select('#',...)==1,'static Remove');local f=...;W.removeCalls=W.removeCalls+1;W.removed=f
 if W.removeThrow then error('Remove unavailable')end
 if W.removeFalse then return false end
 for i,v in ipairs(W.callbacks)do if v==f then table.remove(W.callbacks,i);break end end
end}
E={Game={GetCurrentGameTurn=function(...)assert(select('#',...)==0);return W.turn end,
 GetLocalPlayer=function(...)assert(select('#',...)==0);return W.player end},Players={[0]=p},
 PlayerConfigurations={[0]={IsHuman=function()return W.human end,GetLeaderTypeName=function()return W.leader end}},
 GameInfo={Projects={PROJECT_ENHANCE_DISTRICT_HOLY_SITE={Index=12,ProjectType='PROJECT_ENHANCE_DISTRICT_HOLY_SITE'}},
 GreatPersonClasses={GREAT_PERSON_CLASS_PROPHET={Index=4,GreatPersonClassType='GREAT_PERSON_CLASS_PROPHET'}}},
 Events={CityProjectCompleted=event},cityID=196610}
function Emit(pid,cid,project)for _,fn in ipairs(W.callbacks)do fn(pid,cid,project)end end
'''


class PrayerCompletionTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True);self.lua.execute(FIXTURE)
        path=Path(os.environ.get('BAIQI_PRAYER_EVENT_SOURCE') or ROOT/'tools/lua/diagnostic_prayer_completion.lua')
        self.module=self.lua.execute(path.read_text(encoding='utf-8'))
        self.w=self.lua.globals().W;self.e=self.lua.globals().E

    def install(self):
        self.handle=self.module.Install(self.e)
        return self.handle

    def emit(self,pid=0,city=196610,project=12):
        self.lua.globals().Emit(pid,city,project)
        self.assertEqual(self.w.writes,0)

    def test_default_bound_static_event_and_exact_known_record(self):
        h=self.install();self.emit()
        row=h.samples[1]
        self.assertEqual((row.playerID,row.cityID,row.projectID,row.turn,row.status),(0,196610,12,111,'KNOWN'))
        self.assertEqual((row.own.points,row.own.perTurn,row.own.faith,row.own.held),(44,4,171,False))
        self.assertEqual(row.observation,'COMPLETION_CALLBACK_NOT_REWARD_ATTRIBUTION')
        self.assertEqual(h.errors,0)

    def test_interturn_callback_does_not_require_active_turn_or_idle_core(self):
        self.e.maxRecords=1;self.install();self.lua.execute('E.Players[0].IsTurnActive=function()error("must not gate interturn event")end')
        self.emit();self.assertEqual(self.handle.samples[1].status,'KNOWN')

    def test_other_players_cities_projects_and_project_hash_are_ignored_before_snapshot(self):
        h=self.install()
        for args in ((1,196610,12),(0,99,12),(0,196610,13),(0,196610,30870116)):
            self.emit(*args)
        self.assertEqual(len(h.samples),0);self.assertEqual(self.w.reads,0)

    def test_context_or_ownership_change_ignores_without_reading_own_snapshot(self):
        for key,value in (('player',1),('human',False),('leader','LEADER_OTHER'),('turn',98),('turn',251),('owner',1),('noCity',True)):
            with self.subTest(key=key):
                self.setUp();self.e.maxRecords=2;h=self.install();self.w[key]=value;self.emit()
                self.assertEqual(len(h.samples),0);self.assertEqual(self.w.reads,0)

    def test_missing_snapshot_still_preserves_matching_event_as_unknown(self):
        h=self.install();self.w.throw=True;self.emit()
        row=h.samples[1]
        self.assertEqual((row.status,row.cityID,row.projectID),('UNKNOWN',196610,12))
        self.assertEqual(h.matches,1);self.assertEqual(h.errors,1);self.assertIsNone(row.own)

    def test_changed_or_invalid_snapshot_does_not_publish_numbers(self):
        for key,value in (('changePoints',True),('points',-1),('faith',float('nan')),('rate',-1)):
            with self.subTest(key=key):
                self.setUp();h=self.install();self.w[key]=value;self.emit()
                self.assertEqual(h.samples[1].status,'UNKNOWN')
                self.assertIsNone(h.samples[1].own)

    def test_explicit_bound_drops_without_more_snapshot_reads(self):
        self.e.maxRecords=1;h=self.install();self.emit();reads=self.w.reads
        self.emit();self.assertEqual((len(h.samples),h.matches,h.drops),(1,2,1))
        self.assertEqual(self.w.reads,reads)

    def test_record_bound_and_target_validation(self):
        for key,value in (('maxRecords',False),('maxRecords',0),('maxRecords',129),('maxRecords',float('inf')),('cityID',-1)):
            with self.subTest(key=key):
                self.setUp();self.e[key]=value
                with self.assertRaises(Exception):self.install()
                self.assertEqual(len(self.w.callbacks),0)

    def test_restore_removes_exact_callback_once_and_is_idempotent(self):
        h=self.install();self.assertTrue(h.Restore());self.assertTrue(h.Restore())
        self.assertTrue(self.lua.eval('W.added==W.removed'))
        self.assertEqual(self.w.removeCalls,1)
        self.emit();self.assertEqual(len(h.samples),0)

    def test_failed_remove_is_not_reported_restored_and_can_be_retried(self):
        for key in ('removeThrow','removeFalse'):
            with self.subTest(key=key):
                self.setUp();h=self.install();self.w[key]=True
                self.assertFalse(h.Restore());self.assertFalse(h.restored)
                self.w[key]=False;self.assertTrue(h.Restore())

    def test_add_exception_after_attachment_attempts_exact_cleanup(self):
        self.w.addThrow=True
        with self.assertRaises(Exception):self.install()
        self.assertEqual(len(self.w.callbacks),0)
        self.assertTrue(self.lua.eval('W.added==W.removed'))

    def test_native_object_metatables_are_supported(self):
        self.lua.execute('setmetatable(E.Game,{});setmetatable(E.Events.CityProjectCompleted,{})')
        h=self.install();self.emit();self.assertEqual(h.samples[1].status,'KNOWN')


if __name__=='__main__':
    unittest.main()
