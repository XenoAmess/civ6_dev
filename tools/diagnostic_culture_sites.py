"""Prepare private observations at the three reviewed Admin culture call sites.

The caller pins the complete current payload. Nothing is installed or executed.
"""
from __future__ import annotations

import hashlib
import re

ENTRY = "Lua/BaiqiAdmin.lua"
NAMESPACE = "P6CultureSites174"
CALL = re.compile(r"\bculture:(RequestChangeGovernment|SetGovernmentChangeConsidered|RequestPolicyChanges)\(")
PROVIDER = r'''
 local function Describe(kind,target)
  assert(kind=='PLAYER');local found,count=nil,0
  local ids=PlayerManager.GetAliveIDs();assert(type(ids)=='table')
  local seen={};local n=0
  for _,pid in ipairs(ids)do
   n=n+1;assert(n<=256 and type(pid)=='number'and pid>=0 and pid%1==0 and not seen[pid]);seen[pid]=true
   local p=Players[pid]
   local object=p and type(p.GetCulture)=='function'and p:GetCulture()or nil
   if object==target then found=pid;count=count+1 end
  end
  assert(count==1,'Unknown or ambiguous native culture identity')
  return{owner=found,id=found}
 end
 P6CultureSites174=Factory.New({context='BaiqiExecutor/cold174-culture-sites',capacity=256,
  frame=function()return Game.GetCurrentGameTurn(),Game.GetLocalPlayer()end,
  describe=Describe,unpack=table.unpack or unpack})
 print('CULTURETRACE174_SOURCE_SITES_INSTALLED',3)
'''


def prepare(payload: dict[str, bytes], module: bytes) -> tuple[dict[str, bytes], dict]:
    original = payload[ENTRY].decode('utf-8')
    if NAMESPACE in original or original.startswith('\ufeff'):
        raise ValueError('Occupied culture diagnostic input or unreviewed encoding')
    matches = list(CALL.finditer(original))
    methods = [m.group(1) for m in matches]
    if methods != ['RequestChangeGovernment', 'SetGovernmentChangeConsidered', 'RequestPolicyChanges']:
        raise ValueError('Unreviewed direct culture native sites')
    sites = []
    for i, m in enumerate(matches, 1):
        line = original.count('\n', 0, m.start()) + 1
        site = f'{ENTRY}:{line}:{i}'
        sites.append({'site': site, 'method': m.group(1), 'line': line,
                      'before': m.group(),
                      'after': f"{NAMESPACE}.Method('{site}','PLAYER',culture,'{m.group(1)}')("})
    text = original
    for m, row in reversed(list(zip(matches, sites))):
        text = text[:m.start()] + row['after'] + text[m.end():]
    prefix = (b'-- PRIVATE QA: direct culture native source sites, no SDK/proxy writes.\ndo\n'
              b" assert(P6CultureSites174==nil,'Occupied culture diagnostic namespace')\n local Factory=(function()\n"
              + module + b'\nend)()\n' + PROVIDER.encode('utf-8') + b'end\n')
    result = dict(payload); result[ENTRY] = prefix + text.encode('utf-8')
    inverse = result[ENTRY][len(prefix):].decode('utf-8')
    for row in reversed(sites):
        if inverse.count(row['after']) != 1:
            raise AssertionError('Ambiguous culture source site inverse')
        inverse = inverse.replace(row['after'], row['before'], 1)
    if inverse.encode('utf-8') != payload[ENTRY]:
        raise AssertionError('Culture source inverse differs')
    return result, {'sites': sites, 'all_original_bytes_inverse_verified': True,
                    'input_sha256': hashlib.sha256(payload[ENTRY]).hexdigest(),
                    'module_sha256': hashlib.sha256(module).hexdigest(),
                    'prefix_sha256': hashlib.sha256(prefix).hexdigest(),
                    'SDK_or_global_manager_replacements': 0, 'game_inputs': 0}
