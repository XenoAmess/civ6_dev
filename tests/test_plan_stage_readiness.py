import unittest
from tools.plan_stage_readiness import closing_ready


class ClosingReadinessTests(unittest.TestCase):
    def ready(self,**changes):
        args=dict(turn=91,anchor=1000,active=True,busy=False,processing=False,
                  pending=0,recorded=25,validated=25,errors=0)
        return closing_ready(**dict(args,**changes))

    def test_actual_turn_can_precede_native_anchor(self):
        self.assertFalse(self.ready(anchor=None))
        self.assertTrue(self.ready())

    def test_pending_and_ui_wait_without_changing_counters(self):
        self.assertFalse(self.ready(pending=1,validated=24))
        for changes in ({'active':False},{'busy':True},{'processing':True}):
            self.assertFalse(self.ready(**changes))

    def test_previous_valid_turns_never_close(self):
        for turn in range(85,91):self.assertFalse(self.ready(turn=turn))

    def test_bad_proof_never_waits_as_clean(self):
        for changes in ({'errors':1},{'pending':1},{'validated':24},{'validated':26},
                        {'recorded':-1},{'pending':False},{'errors':0.0},{'recorded':2147483648}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.ready(**changes)

    def test_unknown_anchor_is_not_a_missing_anchor(self):
        for anchor in (False,'1000',float('nan'),float('inf'),0,-1,10**1000):
            with self.subTest(anchor=type(anchor)),self.assertRaises(ValueError):self.ready(anchor=anchor)

    def test_unknown_turn_or_flags_raise(self):
        for changes in ({'turn':True},{'turn':91.0},{'turn':92},{'turn':84},
                        {'active':1},{'busy':None},{'processing':'false'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.ready(**changes)


if __name__=='__main__':unittest.main()
