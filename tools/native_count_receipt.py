"""Strictly parse one counted Native receipt; never replay an action."""
import re


def require_count_receipt(messages, marker, expected_count):
    if type(marker) is not str or re.fullmatch(r'[A-Z0-9_]{1,100}', marker) is None:
        raise ValueError('Exact receipt marker required')
    if type(expected_count) is not int or not 1 <= expected_count <= 80:
        raise ValueError('Exact bounded integer count required')
    if type(messages) not in (list, tuple):
        raise TypeError('Complete message sequence required')
    found = []
    for message in messages:
        if type(message) is not dict or type(message.get('tag')) is not int or type(message.get('payload')) is not str:
            raise ValueError('Unknown Native message envelope')
        if message['tag'] == 3 and message['payload'].startswith('ERR:'):
            raise RuntimeError(message['payload'])
        if message['tag'] == -1:
            fields = message['payload'].split(': ', 1)[-1].split('\t')
            if fields[0] == marker:
                found.append(fields[1:])
    if found != [[str(expected_count)]]:
        raise ValueError(f'Expected one exact {marker} count {expected_count}; got {found!r}')
    return expected_count
