import unittest

from tools.plan_quiet_observation import observe_after_end, window_status


class Clock:
    def __init__(self):
        self.now = 10.0
        self.events = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.events.append(('sleep', self.now, seconds))
        self.now += seconds

    def end(self):
        self.events.append(('END', self.now))
        return True

    def read(self):
        self.events.append(('READ', self.now))
        return {'actual_anchor': None}


class QuietObservationTests(unittest.TestCase):
    def test_actual_end_wait_read_caller_has_no_observation_during_wait(self):
        c = Clock()
        state, proof = observe_after_end(c.end, c.read, clock=c.clock, sleep=c.sleep)
        self.assertEqual(c.events[0], ('END', 10.0))
        self.assertEqual(c.events[-1], ('READ', 40.0))
        self.assertEqual(sum(e[0] == 'END' for e in c.events), 1)
        self.assertEqual(sum(e[0] == 'READ' for e in c.events), 1)
        self.assertTrue(all(e[0] == 'sleep' for e in c.events[1:-1]))
        self.assertEqual(proof['quiet_host_seconds'], 30)
        self.assertFalse(proof['game_window_complete_proved_by_host_wait'])
        self.assertEqual(state, {'actual_anchor': None})

    def test_unknown_acknowledgements_never_sleep_or_observe(self):
        for value in (False, None, 0, 1, 'true', {}, []):
            with self.subTest(value=value):
                c = Clock()
                with self.assertRaises(ValueError):
                    observe_after_end(lambda: value, c.read, clock=c.clock, sleep=c.sleep)
                self.assertEqual(c.events, [])

    def test_end_failure_is_not_replayed(self):
        c = Clock()
        def end():
            c.events.append(('END', c.now))
            raise OSError('unknown Native result')
        with self.assertRaises(OSError):
            observe_after_end(end, c.read, clock=c.clock, sleep=c.sleep)
        self.assertEqual(c.events, [('END', 10.0)])

    def test_read_failure_is_not_retried(self):
        c = Clock()
        def read():
            c.events.append(('READ', c.now))
            raise OSError('unknown observation')
        with self.assertRaises(OSError):
            observe_after_end(c.end, read, clock=c.clock, sleep=c.sleep)
        self.assertEqual(sum(e[0] == 'READ' for e in c.events), 1)
        self.assertEqual(sum(e[0] == 'END' for e in c.events), 1)

    def test_interrupted_wait_never_observes_or_replays(self):
        c = Clock()
        def interrupted(seconds):
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            observe_after_end(c.end, c.read, clock=c.clock, sleep=interrupted)
        self.assertEqual(c.events, [('END', 10.0)])

    def test_backward_clock_never_observes(self):
        c = Clock()
        ticks = iter((10, 9))
        with self.assertRaises(ValueError):
            observe_after_end(c.end, c.read, clock=lambda: next(ticks), sleep=c.sleep)
        self.assertEqual(c.events, [('END', 10.0)])

    def test_invalid_clock_values_never_observe(self):
        for value in (True, None, '10', -1, float('nan'), float('inf'), 10**1000):
            with self.subTest(value=str(value)[:20]):
                c = Clock()
                with self.assertRaises(ValueError):
                    observe_after_end(c.end, c.read, clock=lambda: value, sleep=c.sleep)
                self.assertEqual(c.events, [])

    def test_quiet_interval_starts_after_end_callback_returns(self):
        c = Clock()
        def slow_end():
            c.events.append(('END', c.now))
            c.now += 7
            return True
        _, proof = observe_after_end(slow_end, c.read, clock=c.clock, sleep=c.sleep)
        self.assertEqual(c.events[-1], ('READ', 47.0))
        self.assertEqual(proof['quiet_host_seconds'], 30)

    def test_stalled_clock_is_bounded_without_observation(self):
        c = Clock()
        with self.assertRaises(ValueError):
            observe_after_end(c.end, c.read, clock=c.clock, sleep=lambda _: None)
        self.assertEqual(c.events, [('END', 10.0)])

    def test_large_oversleep_fails_before_read(self):
        c = Clock()
        def oversleep(_):
            c.now += 121
        with self.assertRaises(ValueError):
            observe_after_end(c.end, c.read, clock=c.clock, sleep=oversleep)
        self.assertEqual(c.events, [('END', 10.0)])

    def test_short_wakes_do_not_shorten_required_quiet_time(self):
        c = Clock()
        def short_wake(_):
            c.now += 0.5
        _, proof = observe_after_end(c.end, c.read, clock=c.clock, sleep=short_wake)
        self.assertEqual(proof['quiet_host_seconds'], 30)
        self.assertEqual(proof['sleep_calls'], 60)

    def test_exact_and_fractional_deadline(self):
        c = Clock(); c.now = 10.125
        _, proof = observe_after_end(c.end, c.read, clock=c.clock, sleep=c.sleep)
        self.assertEqual(proof['quiet_host_seconds'], 30)
        self.assertEqual(c.events[-1], ('READ', 40.125))

    def test_unknown_anchor_does_not_become_complete_from_host_wait(self):
        self.assertEqual(window_status(anchor=None, observed_game_time=100)['phase'], 'ANCHOR_UNKNOWN')
        self.assertFalse(window_status(anchor=None, observed_game_time=100)['window_complete'])

    def test_window_and_readiness_margin_boundaries(self):
        for age, phase, inside, complete in (
            (0, 'WAIT_WINDOW', True, False), (9.999, 'WAIT_WINDOW', True, False),
            (10, 'WAIT_WINDOW', False, False), (10.249, 'WAIT_WINDOW', False, False),
            (10.25, 'COMPLETE', False, True), (30, 'COMPLETE', False, True)):
            with self.subTest(age=age):
                value = window_status(anchor=100, observed_game_time=100 + age)
                self.assertEqual(value['phase'], phase)
                self.assertEqual(value['observer_inside_window'], inside)
                self.assertEqual(value['window_complete'], complete)

    def test_clock_before_anchor_is_rejected(self):
        with self.assertRaises(ValueError):
            window_status(anchor=100, observed_game_time=99)

    def test_invalid_game_times_are_rejected_even_when_anchor_unknown(self):
        for value in (True, None, '100', -1, float('nan'), float('inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                window_status(anchor=None, observed_game_time=value)

    def test_invalid_anchor_is_rejected(self):
        for value in (True, '100', -1, float('nan'), float('inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                window_status(anchor=value, observed_game_time=100)


if __name__ == '__main__':
    unittest.main()
