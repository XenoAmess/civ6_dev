from tools.run_observed_acceptance import _payload

def request_end(query, turn, token,*,expected_source_version=140):
    if type(expected_source_version)is not int or expected_source_version not in (140,141,142):raise ValueError('Invalid source version')
    if type(turn) is not int or not (85 <= turn <= 89):
        raise ValueError('Invalid turn')
    if type(token) is not str or len(token) != 32 or any(c not in '0123456789abcdef' for c in token):
        raise ValueError('Invalid token')
    code = f'''
assert(Game.GetCurrentGameTurn()=={turn} and Game.GetLocalPlayer()==0 and Players[0]:IsTurnActive() and Game.IsAllowStrategicCommands(0) and UI.CanEndTurn() and not UI.IsGameCoreBusy() and not UI.IsProcessingMessages())
local bridge=ExposedMembers.P6BaiqiPairEndBridge
assert(bridge and bridge.marker=='baiqi-paired-end-bridge-v1' and bridge.source_version=={expected_source_version} and type(bridge.Begin)=='function')
assert(bridge.Begin({turn},"{token}"))
UI.RequestAction(ActionTypes.ACTION_ENDTURN)
print('P6_PAIR_ORDINARY_ISSUED',{turn},"{token}")
'''
    ack = _payload(query('ActionPanel', code), 'P6_PAIR_ORDINARY_ISSUED')
    if ack != [str(turn), token]:
        raise RuntimeError('Unknown issuance receipt')
    return {'turn': turn, 'token': token, 'requested': True, 'forced': False}


def request_pressure_end(query, turn, token, *, initial_turn):
    """Issue one ordinary request; the receipt does not prove turn activation."""
    if type(initial_turn) is not int or not (0 <= initial_turn <= 2147483641):
        raise ValueError('Invalid initial_turn')
    if type(turn) is not int or not (initial_turn <= turn <= initial_turn + 4):
        raise ValueError('Invalid turn')
    if type(token) is not str or len(token) != 32 or any(c not in '0123456789abcdef' for c in token):
        raise ValueError('Invalid token')
    code = f'''
assert(Game.GetCurrentGameTurn()=={turn} and Game.GetLocalPlayer()==0 and Players[0]:IsTurnActive() and Game.IsAllowStrategicCommands(0) and UI.CanEndTurn() and not UI.IsGameCoreBusy() and not UI.IsProcessingMessages())
local bridge=ExposedMembers.P6BaiqiPairEndBridge
assert(bridge and bridge.marker=='baiqi-paired-end-bridge-pressure-v1' and bridge.source_version==142 and bridge.source=='baiqi142-pressure-paired-v1' and bridge.initial_turn=={initial_turn} and type(bridge.Begin)=='function')
assert(bridge.Begin({turn},"{token}"))
UI.RequestAction(ActionTypes.ACTION_ENDTURN)
print('P6_PRESSURE_PAIR_ORDINARY_ISSUED',{turn},"{token}",{initial_turn})
'''
    ack = _payload(query('ActionPanel', code), 'P6_PRESSURE_PAIR_ORDINARY_ISSUED')
    if ack != [str(turn), token, str(initial_turn)]:
        raise RuntimeError('Unknown issuance receipt')
    return {'turn': turn, 'token': token, 'initial_turn': initial_turn, 'source': 'baiqi142-pressure-paired-v1', 'source_version': 142, 'requested': True, 'forced': False}
