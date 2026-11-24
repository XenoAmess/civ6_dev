"""Reduce observer work during the frozen ten-second planning windows.

This changes the test harness, not the mod, clocks, budgets or retained samples.
A completed host wait does not prove a game window has started or completed.
"""
from __future__ import annotations

import math
import time

QUIET_SECONDS = 30.0
MAX_WAIT_SECONDS = 120.0
MAX_SLEEPS = 120
WINDOW_SECONDS = 10.0
READINESS_MARGIN_SECONDS = 0.25


def _number(value, name):
    if type(value) not in (int, float):
        raise ValueError(f'Unknown {name}')
    try:
        valid = math.isfinite(value) and value >= 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f'Invalid {name}')
    return float(value)


def observe_after_end(request_end, read_state, *, clock=time.monotonic, sleep=time.sleep):
    """Request one qualified END, wait without queries, then observe once.

    The caller owns all Native qualification and must return exactly True only
    after its normal END acknowledgement has been validated. Exceptions and
    unknown acknowledgements stop here; neither END nor observation is retried.
    """
    if not all(callable(x) for x in (request_end, read_state, clock, sleep)):
        raise TypeError('Explicit callable dependencies required')
    before_end = _number(clock(), 'monotonic clock')
    if request_end() is not True:
        raise ValueError('Unknown normal END acknowledgement; no observation')
    start = previous = _number(clock(), 'monotonic clock')
    if start < before_end:
        raise ValueError('Monotonic clock moved backwards during END')
    sleeps = 0
    while True:
        now = _number(clock(), 'monotonic clock')
        if now < previous:
            raise ValueError('Monotonic clock moved backwards')
        elapsed = now - start
        if elapsed > MAX_WAIT_SECONDS:
            raise ValueError('Quiet observation deadline exceeded')
        if elapsed >= QUIET_SECONDS:
            break
        if sleeps >= MAX_SLEEPS:
            raise ValueError('Quiet observation clock did not progress')
        sleep(min(1.0, QUIET_SECONDS - elapsed))
        sleeps += 1
        previous = now
    # The sole observation callback follows the entire quiet interval.
    state = read_state()
    return state, {'quiet_host_seconds': elapsed, 'sleep_calls': sleeps,
                   'END_calls': 1, 'observation_calls': 1,
                   'game_window_complete_proved_by_host_wait': False}


def window_status(*, anchor, observed_game_time):
    """Classify the actual game clock, independently of the host wait.

    The actual caller must additionally validate turn, player, profile quality,
    readiness and pre-anchor receipts. A later wire audit must consider every
    transaction, not just this callback's print timestamp.
    """
    now = _number(observed_game_time, 'observed game time')
    if anchor is None:
        return {'phase': 'ANCHOR_UNKNOWN', 'window_complete': False,
                'observer_inside_window': None, 'age': None}
    at = _number(anchor, 'actual game anchor')
    if now < at:
        raise ValueError('Game clock predates actual anchor')
    age = now - at
    complete = age >= WINDOW_SECONDS + READINESS_MARGIN_SECONDS
    return {'phase': 'COMPLETE' if complete else 'WAIT_WINDOW',
            'window_complete': complete,
            'observer_inside_window': age < WINDOW_SECONDS,
            'age': age}
