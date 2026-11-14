"""Isolated providers only; these checks do not establish Native event semantics."""
from pathlib import Path
import importlib
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'tools/lua/diagnostic_operation_event.lua'


class OperationEventTests(unittest.TestCase):
    def runtimes(self):
        for version in ('lua51','lua53'):
            with self.subTest(version=version):
                runtime=importlib.import_module('lupa.'+version).LuaRuntime(unpack_returned_tuples=True)
                runtime.globals().New=runtime.execute(SOURCE.read_text(encoding='utf-8'))
                runtime.execute('''S={adds=0,removes=0,clockReads=0,turnReads=0,pid=0};env={
                  Add=function(fn)S.adds=S.adds+1;S.fn=fn end,
                  Remove=function(fn)S.removes=S.removes+1;assert(fn==S.fn);S.removed=fn end,
                  Now=function()S.clockReads=S.clockReads+1;return 12.25 end,
                  GetLocal=function()return S.pid end,
                  GetTurn=function()S.turnReads=S.turnReads+1;return 333 end}''')
                yield runtime

    def test_owned_record_preserves_time_turn_ids_and_types(self):
        for l in self.runtimes():
            l.execute('h=New(env,64);S.fn(0,8650807,-123)')
            self.assertEqual(l.eval('type(New)'),'function')
            self.assertEqual(l.eval('#h.samples'),1)
            for key,value in dict(ownerID=0,unitID=8650807,operationID=-123,turn=333,time=12.25,argc=3,qualified=True).items():
                self.assertEqual(l.eval('h.samples[1]')[key],value)
            self.assertEqual(l.eval('#h.samples[1].argtypes'),3)
            self.assertEqual(l.eval('h.errors'),0)

    def test_nil_and_long_arity_remain_unqualified_without_copying_extra_objects(self):
        for l in self.runtimes():
            l.execute('h=New(env,64);S.fn(0,1,2,nil);S.fn(0,1,2,nil,{},nil,{},nil,nil,nil)')
            self.assertEqual(l.eval('h.samples[1].argc'),4)
            self.assertEqual(l.eval('h.samples[1].argtypes[4]'),'nil')
            self.assertEqual(l.eval('h.samples[2].argc'),10)
            self.assertEqual(l.eval('#h.samples[2].argtypes'),8)
            self.assertEqual(l.eval('h.samples[2].argtypes[5]'),'table')
            self.assertFalse(l.eval('h.samples[1].qualified'))
            self.assertFalse(l.eval('h.samples[2].qualified'))
            self.assertEqual(l.eval('h.invalid'),2)

    def test_foreign_owner_and_nonzero_local_do_not_read_world_metadata(self):
        for l in self.runtimes():
            l.execute('h=New(env,8);S.fn(1,1,2);S.pid=1;S.fn(1,1,2)')
            self.assertEqual(l.eval('h.ignored'),1)
            self.assertEqual(l.eval('h.invalid'),1)
            self.assertEqual(l.eval('S.clockReads+S.turnReads'),0)
            self.assertEqual(l.eval('#h.samples'),0)

    def test_bad_ids_clock_and_turn_never_become_records(self):
        for l in self.runtimes():
            l.execute("h=New(env,8);S.fn(0,-1,2);S.fn(0,1,4294967296);env.Now=function()return 0/0 end;S.fn(0,1,2);env.Now=function()return -1 end;S.fn(0,1,2);env.GetTurn=function()return '333' end;S.fn(0,1,2)")
            self.assertEqual(l.eval('h.invalid'),5)
            self.assertEqual(l.eval('#h.samples'),0)

    def test_capacity_and_disabled_callback_are_bounded(self):
        for l in self.runtimes():
            l.execute('h=New(env,1);S.fn(0,1,2);S.fn(0,2,2);assert(h.Retire());S.fn(0,3,2)')
            self.assertEqual(l.eval('#h.samples'),1)
            self.assertEqual(l.eval('h.dropped'),1)
            self.assertEqual(l.eval('h.seen'),2)

    def test_retire_removes_same_owned_callback_once(self):
        for l in self.runtimes():
            l.execute('h=New(env,1);assert(h.Retire()==true and h.Retire()==true)')
            self.assertEqual(l.eval('S.removes'),1)
            self.assertFalse(l.eval('h.enabled'))
            self.assertFalse(l.eval('h.subscribed'))
            self.assertTrue(l.eval('h.retired and h.cleanupKnown'))

    def test_add_after_binding_error_cleans_own_callback_without_rebinding(self):
        for l in self.runtimes():
            l.execute("env.Add=function(fn)S.adds=S.adds+1;S.fn=fn;error('unknown bind')end;h=New(env,1);S.fn(0,1,2)")
            self.assertEqual(l.eval('S.adds'),1)
            self.assertEqual(l.eval('S.removes'),1)
            self.assertEqual(l.eval('h.errors'),1)
            self.assertFalse(l.eval('h.enabled or h.subscribed'))
            self.assertTrue(l.eval('h.retired and h.cleanupKnown'))
            self.assertEqual(l.eval('#h.samples'),0)

    def test_unknown_remove_does_not_claim_unsubscribed_or_retry(self):
        for l in self.runtimes():
            l.execute("env.Remove=function(fn)S.removes=S.removes+1;assert(fn==S.fn);error('unknown removal')end;h=New(env,1);assert(h.Retire()==false and h.Retire()==false);S.fn(0,1,2)")
            self.assertEqual(l.eval('S.removes'),1)
            self.assertIsNone(l.eval('h.subscribed'))
            self.assertFalse(l.eval('h.cleanupKnown or h.enabled'))
            self.assertEqual(l.eval('h.errors'),1)
            self.assertEqual(l.eval('#h.samples'),0)

    def test_invalid_dependencies_and_capacity_fail_before_add(self):
        for l in self.runtimes():
            l.execute('''for _,v in ipairs({0,4097,1.5,true})do assert(not pcall(New,env,v))end
              for _,k in ipairs({'Add','Remove','Now','GetLocal','GetTurn'})do
                local old=env[k];env[k]=true;assert(not pcall(New,env,8));env[k]=old
              end''')
            self.assertEqual(l.eval('S.adds'),0)
            self.assertEqual(l.eval('S.clockReads+S.turnReads'),0)

    def test_metadata_errors_do_not_escape_native_event_provider(self):
        for l in self.runtimes():
            l.execute("h=New(env,8);env.Now=function()error('clock')end;assert(pcall(S.fn,0,1,2));env.Now=function()return 1 end;env.GetTurn=function()error('turn')end;assert(pcall(S.fn,0,1,2));env.GetLocal=function()error('local')end;assert(pcall(S.fn,0,1,2))")
            self.assertEqual(l.eval('h.errors'),3)
            self.assertEqual(l.eval('#h.samples'),0)


if __name__=='__main__':unittest.main()
