"""Prepare reversible, source-bound Core write observations in memory only.

This never installs a package, changes SDK tables, or sends game operations.
The caller must pin/verify the whole input payload and qualify the private build.
"""
from __future__ import annotations

import hashlib
import re

ENTRY = "Lua/BaiqiGameplay.lua"
NAMESPACE = "P6CoreSites174"
METHOD = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*):(SetProperty|AttachModifierByID|ChangeGoldBalance)\(")
DIRECT = re.compile(r"\b(Game\.SetProperty|UnitManager\.FinishMoves)\(")
TRANSFER = re.compile(r"\bpcall\(\s*(CityManager\.TransferCity)\s*,")
INCLUDE = re.compile(r'^\s*include\("([A-Za-z0-9_]+)"\)', re.MULTILINE)
PCALL_INCLUDE = re.compile(r'\bpcall\(\s*include\s*,\s*"([A-Za-z0-9_]+)"')
KINDS = {"player": "PLAYER", "p": "PLAYER", "unit": "UNIT", "plot": "PLOT", "treasury": "TREASURY"}

PROVIDER = r'''
 local function Describe(kind,target)
  if kind=='PLAYER'or kind=='TREASURY'then
   local found,count=nil,0;local ids=PlayerManager.GetAliveIDs();assert(type(ids)=='table')
   local seen={};local n=0
   for _,pid in ipairs(ids)do
    n=n+1;assert(n<=256 and type(pid)=='number'and pid>=0 and pid%1==0 and not seen[pid]);seen[pid]=true
    local p=Players[pid];local object=p
    if kind=='TREASURY'then object=p and type(p.GetTreasury)=='function'and p:GetTreasury()or nil end
    if object==target then found=pid;count=count+1 end
   end
   assert(count==1,'Unknown or ambiguous native player identity');return{owner=found,id=found}
  end
  assert(target~=nil and type(target.GetOwner)=='function')
  local owner=target:GetOwner()
  if kind=='PLOT'then return{owner=owner,x=target:GetX(),y=target:GetY()}end
  assert(kind=='UNIT'or kind=='CITY');return{owner=owner,id=target:GetID()}
 end
 P6CoreSites174=Factory.New({context='BaiqiGameplay/cold174-native-sites',capacity=4096,
  frame=function()return Game.GetCurrentGameTurn(),Game.GetLocalPlayer()end,
  describe=Describe,unpack=table.unpack or unpack})
 print('CORETRACE174_SOURCE_SITES_INSTALLED',28)
'''


def core_closure(payload: dict[str, bytes]) -> list[str]:
    pending = [ENTRY]
    seen: set[str] = set()
    result = []
    while pending:
        name = pending.pop(0)
        if name in seen:
            continue
        seen.add(name)
        if len(seen) > 97 or name not in payload:
            raise ValueError("Missing or unbounded literal Core include")
        result.append(name)
        text = payload[name].decode("utf-8-sig")
        pending.extend("Lua/" + child + ".lua" for child in INCLUDE.findall(text) + PCALL_INCLUDE.findall(text))
    return result


def prepare(payload: dict[str, bytes], module: bytes) -> tuple[dict[str, bytes], dict]:
    closure = core_closure(payload)
    if len(closure) != 40:
        raise ValueError("Unreviewed Core closure; inspect current producers first")
    prefix = (b"-- PRIVATE QA: passive Core native sites before all original includes.\ndo\n"
              b" assert(P6CoreSites174==nil,'Occupied Core diagnostic namespace')\n local Factory=(function()\n"
              + module + b"\nend)()\n" + PROVIDER.encode("utf-8") + b"end\n")
    transformed = dict(payload)
    sites = []
    counts: dict[str, int] = {}
    for path in closure:
        original = payload[path].decode("utf-8")
        if NAMESPACE in original:
            raise ValueError("Core diagnostic already present")
        edits = []
        for m in METHOD.finditer(original):
            receiver, method = m.groups()
            if receiver not in KINDS or (method == "AttachModifierByID" and receiver != "player") or (method == "ChangeGoldBalance" and receiver != "treasury"):
                raise ValueError("Unreviewed native method receiver")
            edits.append((m.start(), m.end(), KINDS[receiver], method, receiver))
        for m in DIRECT.finditer(original):
            function = m.group(1)
            edits.append((m.start(), m.end(), "GLOBAL" if function.startswith("Game.") else "UNIT", function, None))
        for m in TRANSFER.finditer(original):
            edits.append((m.start(1), m.end(1), "CITY", m.group(1), None))
        edits.sort()
        for index, (start, end, kind, method, receiver) in enumerate(edits, 1):
            if index > 1 and start < edits[index - 2][1]:
                raise ValueError("Overlapping native sites")
            line = original.count("\n", 0, start) + 1
            site = f"{path}:{line}:{index}"
            if receiver:
                after = f"{NAMESPACE}.Method('{site}','{kind}',{receiver},'{method}') ("
            else:
                after = f"{NAMESPACE}.Static('{site}','{kind}',{method})"
                if method != "CityManager.TransferCity":
                    after += "("
            sites.append({"path": path, "site": site, "kind": kind, "method": method,
                          "before": original[start:end], "after": after,
                          "input_sha256": hashlib.sha256(payload[path]).hexdigest()})
            counts[method] = counts.get(method, 0) + 1
        text = original
        for edit, row in reversed(list(zip(edits, sites[-len(edits):] if edits else []))):
            start, end = edit[:2]
            text = text[:start] + row["after"] + text[end:]
        transformed[path] = text.encode("utf-8")
    expected = {"SetProperty": 22, "AttachModifierByID": 1, "ChangeGoldBalance": 1,
                "Game.SetProperty": 2, "CityManager.TransferCity": 1, "UnitManager.FinishMoves": 1}
    if counts != expected or len(sites) != 28:
        raise ValueError("Unreviewed native write site set")
    transformed[ENTRY] = prefix + transformed[ENTRY]
    # Independently invert every unique insertion to the exact original bytes.
    for path in closure:
        text = transformed[path].decode("utf-8")
        if path == ENTRY:
            if not text.startswith(prefix.decode("utf-8")):
                raise AssertionError("Core prefix missing")
            text = text[len(prefix.decode("utf-8")):]
        for row in reversed([v for v in sites if v["path"] == path]):
            if text.count(row["after"]) != 1:
                raise AssertionError("Ambiguous native site inverse")
            text = text.replace(row["after"], row["before"], 1)
        if text.encode("utf-8") != payload[path]:
            raise AssertionError("Core diagnostic inverse differs")
    return transformed, {"closure": closure, "sites": sites, "counts": counts,
                         "module_sha256": hashlib.sha256(module).hexdigest(),
                         "prefix_sha256": hashlib.sha256(prefix).hexdigest(),
                         "all_original_bytes_inverse_verified": True,
                         "SDK_table_writes": 0, "Native_or_game_operations": 0}
