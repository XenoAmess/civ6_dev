"""External TEST_PLAYER preparation before the private ordinary END endpoint."""
import re
from tools.paired_normal_end import request_end


def make_callback(query,child,record,is_diplomacy_visible,*,expected_source_version=142):
    if type(expected_source_version)is not int or expected_source_version!=142:
        raise ValueError('Invalid source version')
    if not all(callable(f)for f in (query,child,record,is_diplomacy_visible)):
        raise TypeError('Callback dependencies must be callable')

    def visible_guard():
        if is_diplomacy_visible() is not False:
            raise RuntimeError('Diplomacy visible or unknown; no dependent input')

    def callback(turn,token):
        if type(turn)is not int or not 85<=turn<=89:
            raise ValueError('Invalid turn')
        if type(token)is not str or re.fullmatch('[0-9a-f]{32}',token)is None:
            raise ValueError('Invalid token')
        visible_guard()
        record(f'callback-{turn}-attempt',{'turn':turn,'token':token,'role':'TEST_PLAYER'})
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
                                         'meaning':'About to call ordinary endpoint once'})
        ack=request_end(query,turn,token,expected_source_version=expected_source_version)
        record(f'issuance-{turn}-returned',{'ack':ack,
                  'meaning':'Call returned; engine acceptance and activation require independent readback'})
        return ack
    return callback
