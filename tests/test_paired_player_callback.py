"""Real clock/bridge endpoint plus external-player preparation failure boundaries."""
import unittest
from lupa.lua53 import LuaError
from test_paired_normal_driver import NormalHarness,execute
from tools import paired_player_callback as subject


class PairedPlayerCallbackTests(unittest.TestCase):
    def setup_case(self):
        h=NormalHarness(source_version=142)
        h.lua.execute('Game.IsAllowStrategicCommands=function()return true end;UI.CanEndTurn=function()return true end')
        events=[];records={};children=[]
        def record(stem,data):
            if stem in records:raise FileExistsError(stem)
            events.append(stem);records[stem]=data
        def query(context,code):
            events.append('query');return h.query(context,code)
        def child(mode,turn,seq):
            children.append((mode,turn,seq));events.append(mode);h.sleep(3)
            if mode=='select':return 'P6_PAIR142_VIEW_NEXT_SKIP_ELIGIBLE'if seq==1 else'P6_PAIR142_NO_NEW_LEGAL_MILITARY_SKIP'
            return 'P6_PAIR142_NORMAL_TESTPLAYER_SKIP'
        def make(**overrides):
            deps=dict(query=query,child=child,record=record,is_diplomacy_visible=lambda:False,expected_source_version=142)
            deps.update(overrides);return subject.make_callback(**deps)
        h.lua.execute("P6PairStage={phase='RECORDING',token='"+'a'*32+"',normal_end=true,source_version=142,ends={[85]=true}}")
        return h,events,records,children,make

    def test_five_actual_clock_segments_exclude_preparation_and_stop90(self):
        h,events,records,children,make=self.setup_case();h.lua.execute('P6PairStage=nil')
        result=execute(h,make(),expected_source_version=142)
        self.assertEqual(list(h.t.actions.values()),list(range(85,90)))
        self.assertEqual([r['seconds']for r in result['records']],[2]*5)
        self.assertEqual(result['source_version'],142)
        self.assertEqual(len(children),15)
        for t in range(85,90):
            self.assertLess(events.index(f'issuance-{t}-attempt'),events.index(f'issuance-{t}-returned'))
            self.assertEqual(set(records[f'issuance-{t}-returned']['ack']),{'turn','token','requested','forced'})

    def test_diplomacy_appearing_after_select_prevents_step_and_end(self):
        h,events,records,children,make=self.setup_case()
        with self.assertRaisesRegex(RuntimeError,'Diplomacy'):
            make(is_diplomacy_visible=lambda:not not children)(85,'a'*32)
        self.assertEqual(children,[('select',85,1)]);self.assertEqual(len(h.t.actions),0)

    def test_sixty_unexhausted_selections_never_issue_end(self):
        h,events,records,children,make=self.setup_case();calls=[]
        def child(mode,*args):
            calls.append(mode)
            return 'P6_PAIR142_VIEW_NEXT_SKIP_ELIGIBLE'if mode=='select'else'P6_PAIR142_NORMAL_TESTPLAYER_SKIP'
        with self.assertRaisesRegex(RuntimeError,'bound'):make(child=child)(85,'a'*32)
        self.assertEqual(calls.count('select'),60);self.assertEqual(len(h.t.actions),0)

    def test_action_then_lost_receipt_cannot_be_replayed(self):
        h,events,records,children,make=self.setup_case();h.lose_end=85;cb=make()
        with self.assertRaises(OSError):cb(85,'a'*32)
        self.assertIn('issuance-85-attempt',records)
        self.assertNotIn('issuance-85-returned',records)
        with self.assertRaises(FileExistsError):cb(85,'a'*32)
        self.assertEqual(list(h.t.actions.values()),[85])

    def test_control_queue_block_never_starts_clock_or_fills_domestic_work(self):
        h,events,records,children,make=self.setup_case()
        h.lua.execute('UI.CanEndTurn=function()return false end')
        with self.assertRaises(LuaError):make()(85,'a'*32)
        self.assertEqual(len(h.t.actions),0)
        self.assertIsNone(h.lua.eval('P6PairClock:Snapshot().pending'))
        self.assertEqual(set(c[0]for c in children),{'select','step'})

    def test_unknown_selection_skip_and_exception_stop_before_end(self):
        for mode in ('ambiguous','unknown_skip','exception'):
            with self.subTest(mode=mode):
                h,events,records,children,make=self.setup_case();calls=[]
                def child(which,*args):
                    calls.append(which)
                    if mode=='exception':raise OSError('unknown selection outcome')
                    if which=='select':return 'P6_PAIR142_VIEW_NEXT_SKIP_ELIGIBLE'+(' P6_PAIR142_NO_NEW_LEGAL_MILITARY_SKIP'if mode=='ambiguous'else'')
                    return 'unknown'
                with self.assertRaises((RuntimeError,OSError)):make(child=child)(85,'a'*32)
                self.assertEqual(len(h.t.actions),0)
                self.assertNotIn('issuance-85-attempt',records)

    def test_reservation_failure_precedes_selection_and_issuance_failure_precedes_end(self):
        for fail in ('callback-85-attempt','issuance-85-attempt'):
            with self.subTest(fail=fail):
                h,events,records,children,make=self.setup_case()
                def record(stem,data):
                    if stem==fail:raise OSError('disk full')
                with self.assertRaises(OSError):make(record=record)(85,'a'*32)
                self.assertEqual(len(h.t.actions),0)
                if fail.startswith('callback'):self.assertEqual(children,[])

    def test_invalid_python_arguments_fail_before_external_work(self):
        for turn,token in ((True,'a'*32),(85.,'a'*32),(90,'a'*32),(85,'A'*32),(85,None)):
            h,events,records,children,make=self.setup_case()
            with self.assertRaises(ValueError):make()(turn,token)
            self.assertEqual(events,[])
        for version in (True,140,142.,143):
            h,events,records,children,make=self.setup_case()
            with self.assertRaises(ValueError):make(expected_source_version=version)
            self.assertEqual(events,[])


if __name__=='__main__':unittest.main()
