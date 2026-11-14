"""External TEST_PLAYER preparation before the private ordinary END endpoint."""
import re
from tools.paired_normal_end import request_end,request_pressure_end


def make_callback(query,child,record,is_diplomacy_visible,*,expected_source_version=142,pressure_initial_turn=None):
    if type(expected_source_version)is not int or expected_source_version!=142:
        raise ValueError('Invalid source version')
    if not all(callable(f)for f in (query,child,record,is_diplomacy_visible)):
        raise TypeError('Callback dependencies must be callable')
    pressure=pressure_initial_turn is not None
    if pressure and(type(pressure_initial_turn)is not int or not 0<=pressure_initial_turn<=2147483641):
        raise ValueError('Invalid pressure initial_turn')
    first=pressure_initial_turn if pressure else 85
    metadata={'source':'baiqi142-pressure-paired-v1','initial_turn':first}if pressure else{}

    def visible_guard():
        if is_diplomacy_visible() is not False:
            raise RuntimeError('Diplomacy visible or unknown; no dependent input')

    def callback(turn,token):
        if type(turn)is not int or not first<=turn<=first+4:
            raise ValueError('Invalid turn')
        if type(token)is not str or re.fullmatch('[0-9a-f]{32}',token)is None:
            raise ValueError('Invalid token')
        visible_guard()
        record(f'callback-{turn}-attempt',{'turn':turn,'token':token,'role':'TEST_PLAYER',**metadata})
        for seq in range(1,61):
            visible_guard()
            selected=child('select',turn,seq)
            if type(selected)is not str:
                raise RuntimeError('Unknown selection receipt')
            exhausted='P6_PAIR142_NO_NEW_LEGAL_MILITARY_SKIP'in selected
            eligible='P6_PAIR142_VIEW_NEXT_SKIP_ELIGIBLE'in selected
            if exhausted==eligible:
                raise RuntimeError('Unknown or conflicting selection receipt')
            if exhausted:
                break
            visible_guard()
            stepped=child('step',turn,seq)
            if type(stepped)is not str or 'P6_PAIR142_NORMAL_TESTPLAYER_SKIP'not in stepped:
                raise RuntimeError('Unknown military SKIP receipt')
        else:
            raise RuntimeError('Military preparation bound; no END')
        visible_guard()
        record(f'issuance-{turn}-attempt',{'turn':turn,'token':token,'forced':False,
                                         'meaning':'About to call ordinary endpoint once',**metadata})
        ack=(request_pressure_end(query,turn,token,initial_turn=first)if pressure
             else request_end(query,turn,token,expected_source_version=expected_source_version))
        record(f'issuance-{turn}-returned',{'ack':ack,
                  'meaning':'Call returned; engine acceptance and activation require independent readback'})
        return ack
    return callback
