"""Declare observed Civ VI Tuner realms before dispatching a query.

This is a caller contract, not a claim that a result was accepted or completed.
Unknown context names require a separate observation before being admitted.
"""
from types import MappingProxyType

CONTEXT_REALMS=MappingProxyType({
    'BaiqiGameplay':'CORE',
    'GameCore_Tuner':'CORE',
    'BaiqiExecutor':'UI',
    'WorldInput':'UI',
    'MainMenu':'UI',
    'ActionPanel':'UI',
    'UnitPanel':'UI',
    'CityPanel':'UI',
    'CityPanelOverview':'UI',
    'DiplomacyActionView':'UI',
    'DiplomacyDealView':'UI',
    'InGameTopOptionsMenu':'UI',
    'GreatWorksOverview':'UI',
    'ReportScreen':'UI',
})

def context_realm(context:str)->str:
    if type(context)is not str or context not in CONTEXT_REALMS:
        raise ValueError('Unqualified Tuner context')
    return CONTEXT_REALMS[context]

def checked_call(query,context:str,code:str,*,expected_realm:str):
    actual=context_realm(context)
    if expected_realm not in ('UI','CORE')or actual!=expected_realm:
        raise ValueError(f'Tuner realm mismatch: {context} is {actual}, expected {expected_realm}')
    if not callable(query)or type(code)is not str or not code:
        raise ValueError('A query callable and nonempty source are required')
    return query(context,code)
