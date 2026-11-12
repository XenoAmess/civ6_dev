"""Independent food evidence domains; no game actions or causal conclusions."""
from __future__ import annotations

import math


def _number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _integer(value, minimum=None):
    return type(value) is int and _number(value) and (minimum is None or value >= minimum)


def _endpoint(row):
    return (type(row) is dict and type(row.get('scope_key')) is str and bool(row['scope_key'])
            and _integer(row.get('cityID'), 0) and _integer(row.get('turn'), 0)
            and _number(row.get('surplus')))


def _ui_sample(row):
    return (_endpoint(row) and _integer(row.get('population'), 1)
            and _number(row.get('stock')) and row['stock'] >= 0
            and _integer(row.get('project_hash'))
            and _number(row.get('project_progress')) and row['project_progress'] >= 0)


def analyze_food_interval(ui_before, ui_after, core_before, core_after, production_events):
    """Validate supplied provenance; matching turn alone does not prove simultaneity."""
    ui = {'qualified': False, 'reason': 'INVALID_UI_INTERVAL', 'stock_delta': None}
    core = {'qualified': False, 'reason': 'UNALIGNED_CORE_ENDPOINTS',
            'before_conflict': None, 'after_conflict': None}
    production = {'qualified': False, 'reason': 'MISSING_EVENT_COVERAGE', 'events': []}
    result = {'ui_interval': ui, 'core_comparison': core, 'production': production,
              'causal_conclusion': None}
    if (_ui_sample(ui_before) and _ui_sample(ui_after)
            and ui_before['scope_key'] == ui_after['scope_key']
            and ui_before['cityID'] == ui_after['cityID']
            and ui_after['turn'] == ui_before['turn'] + 1
            and ui_before['population'] == ui_after['population']):
        ui.update(qualified=True, reason='ALIGNED_UI_STOCK_DELTA',
                  stock_delta=ui_after['stock'] - ui_before['stock'])

    pairs = ((ui_before, core_before), (ui_after, core_after))
    if all(_endpoint(u) and _endpoint(c)
           and all(u[k] == c[k] for k in ('scope_key', 'cityID', 'turn')) for u, c in pairs):
        core.update(qualified=True, reason='ALIGNED_ENDPOINT_VALUES_NOT_ATOMIC_SAMPLES',
                    before_conflict=ui_before['surplus'] != core_before['surplus'],
                    after_conflict=ui_after['surplus'] != core_after['surplus'])

    if production_events is None:
        return result
    if type(production_events) is not list:
        production['reason'] = 'INVALID_EVENT_CONTAINER'
        return result
    if len(production_events) > 128:
        production['reason'] = 'EVENT_LIMIT_EXCEEDED_NO_PREFIX_QUALIFICATION'
        return result
    if not ui['qualified']:
        production['reason'] = 'UNQUALIFIED_UI_EVENT_RANGE'
        return result
    malformed = False
    for event in production_events:
        if (type(event) is not dict or type(event.get('scope_key')) is not str
                or not event['scope_key'] or not _integer(event.get('cityID'), 0)
                or not _integer(event.get('turn'), 0)
                or event.get('event') not in ('CityProductionCompleted', 'CityProductionChanged', 'CityProductionUpdated')
                or any(event.get(k) is not None and not _integer(event[k])
                       for k in ('productionKind', 'productionIndex'))):
            malformed = True
            continue
        if (event['scope_key'] == ui_before['scope_key']
                and event['cityID'] == ui_before['cityID']
                and ui_before['turn'] <= event['turn'] <= ui_after['turn']
                and event['event'] == 'CityProductionCompleted'):
            production['events'].append({k: event.get(k) for k in (
                'scope_key', 'cityID', 'turn', 'event', 'productionKind', 'productionIndex')})
    production.update(qualified=not malformed,
                      reason='MALFORMED_EVENT_COVERAGE' if malformed else 'BOUNDED_RECORDED_LIST_ONLY')
    return result
