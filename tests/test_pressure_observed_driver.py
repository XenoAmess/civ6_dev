"""Scheduling/receipts with33 contract doubles, not a Native performance proof."""
from pathlib import Path
from lupa.lua51 import LuaRuntime as Lua51
from uuid import uuid4
import json,unittest
from tests.observed_driver_harness import DriverHarness
from tools.run_observed_acceptance import run


class PressureObservedDriverTests(unittest.TestCase):
    def case(self,first=6):
        h=DriverHarness();h.world.turn=first
        h.lua.execute("P6Q20PressureBuild={source='baiqi142-pressure-observed-v1',source_version=142}")
        h.lua.globals().P6Q20PressureBuild.initial_turn=first
        ledger=Path('.local-model/pressure-observed-driver-tests')/uuid4().hex;calls=[];h.pressure_callback_times=[]
        def callback(turn,token):
            self.assertTrue(h.all_recording(True));self.assertEqual(h.world.turn,turn)
            intent=json.loads((ledger/f'end{turn}.json').read_text(encoding='utf-8'))
            self.assertEqual(intent['token'],token);self.assertEqual(intent['initial_turn'],first)
            calls.append(turn)
            h.pressure_callback_times.append((turn,h.now()))
            if h.advance:h.world.turn+=1;h._anchor(int(h.world.turn))
            return dict(turn=turn,token=token,requested=True,forced=False)
        def execute(cb=None,**options):
            return run(h.query,h.diplomacy_visible,h.now,h.sleep,h.emit,ledger,sample_budget=4096,
                       request_normal_end=callback if cb is None else cb,pressure_initial_turn=first,**options)
        return h,ledger,calls,callback,execute

    def test_six_actual_ends_five_windows_close_without_closing_end(self):
        for first in(0,6,2147483641):
            h,ledger,calls,cb,execute=self.case(first);r=execute()
            self.assertEqual(calls,list(range(first,first+6)));self.assertEqual(r['requested_turns'],calls)
            self.assertEqual(r['window_turns'],list(range(first+1,first+6)));self.assertEqual(r['closing_turn'],first+6)
            self.assertEqual((r['source'],r['source_version'],r['initial_turn']),('baiqi142-pressure-observed-v1',142,first))
            self.assertFalse((ledger/f'end{first+6}.json').exists());self.assertTrue(h.all_recording(False))
            self.assertEqual(h.actions,[])
            for t,at in h.pressure_callback_times[1:]:self.assertGreaterEqual(at,h.anchor_times[t]+10)
            self.assertFalse(any('UserForced'in q or'UI.RequestAction('in q for q in h.queries))
            parser=Lua51()
            for code in h.queries:parser.compile(code)

    def test_invalid_configuration_before_ledger_or_query(self):
        for first,budget,forced in((True,4096,False),(6.0,4096,False),(-1,4096,False),(2147483642,4096,False),(6,4095,False),(6,4096,True)):
            h,ledger,calls,cb,execute=self.case()
            with self.assertRaises(ValueError):run(h.query,h.diplomacy_visible,h.now,h.sleep,h.emit,ledger,
                sample_budget=budget,request_normal_end=cb,legacy_forced=forced,pressure_initial_turn=first)
            self.assertFalse(ledger.exists());self.assertEqual(h.queries,[]);self.assertEqual(calls,[])

    def test_missing_or_wrong_build_and_stage_headers_never_end(self):
        for edit in('P6Q20PressureBuild=nil',"P6Q20PressureBuild.source='wrong'",'P6Q20PressureBuild.source_version=141','P6Q20PressureBuild.initial_turn=1'):
            h,ledger,calls,cb,execute=self.case();h.lua.execute(edit)
            with self.assertRaises(Exception):execute()
            self.assertEqual(calls,[]);self.assertEqual(h.actions,[]);self.assertTrue(h.all_recording(False))
        h,ledger,calls,cb,execute=self.case();original=h.query
        def corrupt(context,code):
            if 'P6_Q20_STATE'in code:h.lua.execute('P6Q20StageB.initial_turn=0')
            return original(context,code)
        h.query=corrupt
        with self.assertRaises(Exception):execute()
        self.assertEqual(calls,[6]);self.assertTrue(h.all_recording(False))

    def test_lost_ready_and_action_ack_not_replayed(self):
        h,ledger,calls,cb,execute=self.case();original=h.query
        def lose(context,code):
            result=original(context,code)
            if 'P6_Q20_READY'in code:raise OSError('unknown READY')
            return result
        h.query=lose
        with self.assertRaises(OSError):execute()
        self.assertEqual(calls,[]);self.assertTrue(h.all_recording(False))
        h,ledger,calls,cb,execute=self.case()
        def lost(turn,token):cb(turn,token);raise OSError('unknown action ACK')
        with self.assertRaises(OSError):execute(lost)
        self.assertEqual(calls,[6]);self.assertEqual(len(list(ledger.glob('end*.json'))),1);self.assertTrue(h.all_recording(False))

    def test_no_activation_timeout_and_bad_receipt(self):
        h,ledger,calls,cb,execute=self.case();h.advance=False
        with self.assertRaises(TimeoutError):execute()
        self.assertEqual(calls,[6]);self.assertTrue(h.all_recording(False))
        h,ledger,calls,cb,execute=self.case()
        def bad(turn,token):return dict(cb(turn,token),source='paired')
        with self.assertRaises(RuntimeError):execute(bad)
        self.assertEqual(calls,[6]);self.assertTrue(h.all_recording(False))

    def test_readonly_fault_and_diplomacy_delay_preserve_ends(self):
        h,ledger,calls,cb,execute=self.case();h.fail_poll_once=True;start=[]
        def visible(_):
            if h.world.turn==8 and not start:start.append(h.now())
            return h.world.turn==8 and h.now()<start[0]+3
        h.visibility=visible;r=execute()
        self.assertEqual(calls,[6,7,8,9,10,11]);self.assertEqual(r['turn'],12)
        self.assertTrue(h.all_recording(False));self.assertTrue(any('READONLY_POLL_TRANSPORT'in line for line in h.logs))
