from collections.abc import Sequence, Mapping

MAX_RETAINED_SAMPLES = 4096

OVERRIDES = {
    'UI/BaiqiExecutor.lua': 2048,
    'UI/BaiqiUnitFlagManager.lua': 768,
    'UI/BaiqiGovernmentScreen.lua': 384,
    'UI/BaiqiTechTree.lua': 192,
    'Lua/BaiqiGameplay.lua': 128,
    'UI/BaiqiUnitPanel.lua': 64,
    'UI/BaiqiCityPanel.lua': 64,
    'UI/BaiqiResearchChooser.lua': 64,
}


def bounded_quotas(expected_keys: Sequence[str]) -> dict[str, int]:
    if not isinstance(expected_keys, Sequence) or isinstance(expected_keys, (str, bytes, bytearray, Mapping)):
        raise TypeError('expected_keys must be a sequence of strings')
    keys = list(expected_keys)
    crisis_key = 'UI/BaiqiWorldCrisisPopup.lua'
    if len(keys) not in (32, 33):
        raise ValueError('expected legacy32 or source11133 keys')
    if any(not isinstance(k, str) or not k for k in keys):
        raise ValueError('keys must be non-empty strings')
    if len(set(keys)) != len(keys):
        raise ValueError('keys must be unique')
    if (len(keys) == 33) != (crisis_key in keys):
        raise ValueError('source111 context layout must include its crisis key')
    for k in OVERRIDES:
        if k not in keys:
            raise ValueError(f'missing override key: {k}')
    quotas = {}
    for k in keys:
        if k in OVERRIDES:
            # Fund the new context from executor capacity; the global4096 cap
            # and every legacy32 quota remain unchanged.
            quotas[k] = OVERRIDES[k] - (16 if len(keys) == 33 and k == 'UI/BaiqiExecutor.lua' else 0)
        else:
            quotas[k] = 16
    if any(type(v) is not int or v <= 0 for v in quotas.values()):
        raise ValueError('quotas must be positive integers')
    total = sum(quotas.values())
    if total != MAX_RETAINED_SAMPLES:
        raise ValueError(f'quota sum {total} != {MAX_RETAINED_SAMPLES}')
    return quotas
