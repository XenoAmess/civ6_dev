from tools.run_observed_acceptance import _payload

def request_end(query, turn, token,*,expected_source_version=140):
    if type(expected_source_version)is not int or expected_source_version not in (140,141):raise ValueError('Invalid source version')
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
