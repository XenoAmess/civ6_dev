"""Prepare a reversible private observer of existing source142/155 settlement calls."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
if __package__ in (None,''):
    sys.path.insert(0,str(ROOT))
from tools.build_mod import contained,digest,manifest_files,package

CONTROLLER='Lua/BaiqiController.lua'
EDITS=(
 ('local function SettlementSites(player, state, firstOnly, excluded, unitID, preferredIndex, oneValidation)',
  'local function SettlementSitesBody(player, state, firstOnly, excluded, unitID, preferredIndex, oneValidation, qa)'),
 ('  if ai == nil then return result end\n  local seen={}',
  '  if ai == nil then return result end\n  if qa then qa.ai_available=true end\n  local seen={}'),
 ('        seen[index]=candidate;candidates[#candidates+1]=candidate',
  '        seen[index]=candidate;candidates[#candidates+1]=candidate\n        if qa then qa.admitted=qa.admitted+1 end'),
 ('  for rank, recommendation in pairs(ai:GetSettlementRecommendations(12) or {}) do',
  '  local hints=ai:GetSettlementRecommendations(12)\n  if qa then qa.hints_kind=type(hints) end\n  for rank, recommendation in pairs(hints or {}) do\n    if qa then qa.raw_hints=qa.raw_hints+1 end'),
 ('  for i,candidate in ipairs(candidates) do\n    if oneValidation',
  '  for i,candidate in ipairs(candidates) do\n    if qa then qa.visited=qa.visited+1 end\n    if oneValidation'),
 ('      if KnownExpansionSupport(plot,player,contextID)==true then\n        result[#result+1]',
  '      local support=KnownExpansionSupport(plot,player,contextID)\n      if qa then\n        qa.cheap_pass=qa.cheap_pass+1\n        local key=support==true and "support_true" or(support==false and "support_false" or "support_unknown")\n        qa[key]=qa[key]+1\n      end\n      if support==true then\n        result[#result+1]'),
 ('local function RecruitAllowed(role,economy,player,state)',
  'local function SettlementSites(player,state,firstOnly,excluded,unitID,preferredIndex,oneValidation,censusCaller)\n  return P6SettlementCensus.Run(SettlementSitesBody,censusCaller,player,state,firstOnly,excluded,unitID,preferredIndex,oneValidation)\nend\n\nlocal function RecruitAllowed(role,economy,player,state,censusCaller)'),
 ('#SettlementSites(player,state,true)>0', '#SettlementSites(player,state,true,nil,nil,nil,nil,censusCaller)>0'),
 ('SettlementSites(player,state,true,search.tested,id,settlementTargets[id],true)',
  'SettlementSites(player,state,true,search.tested,id,settlementTargets[id],true,"settler_alternatives")'),
 ('RecruitAllowed(role,economy,player,state) then', 'RecruitAllowed(role,economy,player,state,"recruit_choice") then'),
 ('RecruitAllowed(role,actual,freshPlayer,freshState)\n', 'RecruitAllowed(role,actual,freshPlayer,freshState,"recruit_write")\n'),
)

_SUPPORT_167 = '      local supported,why=KnownExpansionSupport(plot,player,contextID,oneValidation)\n      if why=="support_geometry_pending" then'
_OBSERVED_SUPPORT_167 = ('      local supported,why=KnownExpansionSupport(plot,player,contextID,oneValidation)\n'
 '      if qa then\n        qa.cheap_pass=qa.cheap_pass+1\n'
 '        local key=supported==true and "support_true" or(supported==false and "support_false" or "support_unknown")\n'
 '        qa[key]=qa[key]+1\n      end\n      if why=="support_geometry_pending" then')
EDITS_167 = EDITS[:5] + ((_SUPPORT_167, _OBSERVED_SUPPORT_167),) + EDITS[6:]

def _edit_rules(text: str, *, instrumented: bool = False):
    column = 1 if instrumented else 0
    legacy, sliced = text.count(EDITS[5][column]), text.count(EDITS_167[5][column])
    if legacy == 1 and sliced == 0:
        return EDITS
    if sliced == 1 and legacy == 0:
        return EDITS_167
    raise ValueError('Unknown or duplicate settlement support shape')


def transform(raw: str, *, source_version: int = 142) -> tuple[str,str]:
    if type(source_version) is not int or source_version not in (142,155,156,157,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,179):
        raise ValueError('Census requires exact source142 or155')
    text=raw
    for old,new in _edit_rules(raw):
        if text.count(old)!=1:
            raise ValueError('Unknown or duplicate settlement census anchor: '+old[:90])
        text=text.replace(old,new,1)
    collector=(ROOT/'tools/lua/diagnostic_settlement_census.lua').read_text(encoding='utf-8')
    runner=(ROOT/'tools/lua/diagnostic_settlement_runner.lua').read_text(encoding='utf-8')
    prefix='\n'.join([
        f'-- BAIQI_DIAGNOSTIC_ONLY: natural source{source_version} settlement census; no gameplay commands.',
        'assert(P6SettlementCensus==nil,"Existing settlement census owner")','do',
        ' local NewCensus=(function()\n'+collector+'\n end)()',
        ' P6SettlementCensus=NewCensus(256)',
        ' local Bind=(function()\n'+runner+'\n end)()',
        ' Bind(P6SettlementCensus,{turn=function() return Game.GetCurrentGameTurn() end,',
        '   clock=function() return Automation.GetTime() end})','end',''])
    changed=prefix+text
    if restore_release(changed,prefix)!=raw:
        raise ValueError('Census edits are not exactly reversible')
    return changed,prefix


def restore_release(text: str,prefix: str) -> str:
    if not text.startswith(prefix):
        raise ValueError('Unknown census prefix')
    text=text[len(prefix):]
    for old,new in reversed(_edit_rules(text, instrumented=True)):
        if text.count(new)!=1:
            raise ValueError('Unknown census inverse anchor')
        text=text.replace(new,old,1)
    return text


def build(output_dir: Path) -> dict:
    source=ROOT/'mod/Baiqi'
    version_text=ET.fromstring((source/'Baiqi.modinfo').read_bytes()).get('version')
    if version_text not in ('142','155','156','157','158','159','160','161','162','163','164','165','166','167','168','169','170','171','172','179'):
        raise ValueError('Census requires actual source142 or155')
    version=int(version_text)
    output_dir=output_dir.resolve()
    if (output_dir.exists() or output_dir==source.resolve()
        or output_dir.is_relative_to(source.resolve()) or source.resolve().is_relative_to(output_dir)):
        raise ValueError('Census output must be a separate new directory')
    files=manifest_files(source);contents={name:contained(source,name).read_bytes()for name in files}
    raw=contents[CONTROLLER].decode('utf-8');text,prefix=transform(raw,source_version=version)
    from lupa.lua51 import LuaRuntime as Lua51
    from lupa.lua53 import LuaRuntime as Lua53
    c51=Lua51().eval('function(s) local f,e=loadstring(s);assert(f,e) end')
    c53=Lua53().eval('function(s) local f,e=load(s);assert(f,e) end')
    count=0
    for name,data in contents.items():
        if name.endswith('.lua'):
            code=text if name==CONTROLLER else data.decode('utf-8-sig')
            c51(code);c53(code);count+=1
    if contents!={name:contained(source,name).read_bytes()for name in manifest_files(source)}:
        raise ValueError('Release source changed during census build')
    output_dir.mkdir(parents=True,exist_ok=False);target=output_dir/'Baiqi'
    for name,data in contents.items():
        dst=contained(target,name);dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(text.encode('utf-8')if name==CONTROLLER else data)
    changed=[name for name in files if contained(target,name).read_bytes()!=contents[name]]
    if manifest_files(target)!=files or changed!=[CONTROLLER]:raise ValueError('Unexpected census package differences')
    archive=output_dir/f'Baiqi-settlement{version}-census.zip'
    if package(target,archive)!=files:raise ValueError('Census archive inventory changed')
    result={'mode':f'baiqi{version}-settlement-census-v1','source_version':version,'files':len(files),
        'lua_sources_compiled_51_and_53':count,'changed_files':changed,'release_recovers_exactly':True,
        'selection_and_safety_call_count_unchanged':True,'metadata_reads_added':'Turn/city count at entry and exit, diagnostic clock twice per observed natural call.',
        'census_capacity':256,'timing_budget':'Separate diagnostic census; does not alter existing4096 planning sample cap or grant performance budgets.',
        'archive_sha256':digest(archive),'source_hashes':{k:hashlib.sha256(v).hexdigest()for k,v in contents.items()},
        'instrumented_hashes':{k:digest(target/k)for k in files},'installed':False,'Native_pressure_status':'UNVERIFIED'}
    with(output_dir/'diagnostic-build.json').open('x',encoding='utf-8')as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True)
    print(json.dumps(build(p.parse_args().output_dir),ensure_ascii=False))


if __name__=='__main__':main()
