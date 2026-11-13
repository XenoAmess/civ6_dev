"""Use the real private clock/bridge; cross-context execution is a fixture."""
import unittest
from lupa.lua53 import LuaError
from test_paired_normal_driver import NormalHarness,execute
from tools.paired_normal_end import request_end


class OrdinaryEndpointTests(unittest.TestCase):
    def harness(self):
        h=NormalHarness()
        h.lua.execute('Game.IsAllowStrategicCommands=function()return true end;UI.CanEndTurn=function()return true end')
        return h

    def ready(self,h):
        token='a'*32
        h.lua.execute("P6PairStage={phase='RECORDING',token='"+token+"',normal_end=true,source_version=140,ends={[85]=true}}")
        return token

    def test_five_real_clock_segments_exclude_player_preparation(self):
        h=self.harness()
        def callback(turn,token):
            self.assertTrue((h.ledger/f'end-{turn}.json').exists())
            h.sleep(5)
            return request_end(h.query,turn,token)
        result=execute(h,callback)
        self.assertEqual(list(h.t.actions.values()),list(range(85,90)))
        self.assertEqual([r['seconds']for r in result['records']],[2]*5)
        self.assertEqual(result['end_mode'],'ORDINARY_CALLBACK')

    def test_bridge_refuses_second_call_before_any_second_action(self):
        h=self.harness();token=self.ready(h)
        self.assertEqual(request_end(h.query,85,token),dict(turn=85,token=token,requested=True,forced=False))
        with self.assertRaises(LuaError):request_end(h.query,85,token)
        self.assertEqual(list(h.t.actions.values()),[85])
        self.assertEqual(h.lua.eval('P6PairEndOwner.refused'),1)

    def test_unknown_receipt_after_action_does_not_retry(self):
        for shape in ('missing','wrong','duplicate','terminal_error'):
            with self.subTest(shape=shape):
                h=self.harness();token=self.ready(h);calls=[]
                def query(context,code):
                    calls.append(context);messages=h.query(context,code)
                    if shape=='missing':return []
                    if shape=='wrong':return [{'tag':-1,'payload':'O\0ActionPanel: P6_PAIR_ORDINARY_ISSUED\t86\t'+token}]
                    if shape=='duplicate':return messages+messages
                    return messages+[{'tag':3,'payload':'ERR:unknown after issuance'}]
                with self.assertRaises(RuntimeError):request_end(query,85,token)
                self.assertEqual(calls,['ActionPanel']);self.assertEqual(list(h.t.actions.values()),[85])

    def test_action_then_transport_error_stays_single_attempt(self):
        h=self.harness();token=self.ready(h);h.lose_end=85
        with self.assertRaisesRegex(OSError,'action executed'):request_end(h.query,85,token)
        self.assertEqual(list(h.t.actions.values()),[85])
        self.assertEqual(h.lua.eval('P6PairClock:Snapshot().pending.from_turn'),85)

    def test_invalid_python_arguments_do_not_query(self):
        for turn,token in ((True,'a'*32),(85.0,'a'*32),(84,'a'*32),(90,'a'*32),
                           (85,'a'*31),(85,'A'*32),(85,'a'*31+'"'),(85,None)):
            with self.subTest(turn=turn,token=token):
                calls=[]
                with self.assertRaises(ValueError):request_end(lambda *args:calls.append(args),turn,token)
                self.assertEqual(calls,[])

    def test_ui_and_bridge_guards_fail_before_clock_or_action(self):
        for setup in ('UI.CanEndTurn=function()return false end',
                      'Game.IsAllowStrategicCommands=function()return false end',
                      'UI.IsGameCoreBusy=function()return true end',
                      'ExposedMembers.P6BaiqiPairEndBridge=nil',
                      "ExposedMembers.P6BaiqiPairEndBridge.marker='foreign'",
                      'T.turn=86'):
            with self.subTest(setup=setup):
                h=self.harness();token=self.ready(h);h.lua.execute(setup)
                with self.assertRaises(LuaError):request_end(h.query,85,token)
                self.assertEqual(len(h.t.actions),0)
                self.assertIsNone(h.lua.eval('P6PairClock:Snapshot().pending'))
                self.assertEqual(h.lua.eval('P6PairEndOwner.refused'),0)


if __name__=='__main__':unittest.main()
