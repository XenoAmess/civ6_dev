"""Bound retries to the paired player's fixed, read-only visibility query."""
from tools.run_observed_acceptance import _payload

CONTEXT = 'DiplomacyActionView'
CODE = "print('PAIR142_DIPLO',not ContextPtr:IsHidden())"


def read_visibility(query, sleep, emit, *, attempts=3):
    if not callable(query) or not callable(sleep) or not callable(emit):
        raise TypeError('Dependencies must be callable')
    if type(attempts) is not int or not 1 <= attempts <= 3:
        raise ValueError('attempts must be int 1..3')

    last_exc = None
    for i in range(1, attempts + 1):
        try:
            messages = query(CONTEXT, CODE)
            fields = _payload(messages, 'PAIR142_DIPLO')
            if fields == ['true']:
                return True
            if fields == ['false']:
                return False
            raise RuntimeError(f'Malformed visibility receipt: {fields}')
        except (OSError, EOFError) as error:
            last_exc = error
            if i < attempts:
                emit(f'Visibility read attempt {i} failed with {type(error).__name__}; retrying')
                sleep(0.25)
            else:
                emit(f'Visibility read attempt {i} failed with {type(error).__name__}; exhausted')
        except Exception:
            raise

    raise last_exc
