import unittest
from tools.tuner_context_contract import checked_call,context_realm

class TunerContextContractTests(unittest.TestCase):
    def test_ui_cannot_enter_a_core_call(self):
        entered=[]
        for context in ['WorldInput','BaiqiExecutor','MainMenu']:
            with self.assertRaises(ValueError):
                checked_call(lambda *a:entered.append(a),context,'side_effect()',expected_realm='CORE')
        self.assertEqual(entered,[])

    def test_unknown_or_ambiguous_declaration_rejected_before_dispatch(self):
        entered=[]
        for context,realm in [('BaiqiGamePlay','CORE'),('OtherContext','CORE'),('BaiqiGameplay','CORE '),('BaiqiGameplay',None),('BaiqiGameplay','UI')]:
            with self.assertRaises(ValueError):
                checked_call(lambda *a:entered.append(a),context,'query()',expected_realm=realm)
        self.assertEqual(entered,[])

    def test_correct_context_dispatched_once_and_result_preserved(self):
        entered=[];result=object()
        def query(*args):entered.append(args);return result
        self.assertIs(checked_call(query,'BaiqiGameplay','original_source',expected_realm='CORE'),result)
        self.assertEqual(entered,[('BaiqiGameplay','original_source')])
        self.assertEqual(context_realm('WorldInput'),'UI')

    def test_original_error_is_never_retried_or_converted(self):
        entered=[];error=RuntimeError('original request result unavailable')
        def query(*args):entered.append(args);raise error
        with self.assertRaises(RuntimeError)as caught:
            checked_call(query,'BaiqiGameplay','original_source',expected_realm='CORE')
        self.assertIs(caught.exception,error)
        self.assertEqual(len(entered),1)

if __name__=='__main__':unittest.main()
