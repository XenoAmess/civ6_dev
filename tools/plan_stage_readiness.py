"""Read-only readiness gate before the private Stage A final Native assertion."""
import math


def _validate_common(anchor,active,busy,processing,pending,recorded,validated,errors):
    if any(type(value)is not bool for value in (active,busy,processing)):
        raise ValueError('Unknown closing flags')
    if any(type(value)is not int or not 0<=value<=2147483647
           for value in (pending,recorded,validated,errors)):
        raise ValueError('Unknown proof counters')
    if errors or pending+validated!=recorded:
        raise ValueError('Invalid or failed pre-anchor proof')
    if anchor is not None:
        if type(anchor)not in (int,float):
            raise ValueError('Unknown closing anchor')
        try:
            numeric=float(anchor)
        except OverflowError as exc:
            raise ValueError('Overflowing closing anchor')from exc
        if not math.isfinite(numeric)or numeric<=0:
            raise ValueError('Invalid closing anchor')

def closing_ready(turn,anchor,active,busy,processing,pending,recorded,validated,errors):
    if type(turn)is not int or not 85<=turn<=91:
        raise ValueError('Unknown closing turn')
    _validate_common(anchor,active,busy,processing,pending,recorded,validated,errors)
    return (turn==91 and anchor is not None and active and not busy
            and not processing and pending==0 and recorded==validated)

def pressure_closing_ready(initial_turn,turn,anchor,active,busy,processing,pending,recorded,validated,errors):
    if type(initial_turn)is not int or not 0<=initial_turn<=2147483641:
        raise ValueError('Invalid initial_turn')
    if type(turn)is not int or not initial_turn<=turn<=initial_turn+6:
        raise ValueError('Unknown closing turn')
    _validate_common(anchor,active,busy,processing,pending,recorded,validated,errors)
    return (turn==initial_turn+6 and anchor is not None and active and not busy
            and not processing and pending==0 and recorded==validated)
