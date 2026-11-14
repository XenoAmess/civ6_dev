"""Real prefix, bridge, clock and END API; synthetic UI transport only."""
import json,unittest
from tests import test_paired_normal_driver as normal
from tools.build_static_control import clock_prelude
from tools.run_paired_acceptance import run
from tools.paired_player_callback import make_callback


class PressureHarness(normal.NormalHarness):
    def __init__(self,first=1,**kwargs):
        super().__init__(source_version=142,**kwargs);self.first=first;self.t.turn=first
        self.lua.execute('assert(P6PairEndOwner.Retire());P6PairEndOwner=nil')
        self.lua.execute(clock_prelude(normal_end_bridge=True,source_version=142,pressure_initial_turn=first))
        self.t.visitAt=first+2
        self.lua.execute('''Game.IsAllowStrategicCommands=function()return true end;UI.CanEndTurn=function()return true end
UI.RequestAction=function(...)assert(select('#',...)==1 and (...)==2)
 T.actions[#T.actions+1]=T.turn;T.nextAt=T.time+2;if T.visit and T.turn==T.visitAt then T.diplomacy=true end end''')
        self.child_calls=[]
    def child(self,mode,turn,seq):
        self.child_calls.append((mode,turn,seq));self.sleep(1)
        return 'P6_PAIR142_NO_NEW_LEGAL_MILITARY_SKIP'
    def record(self,name,value):
        with(self.ledger/(name+'.json')).open('x',encoding='utf-8')as f:json.dump(value,f)
    def callback(self):
        return make_callback(self.query,self.child,self.record,self.visible,pressure_initial_turn=self.first)
    def run(self,callback=None,**kwargs):
        return run(self.query,self.visible,self.close,self.now,self.sleep,self.emit,self.ledger,
                   variant=kwargs.pop('variant','enabled'),fixture_sha256='0'*64,expected_source_version=142,
                   request_normal_end=self.callback()if callback is None else callback,
                   pressure_initial_turn=self.first,**kwargs)


class PressurePairedDriverTests(unittest.TestCase):
    def test_all_five_actual_segments_and_no_closing_end(self):
        for first in(0,1,2147483641):
            h=PressureHarness(first);r=h.run()
            self.assertEqual(r['requested_turns'],list(range(first,first+5)))
            self.assertEqual(list(h.t.actions.values()),r['requested_turns'])
            self.assertEqual([x['from_turn']for x in r['records']],r['requested_turns'])
            self.assertEqual([x['seconds']for x in r['records']],[2]*5)
            self.assertEqual((r['source'],r['initial_turn'],r['source_version']),('baiqi142-pressure-paired-v1',first,142))
            self.assertEqual(h.t.turn,first+5);self.assertFalse((h.ledger/f'end-{first+5}.json').exists())
            self.assertTrue(h.lua.eval('P6PairClock:Snapshot().retired'));self.assertFalse(h.lua.eval('P6PairEndOwner.active'))
            self.assertEqual([t for mode,t,seq in h.child_calls],r['requested_turns'])

    def test_invalid_calendar_source_and_forced_fail_before_ledger(self):
        for value,source,forced in[(True,142,False),(-1,142,False),(2147483642,142,False),(1,140,False),(1,142,True)]:
            h=PressureHarness()
            with self.assertRaises(ValueError):run(h.query,h.visible,h.close,h.now,h.sleep,h.emit,h.ledger,
                variant='enabled',fixture_sha256='0'*64,expected_source_version=source,
                request_normal_end=h.callback(),pressure_initial_turn=value,legacy_forced=forced)
            self.assertFalse(h.ledger.exists());self.assertEqual(len(h.t.actions),0)
        for value in(True,1.0,-1,2147483642):
            h=PressureHarness()
            with self.assertRaises(ValueError):make_callback(h.query,h.child,h.record,h.visible,pressure_initial_turn=value)
            self.assertEqual(h.child_calls,[])
        h=PressureHarness();cb=h.callback()
        for turn,token in((0,'a'*32),(6,'a'*32),(True,'a'*32),(1,None)):
            with self.assertRaises(ValueError):cb(turn,token)
        self.assertEqual(h.child_calls,[]);self.assertFalse(h.ledger.exists())

    def test_wrong_owner_and_stage_headers_refuse_without_action(self):
        for edit in("P6PairEndOwner.entry.marker='old'","P6PairEndOwner.entry.source='wrong'","P6PairEndOwner.entry.initial_turn=85"):
            h=PressureHarness();h.lua.execute(edit)
            with self.assertRaises(Exception):h.run()
            self.assertEqual(len(h.t.actions),0);self.assertEqual(h.child_calls,[])
        h=PressureHarness();cb=h.callback()
        def corrupt(turn,token):h.lua.execute('P6PairStage.initial_turn=85');return cb(turn,token)
        with self.assertRaises(Exception):h.run(corrupt)
        self.assertEqual(len(h.t.actions),0);self.assertTrue(h.lua.eval('P6PairClock:Snapshot().retired'))

    def test_lost_ready_ack_and_post_action_transport_never_replay(self):
        h=PressureHarness();h.ready_unknown=True
        with self.assertRaises(OSError):h.run()
        self.assertEqual(h.child_calls,[]);self.assertEqual(len(h.t.actions),0)
        h=PressureHarness(lose_end=1)
        with self.assertRaises(OSError):h.run()
        self.assertEqual(list(h.t.actions.values()),[1]);self.assertEqual(len(list(h.ledger.glob('end-*.json'))),1)
        self.assertEqual(h.lua.eval('P6PairClock:Snapshot().pending.from_turn'),1)
        self.assertTrue(h.lua.eval('P6PairClock:Snapshot().retired'))

    def test_diplomacy_and_readonly_fault_preserve_order(self):
        h=PressureHarness(visit=True,poll_fault_after_close=True);r=h.run()
        self.assertEqual(h.close_calls,1);self.assertEqual(list(h.t.actions.values()),[1,2,3,4,5])
        self.assertEqual(r['phase'],'COMPLETE');self.assertIn('PAIR_READONLY_POLL OSError',h.messages)
        h=PressureHarness(visit=True,close_unknown=True)
        with self.assertRaises(OSError):h.run()
        self.assertEqual(list(h.t.actions.values()),[1,2,3]);self.assertEqual(h.close_calls,1)

    def test_timeout_and_bad_receipt_leave_one_attempt(self):
        h=PressureHarness(never_activate=True)
        with self.assertRaises(TimeoutError):h.run()
        self.assertEqual(list(h.t.actions.values()),[1]);self.assertEqual(h.lua.eval('P6PairClock:Snapshot().pending.from_turn'),1)
        h=PressureHarness()
        def bad(turn,token):return dict(turn=turn,token=token,requested=True,forced=False,initial_turn=True,source='baiqi142-pressure-paired-v1',source_version=142)
        with self.assertRaisesRegex(RuntimeError,'issuance receipt'):h.run(bad)
        self.assertEqual(len(h.t.actions),0);self.assertEqual(len(list(h.ledger.glob('end-*.json'))),1)
        h=PressureHarness();h.lua.execute('UI.CanEndTurn=function()return false end')
        with self.assertRaises(Exception):h.run()
        self.assertEqual(len(h.t.actions),0);self.assertIsNone(h.lua.eval('P6PairClock:Snapshot().pending'))
        self.assertEqual(h.child_calls,[('select',1,1)])

    def test_real_driver_captures_feed_pressure_analyzer(self):
        from tools.analyze_paired_turns import analyze_pressure_pairs
        pairs=[]
        for i in range(1,6):
            order=['enabled','control']if i%2 else['control','enabled'];pair=dict(pair=i,order=order)
            for variant in order:pair[variant]=PressureHarness().run(variant=variant)
            pairs.append(pair)
        result=analyze_pressure_pairs(pairs,'0'*64,initial_turn=1)
        self.assertEqual(len(result['matched_rows']),25);self.assertTrue(result['observed_b_delta_budget_ok'])
        self.assertEqual({r['turn']for r in result['matched_rows']},{2,3,4,5,6})
        self.assertEqual(result['pressure_distributions']['delta_ms']['max'],0)
