import unittest
from tools.plan_stage_readiness import closing_ready,pressure_closing_ready


class PressureReadinessTests(unittest.TestCase):
    def ready(self,first=6,**changes):
        args=dict(initial_turn=first,turn=first+6,anchor=1000,active=True,busy=False,processing=False,
                  pending=0,recorded=25,validated=25,errors=0)
        return pressure_closing_ready(**dict(args,**changes))

    def test_actual_t0_t6_max_and_legacy_do_not_relabel(self):
        for first in(0,6,2147483641):
            self.assertTrue(self.ready(first))
            for turn in range(first,first+6):self.assertFalse(self.ready(first,turn=turn))
        self.assertTrue(closing_ready(91,1000,True,False,False,0,25,25,0))
        with self.assertRaises(ValueError):closing_ready(12,1000,True,False,False,0,25,25,0)
        self.assertTrue(self.ready(6,turn=12))

    def test_pending_flags_or_missing_anchor_wait(self):
        for changes in({'active':False},{'busy':True},{'processing':True},{'pending':1,'validated':24},{'anchor':None}):
            self.assertFalse(self.ready(**changes))
        self.assertTrue(self.ready())

    def test_invalid_calendar_types_and_ranges_raise(self):
        for first in(True,6.0,-1,2147483642,None):
            with self.assertRaises(ValueError):pressure_closing_ready(first,12,1000,True,False,False,0,25,25,0)
        for turn in(True,12.0,5,13):
            with self.assertRaises(ValueError):self.ready(turn=turn)

    def test_invalid_flags_counters_and_proof_raise(self):
        for changes in({'active':1},{'busy':None},{'processing':'false'},{'pending':False},{'recorded':25.0},
                        {'recorded':-1},{'validated':2147483648},{'errors':1},{'pending':1},{'validated':24}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.ready(**changes)

    def test_bad_anchor_is_not_treated_as_missing(self):
        for anchor in(False,'1000',float('nan'),float('inf'),0,-1,10**1000):
            with self.subTest(anchor=type(anchor)),self.assertRaises(ValueError):self.ready(anchor=anchor)
