"""Bound Core-minus-UI clock offset from synchronous bracket samples.

This assumes one constant offset for the supplied observations; it cannot prove
clock synchronization, native bridge identity, or all-module timing coverage.
"""

from collections.abc import Sequence, Mapping
import math

def intersect_offsets(samples):
    if isinstance(samples, (str, bytes, bytearray, Mapping)):
        raise ValueError("samples must be a non-text, non-mapping iterable")
    try:
        iterator = iter(samples)
    except TypeError as exc:
        raise ValueError("samples must be iterable") from exc

    lower = -math.inf
    upper = math.inf
    count = 0

    for item in iterator:
        if (not isinstance(item, Sequence)
                or isinstance(item, (str, bytes, bytearray, Mapping))
                or len(item) != 3):
            raise ValueError("sample must be a three-item sequence")
        a, c, z = item
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               for v in (a, c, z)):
            raise ValueError("values must be int or float, excluding bool")
        if a < 0 or c < 0 or z < 0:
            raise ValueError("values must be nonnegative")
        if a > z:
            raise ValueError("ui_after must be >= ui_before")
        try:
            af, cf, zf = float(a), float(c), float(z)
        except OverflowError as exc:
            raise ValueError("values exceed float range") from exc
        if not math.isfinite(af) or not math.isfinite(cf) or not math.isfinite(zf):
            raise ValueError("values must be finite")
        lo = cf - zf
        hi = cf - af
        if lo > lower:
            lower = lo
        if hi < upper:
            upper = hi
        count += 1

    if count == 0:
        raise ValueError("samples must be nonempty")

    if not math.isfinite(lower) or not math.isfinite(upper):
        raise ValueError("offset bounds exceed float range")

    return {
        "samples": count,
        "lower_seconds": float(lower),
        "upper_seconds": float(upper),
        "consistent": lower <= upper,
    }
