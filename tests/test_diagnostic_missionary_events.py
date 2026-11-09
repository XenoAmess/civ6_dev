"""Passive event identity, raw data bounds and exact subscription cleanup."""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=r'''
W={turn=138,reads=0,callbacks={},addCalls=0,removeCalls={},snap={charges=1,x=55,delayed=false}}
names={'UnitChargesChanged','UnitOperationStarted','UnitOperationDeactivated','UnitRemovedFromMap'}
events={}
for _,eventName in ipairs(names)do
 local name=eventName;W.callbacks[name]={};W.removeCalls[name]=0
 events[name]={
  Add=function(...)
   assert(select('#',...)==1);local cb=...;W.addCalls=W.addCalls+1
   table.insert(W.callbacks[name],cb)
   if W.addFailure==name then if W.addThrow then error('after attachment')else return false end end
  end,
  Remove=function(...)
   assert(select('#',...)==1);local cb=...;W.removeCalls[name]=W.removeCalls[name]+1
   if W.removeFailure==name then if W.removeThrow then error('remove')else return false end end
   for i,value in ipairs(W.callbacks[name])do if value==cb then table.remove(W.callbacks[name],i);return end end
   error('duplicate or foreign removal')
  end
 }
end
E={Events=events,unitID=0,scope=function()if W.scopeThrow then error('scope')end;return W.turn end,
 snapshot=function()W.reads=W.reads+1;if W.snapshotThrow then error('snapshot')end;return W.snap end}
function Emit(name,...)
 local list={};for i,fn in ipairs(W.callbacks[name])do list[i]=fn end
 for _,fn in ipairs(list)do fn(...)end
end
'''

class MissionaryEventTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True);self.lua.execute(FIXTURE)
        path=Path(os.environ.get('BAIQI_MISSIONARY_EVENT_SOURCE') or ROOT/'tools/lua/diagnostic_missionary_events.lua')
        self.m=self.lua.execute(path.read_text(encoding='utf-8'));self.w=self.lua.globals().W;self.e=self.lua.globals().E

    def install(self):
        self.h=self.m.Install(self.e);self.lua.globals().H=self.h;return self.h

    def emit(self,expr="Emit('UnitChargesChanged',0,0,0,1)"):
        self.lua.execute(expr)

    def test_zero_actor_exact_static_bindings_and_trailing_nil_argc(self):
        h=self.install();self.emit("Emit('UnitChargesChanged',0,0,nil,1,nil)")
        r=h.samples[1]
        self.assertEqual((r.event,r.turn,r.argc,r.args[4],r.snapshotStatus),('UnitChargesChanged',138,5,1,'RAW'))
        self.assertIsNone(r.args[3]);self.assertIsNone(r.args[5])

    def test_foreign_owner_actor_and_scope_are_not_read(self):
        h=self.install()
        self.emit("Emit('UnitChargesChanged',1,0,0,1);Emit('UnitRemovedFromMap',0,1)")
        self.w.turn=-1;self.emit();self.w.turn=None;self.emit()
        self.w.scopeThrow=True;self.emit()
        self.assertEqual(self.w.reads,0);self.assertEqual(len(h.samples),0)
        self.assertEqual((h.ignored,h.errors),(2,1))

    def test_args_and_snapshot_are_bounded_detached_raw_values(self):
        h=self.install();self.emit()
        self.w.snap.charges=99;self.assertEqual(h.samples[1].snapshot.charges,1)
        for expr in ("Emit('UnitChargesChanged',0,0,1,2,3,4,5,6,7)",
                     "Emit('UnitChargesChanged',0,0,{})",
                     "Emit('UnitChargesChanged',0,0,0/0)",
                     "Emit('UnitChargesChanged',0,0,string.rep('x',129))"):
            before=self.w.reads;self.emit(expr);r=h.samples[len(h.samples)]
            self.assertEqual(r.snapshotStatus,'UNKNOWN');self.assertIsNone(r.snapshot)
            self.assertEqual(self.w.reads,before)
            self.assertIsNone(r.args[9])

    def test_unknown_snapshot_keeps_event_without_false_known_or_escape(self):
        for change in ("W.snapshotThrow=true","W.snap=nil","W.snap={nested={}}",
                       "W.snap=setmetatable({},{})",
                       "W.snap={};for i=1,33 do W.snap['key'..i]=i end"):
            with self.subTest(change=change):
                self.setUp();h=self.install();self.lua.execute(change);self.emit()
                self.assertEqual((len(h.samples),h.errors),(1,1))
                self.assertEqual(h.samples[1].snapshotStatus,'UNKNOWN')
                self.assertIsNone(h.samples[1].snapshot)

    def test_drop_bound_stops_snapshot_reads(self):
        self.e.maxRecords=1;h=self.install();self.emit();self.emit()
        self.assertEqual((len(h.samples),h.matches,h.drops,self.w.reads),(1,2,1,1))

    def test_all_ports_and_bounds_validate_before_first_add(self):
        for change in ("E.Events.UnitRemovedFromMap.Remove=nil","E.scope=nil","E.snapshot=nil",
                       "E.unitID=-1","E.maxRecords=0","E.maxRecords=129","E.maxRecords=false"):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change)
                with self.assertRaises(Exception):self.install()
                self.assertEqual(self.w.addCalls,0)

    def test_add_failure_after_attachment_removes_current_and_prior_callbacks(self):
        for throw in (False,True):
            with self.subTest(throw=throw):
                self.setUp();self.w.addFailure='UnitOperationDeactivated';self.w.addThrow=throw
                with self.assertRaises(Exception):self.install()
                self.assertTrue(self.lua.eval("(function()for _,v in pairs(W.callbacks)do if #v~=0 then return false end end;return true end)()"))

    def test_partial_restore_retries_only_failed_exact_callback_and_stops_capture(self):
        for throw in (False,True):
            with self.subTest(throw=throw):
                self.setUp();h=self.install();self.w.removeFailure='UnitOperationStarted';self.w.removeThrow=throw
                self.assertFalse(h.Restore());self.assertFalse(h.active);self.assertFalse(h.restored)
                self.emit("Emit('UnitOperationStarted',0,0,1592408602)")
                self.assertEqual(len(h.samples),0)
                self.w.removeFailure=None;self.assertTrue(h.Restore());self.assertTrue(h.Restore())
                self.assertEqual(self.w.removeCalls['UnitOperationStarted'],2)
                self.assertEqual(self.w.removeCalls['UnitChargesChanged'],1)
                self.assertTrue(h.restored)

if __name__=='__main__':unittest.main()
