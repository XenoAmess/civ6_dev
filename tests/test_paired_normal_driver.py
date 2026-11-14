"""Software transport fixture using the actual source140 bridge and Native clock.

Mapping ActionPanel to one Lua runtime proves ordering, not real cross-UI access.
"""
import json
import unittest
from paired_driver_harness import Harness
from tools.build_static_control import clock_prelude
from tools.run_paired_acceptance import run


class NormalHarness(Harness):
    def __init__(self,*,source_version=140,**kwargs):
        super().__init__(**kwargs)
        self.ready_unknown=False
        self.lua.execute('ExposedMembers={};Players[0].IsTurnActive=function()return true end')
        self.lua.execute(clock_prelude(normal_end_bridge=True,source_version=source_version))
        self.lua.execute('''
UI.RequestAction=function(action,args)
 assert(action==2 and args==nil)
 T.actions[#T.actions+1]=T.turn;T.nextAt=T.time+2
 if T.visit and T.turn==87 then T.diplomacy=true end
end
local u={GetID=function()return 7 end,GetX=function()return 8 end,
 GetY=function()return 9 end,GetUnitType=function()return 1 end}
GameInfo.Units[1]={UnitType='UNIT_WARRIOR'}
Players[0].GetUnits=function()return{Members=function()
 local done=false;return function()if not done then done=true;return 1,u end end
end}end
''')

    def query(self,context,code):
        messages=super().query('BaiqiExecutor'if context=='ActionPanel'else context,code)
        if self.ready_unknown and 'P6_PAIR_READY' in code:
            self.ready_unknown=False
            raise OSError('READY executed but response unavailable')
        return messages

    def request(self,turn,token,*,begin=True):
        ledger=json.loads((self.ledger/f'end-{turn}.json').read_text(encoding='utf-8'))
        assert ledger['turn']==turn and ledger['token']==token
        assert ledger['status']=='ATTEMPTED_BEFORE_NATIVE'
        self.sleep(5)  # Test-player selection/preparation is outside the clock.
        code=(f'assert(ExposedMembers.P6BaiqiPairEndBridge.Begin({turn},{json.dumps(token)}));'if begin else'')
        self.query('ActionPanel',code+'UI.RequestAction(ActionTypes.ACTION_ENDTURN)')
        return dict(turn=turn,token=token,requested=True,forced=False)


def execute(h,callback=None,**kwargs):
    return run(h.query,h.visible,h.close,h.now,h.sleep,h.emit,h.ledger,
               variant='enabled',fixture_sha256='0'*64,
               request_normal_end=h.request if callback is None else callback,**kwargs)


class NormalPairedDriverTests(unittest.TestCase):
    def assert_retired(self,h):
        self.assertEqual(h.lua.eval('P6PairStage.phase'),'ABORTED')
        self.assertTrue(h.lua.eval('P6PairClock:Snapshot().retired'))
        self.assertFalse(h.lua.eval('P6PairEndOwner.active'))
        self.assertIsNone(h.lua.eval('ExposedMembers.P6BaiqiPairEndBridge'))

    def test_actual_clock_excludes_preparation_and_never_ends90(self):
        h=NormalHarness();result=execute(h)
        self.assertEqual(list(h.t.actions.values()),list(range(85,90)))
        self.assertEqual([r['seconds']for r in result['records']],[2]*5)
        self.assertEqual([r['from_turn']for r in result['records']],list(range(85,90)))
        self.assertEqual(result['source_version'],140)
        self.assertEqual(result['end_mode'],'ORDINARY_CALLBACK')
        self.assertIs(result['forced'],False)
        self.assertEqual(result['phase'],'COMPLETE')
        self.assertEqual(h.lua.eval('P6PairStage.baseline[1].id'),7)
        self.assertEqual(h.lua.eval('P6PairStage.baseline[1].x'),8)
        self.assertTrue(h.lua.eval('P6PairClock:Snapshot().retired'))
        self.assertFalse(h.lua.eval('P6PairEndOwner.active'))
        self.assertFalse((h.ledger/'end-90.json').exists())

    def test_action_then_callback_transport_failure_is_not_replayed(self):
        h=NormalHarness()
        def callback(turn,token):
            h.request(turn,token)
            raise OSError('ordinary action issued; ACK unknown')
        with self.assertRaisesRegex(OSError,'ACK unknown'):execute(h,callback)
        self.assertEqual(list(h.t.actions.values()),[85])
        self.assertEqual(len(list(h.ledger.glob('end-*.json'))),1)
        self.assertEqual(h.lua.eval('P6PairClock:Snapshot().pending.from_turn'),85)
        self.assert_retired(h)
        self.assertIn('PAIR_ABORT_BRIDGE_RETIRE_RECEIPT ["true"]',h.messages)

    def test_bad_receipts_abort_without_actions_or_retry(self):
        for edit in ({'forced':True},{'requested':False},{'turn':85.0},
                     {'extra':True},{'token':'wrong'}):
            with self.subTest(edit=edit):
                h=NormalHarness();calls=[]
                def callback(turn,token):
                    calls.append(turn)
                    return dict(dict(turn=turn,token=token,requested=True,forced=False),**edit)
                with self.assertRaisesRegex(RuntimeError,'issuance receipt'):execute(h,callback)
                self.assertEqual(calls,[85]);self.assertEqual(len(h.t.actions),0)
                self.assert_retired(h)

    def test_lost_ready_ack_never_calls_player(self):
        h=NormalHarness();h.ready_unknown=True;calls=[]
        with self.assertRaisesRegex(OSError,'READY executed'):
            execute(h,lambda *args:calls.append(args))
        self.assertEqual(calls,[]);self.assertEqual(len(h.t.actions),0)
        self.assertTrue(h.lua.eval('P6PairStage.ends[85]'))
        self.assert_retired(h)

    def test_action_without_clock_bridge_aborts_once(self):
        h=NormalHarness()
        with self.assertRaises(Exception):execute(h,lambda turn,token:h.request(turn,token,begin=False))
        self.assertEqual(list(h.t.actions.values()),[85]);self.assert_retired(h)
        self.assertEqual(len(list(h.ledger.glob('end-*.json'))),1)

    def test_visit_after_end_and_readonly_fault_do_not_replay(self):
        h=NormalHarness(visit=True,poll_fault_after_close=True)
        result=execute(h)
        self.assertEqual(h.close_calls,1)
        self.assertEqual(list(h.t.actions.values()),list(range(85,90)))
        self.assertIn('TEST_PLAYER_PAIR_DIPLOMACY_CALLBACK_RETURNED',h.messages)
        self.assertIn('TEST_PLAYER_PAIR_DIPLOMACY_HIDDEN_CONFIRMED',h.messages)
        self.assertIn('PAIR_READONLY_POLL OSError',h.messages)
        self.assertEqual(result['phase'],'COMPLETE')

    def test_unknown_close_never_ends_next_turn(self):
        h=NormalHarness(visit=True,close_unknown=True)
        with self.assertRaisesRegex(OSError,'close ACK unknown'):execute(h)
        self.assertEqual(h.close_calls,1)
        self.assertEqual(list(h.t.actions.values()),[85,86,87]);self.assert_retired(h)

    def test_missing_or_conflicting_mode_fails_before_ledger(self):
        for options,error in (({},TypeError),({'legacy_forced':1},TypeError),
                              ({'legacy_forced':True,'request_normal_end':lambda *a:None},ValueError)):
            with self.subTest(options=options):
                h=NormalHarness()
                with self.assertRaises(error):
                    run(h.query,h.visible,h.close,h.now,h.sleep,h.emit,h.ledger,
                        variant='enabled',fixture_sha256='0'*64,**options)
                self.assertFalse(h.ledger.exists());self.assertEqual(len(h.t.actions),0)


if __name__=='__main__':unittest.main()
