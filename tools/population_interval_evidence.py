"""Compare complete owned-city population evidence; no causal or action permission."""
import math

def analyze_population_interval(before, after):
    def is_valid_dict(d):
        return isinstance(d, dict)

    def is_valid_scope(s):
        return isinstance(s, str) and len(s) > 0

    def is_valid_turn(t):
        if isinstance(t, bool):
            return False
        if not isinstance(t, int):
            return False
        return 0 <= t <= 100000

    def finite(value):
        try:
            return math.isfinite(value)
        except OverflowError:
            return False

    def is_valid_city(c):
        if not isinstance(c, dict):
            return False
        cid = c.get('cityID')
        owner = c.get('owner')
        x = c.get('x')
        y = c.get('y')
        pop = c.get('population')
        
        if not (isinstance(cid, int) and not isinstance(cid, bool) and cid >= 0 and finite(cid)):
            return False
        if not (isinstance(owner, int) and not isinstance(owner, bool) and owner == 0):
            return False
        if not (isinstance(x, int) and not isinstance(x, bool) and x >= 0 and finite(x)):
            return False
        if not (isinstance(y, int) and not isinstance(y, bool) and y >= 0 and finite(y)):
            return False
        if not (isinstance(pop, int) and not isinstance(pop, bool) and pop > 0 and finite(pop)):
            return False
        return True

    def validate_snapshot(snap):
        if not is_valid_dict(snap):
            return False
        if not is_valid_scope(snap.get('scope_key')):
            return False
        if not is_valid_turn(snap.get('turn')):
            return False
        if snap.get('complete') is not True:
            return False
        cities = snap.get('cities')
        if not isinstance(cities, list):
            return False
        if not (1 <= len(cities) <= 256):
            return False
        seen_ids = set()
        for c in cities:
            if not is_valid_city(c):
                return False
            cid = c['cityID']
            if cid in seen_ids:
                return False
            seen_ids.add(cid)
        return True

    if not validate_snapshot(before) or not validate_snapshot(after):
        return {
            'status': 'UNKNOWN',
            'qualified': False,
            'reason': 'invalid_snapshot',
            'losses': [],
            'new_city_ids': [],
            'causal_conclusion': None
        }

    if before['scope_key'] != after['scope_key']:
        return {
            'status': 'UNKNOWN',
            'qualified': False,
            'reason': 'scope_mismatch',
            'losses': [],
            'new_city_ids': [],
            'causal_conclusion': None
        }

    if after['turn'] != before['turn'] + 1:
        return {
            'status': 'UNKNOWN',
            'qualified': False,
            'reason': 'turn_mismatch',
            'losses': [],
            'new_city_ids': [],
            'causal_conclusion': None
        }

    before_cities = {c['cityID']: c for c in before['cities']}
    after_cities = {c['cityID']: c for c in after['cities']}

    for cid, bc in before_cities.items():
        if cid not in after_cities:
            return {
                'status': 'UNKNOWN',
                'qualified': False,
                'reason': 'missing_city',
                'losses': [],
                'new_city_ids': [],
                'causal_conclusion': None
            }
        ac = after_cities[cid]
        if bc['x'] != ac['x'] or bc['y'] != ac['y'] or bc['owner'] != ac['owner']:
            return {
                'status': 'UNKNOWN',
                'qualified': False,
                'reason': 'identity_mismatch',
                'losses': [],
                'new_city_ids': [],
                'causal_conclusion': None
            }

    losses = []
    for cid, bc in before_cities.items():
        ac = after_cities[cid]
        bp = bc['population']
        ap = ac['population']
        if ap < bp:
            losses.append({
                'cityID': cid,
                'x': bc['x'],
                'y': bc['y'],
                'before_population': bp,
                'after_population': ap,
                'delta': ap - bp
            })

    losses.sort(key=lambda l: l['cityID'])

    new_city_ids = sorted([cid for cid in after_cities if cid not in before_cities])

    if not losses:
        return {
            'status': 'NO_LOSS',
            'qualified': True,
            'reason': 'no_population_loss',
            'losses': [],
            'new_city_ids': new_city_ids,
            'causal_conclusion': None
        }
    else:
        return {
            'status': 'POPULATION_LOSS',
            'qualified': True,
            'reason': 'population_loss_detected',
            'losses': losses,
            'new_city_ids': new_city_ids,
            'causal_conclusion': None
        }
