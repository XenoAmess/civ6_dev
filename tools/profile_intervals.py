"""Union diagnostic intervals after the caller establishes one clock domain.

This helper cannot establish sample coverage or clock calibration. Input pairs
must be sequences; endpoints and the result must be representable finite floats.
"""

from collections.abc import Mapping, Sequence
import math


def union_seconds(intervals):
    try:
        iterator = iter(intervals)
    except TypeError as exc:
        raise ValueError("intervals must be iterable") from exc

    merged = []
    for item in iterator:
        if (not isinstance(item, Sequence)
                or isinstance(item, (str, bytes, bytearray, Mapping))
                or len(item) != 2):
            raise ValueError("interval must be a two-item sequence")
        start, end = item
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               for value in (start, end)):
            raise ValueError("interval values must be int or float, excluding bool")
        if end < start:
            raise ValueError("end must be >= start")
        try:
            start, end = float(start), float(end)
        except OverflowError as exc:
            raise ValueError("interval values exceed float range") from exc
        if not math.isfinite(start) or not math.isfinite(end):
            raise ValueError("interval values must be finite")
        merged.append((start, end))

    if not merged:
        return 0.0
    merged.sort(key=lambda x: x[0])
    total = 0.0
    current_start, current_end = merged[0]
    for i in range(1, len(merged)):
        s, e = merged[i]
        if s <= current_end:
            if e > current_end:
                current_end = e
        else:
            total += current_end - current_start
            current_start, current_end = s, e
    total += current_end - current_start
    if not math.isfinite(total):
        raise ValueError("covered duration exceeds float range")
    return float(total)
