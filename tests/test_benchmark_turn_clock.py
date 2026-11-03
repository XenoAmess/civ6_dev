from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime,LuaError

SOURCE=(Path(__file__).resolve().parents[1]/'tools/lua/benchmark_turn_clock.lua').read_text(encoding='utf-8')


class Harness:
    def __init__(self,capacity=16,setup=''):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
T={time=100,turn=85,pid=0,clockCalls=0,turnCalls=0,pidCalls=0,addCalls=0,removeCalls=0,foreign=0,callbacks={}}
local foreign=function() T.foreign=T.foreign+1 end;T.callbacks[1]=foreign
E={Add=function(fn) assert(type(fn)=='function');T.addCalls=T.addCalls+1;T.callbacks[#T.callbacks+1]=fn;if T.addError then error('after Add') end end,
 Remove=function(fn) T.removeCalls=T.removeCalls+1;if T.removeError then error('Remove unknown') end;for i=#T.callbacks,1,-1 do if T.callbacks[i]==fn then table.remove(T.callbacks,i) end end end,
 Fire=function(...) for _,fn in ipairs(T.callbacks) do fn(...) end end}
Clock=function() T.clockCalls=T.clockCalls+1;if T.clockError then error('clock failed') end;return T.time end
Turn=function() T.turnCalls=T.turnCalls+1;if T.turnError then error('turn failed') end;return T.turn end
Pid=function() T.pidCalls=T.pidCalls+1;return T.pid end
''')
        self.lua.execute(setup);g=self.lua.globals();self.t=g.T;self.event=g.E
        self.h=self.lua.execute(SOURCE)(g.Clock,g.Turn,g.Pid,self.event,capacity)

    def snap(self):return self.h.Snapshot(self.h)
    def begin(self,turn=85):return self.h.Begin(self.h,turn)
    def fire(self,pid=0,turn=86,time=100.25):
        self.t.turn=turn;self.t.time=time;self.event.Fire(pid,False,'extra')
    def retire(self):return self.h.Retire(self.h)


class BenchmarkTurnClockTests(unittest.TestCase):
    def test_constructor_subscribes_once_without_domain_reads(self):
        h=Harness();s=h.snap()
        self.assertEqual((h.t.addCalls,h.t.clockCalls,h.t.turnCalls,h.t.pidCalls),(1,0,0,0))
        self.assertTrue(s.subscribed);self.assertFalse(s.retired);self.assertEqual(len(s.records),0)
        self.assertIsNone(s.pending);self.assertEqual(s.errors,0)

    def test_matching_local_event_records_exactly_once_other_pid_ignored(self):
        h=Harness();self.assertTrue(h.begin());h.fire(1)
        self.assertEqual((h.t.clockCalls,h.t.turnCalls),(1,1))
        h.fire();h.fire(time=999)
        s=h.snap();self.assertEqual(len(s.records),1);record=s.records[1]
        self.assertEqual((record.from_turn,record.to_turn,record.pid,record.started,record.ended,record.seconds),(85,86,0,100,100.25,.25))
        self.assertEqual((h.t.clockCalls,h.t.turnCalls,h.t.pidCalls),(2,2,1));self.assertIsNone(s.pending)

    def test_pending_duplicate_and_full_capacity_refuse(self):
        h=Harness(1);self.assertTrue(h.begin());self.assertFalse(h.begin())
        self.assertEqual((h.snap().refused,h.t.clockCalls),(1,1))
        h.fire();self.assertFalse(h.begin(86))
        self.assertEqual((h.snap().refused,len(h.snap().records),h.t.clockCalls),(2,1,2))

    def test_invalid_begin_observation_never_creates_zero_record(self):
        for setup in ('T.time=0/0','T.time=math.huge','T.time=-1','T.clockError=true','T.turn=84','T.pid=false','T.pid=2147483648'):
            with self.subTest(setup=setup):
                h=Harness(setup=setup);self.assertFalse(h.begin());s=h.snap()
                self.assertEqual((s.errors,len(s.records)),(1,0));self.assertIsNone(s.pending)
                self.assertFalse(h.begin());self.assertEqual(s.refused,0) # Snapshot counters are actual values at snapshot time.

    def test_invalid_end_poison_stops_future_intervals(self):
        for setup in ('T.time=99','T.time=0/0','T.time=math.huge','T.clockError=true','T.turnError=true','T.turn=87'):
            with self.subTest(setup=setup):
                h=Harness();self.assertTrue(h.begin());h.t.turn=86;h.lua.execute(setup);h.event.Fire(0)
                s=h.snap();self.assertEqual((s.errors,len(s.records)),(1,0));self.assertIsNone(s.pending)
                calls=h.t.clockCalls;self.assertFalse(h.begin(86));self.assertEqual(h.t.clockCalls,calls)
        h=Harness();h.t.time=0;self.assertTrue(h.begin());h.fire(time=0)
        self.assertEqual(h.snap().records[1].seconds,0)

    def test_retire_preserves_pending_and_foreign_callback(self):
        h=Harness();self.assertTrue(h.begin());self.assertTrue(h.retire());self.assertTrue(h.retire())
        s=h.snap();self.assertEqual((h.t.removeCalls,len(h.t.callbacks)),(1,1))
        self.assertTrue(s.retired);self.assertFalse(s.subscribed);self.assertEqual(s.pending.started,100)
        calls=h.t.clockCalls;h.fire();self.assertEqual((h.t.clockCalls,h.t.foreign),(calls,1));self.assertFalse(h.begin())

    def test_add_after_registration_error_is_cleaned_once(self):
        h=Harness(setup='T.addError=true');self.assertEqual(len(h.t.callbacks),2)
        self.assertEqual(h.snap().errors,1);self.assertFalse(h.snap().subscribed);self.assertFalse(h.begin())
        self.assertTrue(h.retire());self.assertTrue(h.retire())
        self.assertEqual((h.t.addCalls,h.t.removeCalls,len(h.t.callbacks)),(1,1,1))

    def test_remove_unknown_is_not_replayed_and_callback_stays_inert(self):
        h=Harness();self.assertTrue(h.begin());h.t.removeError=True
        self.assertFalse(h.retire());self.assertFalse(h.retire());h.fire()
        self.assertEqual((h.t.removeCalls,h.t.clockCalls,h.snap().errors),(1,1,1))
        self.assertTrue(h.snap().retired);self.assertFalse(h.snap().subscribed)

    def test_exact_native_integer_and_capacity_boundaries(self):
        for value in (False,True,0,-1,1.5,129,float('nan'),float('inf'),'16'):
            with self.subTest(capacity=value):
                with self.assertRaises(LuaError):Harness(value)
        for value in (False,True,-1,1.5,2147483647,1e308,float('inf'),'85'):
            with self.subTest(turn=value):
                h=Harness();self.assertFalse(h.begin(value));self.assertEqual((h.snap().errors,h.snap().refused,h.t.clockCalls),(0,1,0))


if __name__=='__main__':unittest.main()
