"""Prepare a private source140 Stage A copy with two public planning targets."""
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

EXECUTOR='UI/BaiqiExecutor.lua'
HELPERS={'NewProfile':'diagnostic_profile','WrapWindow':'diagnostic_plan_window',
         'NewTrace':'diagnostic_qualification_trace','NewDeferred':'diagnostic_preanchor_proof',
         'NewPlanA':'diagnostic_plan_stage'}
INCLUDES='include("BaiqiController")\ninclude("BaiqiAdmin")\ninclude("BaiqiMissionaryPurchase")\n'
ACTIVATION_EDITS={
    'Events.PlayerTurnActivated.Add(Activate)':
        'local P6PlanActivation=P6PerfPlanA.WrapActivation(Activate)\nEvents.PlayerTurnActivated.Add(P6PlanActivation)',
    'Events.PlayerTurnActivated.Remove(Activate)':
        'Events.PlayerTurnActivated.Remove(P6PlanActivation)',
}


def restore_release(text: str,prefix: str,binding: str) -> str:
    if not text.startswith(prefix) or text.count(binding)!=1:
        raise ValueError('Unknown diagnostic prefix or binding')
    restored=text[len(prefix):].replace(binding,'',1)
    for old,new in ACTIVATION_EDITS.items():
        if restored.count(new)!=1:
            raise ValueError('Unknown diagnostic activation binding')
        restored=restored.replace(new,old,1)
    return restored


def transform(raw: str,source_version: int = 140) -> tuple[str,str,str]:
    if type(source_version)is not int or source_version not in (140,141):raise ValueError('Expected source140 or141')
    if raw.count(INCLUDES)!=1 or raw.count('local ready=false\n')!=1:
        raise ValueError('Current Executor include/bind site is unknown')
    site=raw.index('local ready=false\n')
    if raw.index(INCLUDES)+len(INCLUDES)!=site:
        raise ValueError('Expected public definitions immediately before ready state')
    lines=[f'-- BAIQI_DIAGNOSTIC_ONLY: independent source{source_version} Stage A.',
           "assert(P6PerfPlanA==nil,'Existing Stage A diagnostic owner')",'do']
    for name,stem in HELPERS.items():
        helper=(ROOT/f'tools/lua/{stem}.lua').read_text(encoding='utf-8')
        lines.append(f' local {name}=(function()\n{helper}\nend)()')
    version_arg='' if source_version==140 else ',141'
    lines+=[' P6PerfPlanA=NewPlanA({Game=Game,Players=Players,Automation=Automation,Events=Events},NewProfile,WrapWindow,NewTrace,NewDeferred'+version_arg+')',
            'end','']
    prefix='\n'.join(lines)
    binding="assert(P6PerfPlanA.Bind(BaiqiAdmin,BaiqiController),'Stage A binding failed')\n"
    text=prefix+raw[:site]+binding+raw[site:]
    for old,new in ACTIVATION_EDITS.items():
        if raw.count(old)!=1:
            raise ValueError('Unknown native activation Add/Remove site')
        text=text.replace(old,new,1)
    return text,prefix,binding


def build(output_dir: Path) -> dict:
    source=ROOT/'mod/Baiqi'
    files=manifest_files(source)
    version=ET.fromstring((source/'Baiqi.modinfo').read_bytes()).get('version')
    if version not in ('140','141'):raise ValueError('Independent Stage A assembler requires actual source140 or141')
    version=int(version)
    output_dir=output_dir.resolve()
    if (output_dir==source.resolve() or output_dir.is_relative_to(source.resolve())
            or source.resolve().is_relative_to(output_dir)):
        raise ValueError('Diagnostic output must be separate from release source')
    if output_dir.exists():
        raise ValueError('Diagnostic output must be a new directory')
    contents={name:contained(source,name).read_bytes() for name in files}
    raw=contents[EXECUTOR].decode('utf-8')
    text,prefix,binding=transform(raw,version)
    if restore_release(text,prefix,binding)!=raw:
        raise ValueError('Unexpected release text after removing declared QA edits')
    from lupa.lua51 import LuaRuntime as Lua51
    from lupa.lua53 import LuaRuntime as Lua53
    compile51=Lua51().eval('function(s) local f,e=loadstring(s);assert(f,e) end')
    compile53=Lua53().eval('function(s) local f,e=load(s);assert(f,e) end')
    lua_count=0
    for name,data in contents.items():
        if name.endswith('.lua'):
            code=data.decode('utf-8-sig');compile51(code);compile53(code);lua_count+=1
    compile51(text);compile53(text)
    if contents!={name:contained(source,name).read_bytes() for name in manifest_files(source)}:
        raise ValueError('Source changed while preparing Stage A')
    output_dir.mkdir(parents=True,exist_ok=False)
    target=output_dir/'Baiqi'
    for name,data in contents.items():
        dst=contained(target,name);dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(text.encode('utf-8') if name==EXECUTOR else data)
    if manifest_files(target)!=files:
        raise ValueError('Diagnostic inventory changed')
    changed=[name for name in files if contained(target,name).read_bytes()!=contents[name]]
    if changed!=[EXECUTOR]:
        raise ValueError('Unexpected diagnostic differences')
    archive=output_dir/f'Baiqi-plan{version}-stageA-v2.zip'
    if package(target,archive)!=files:
        raise ValueError('Diagnostic archive inventory changed')
    result={'mode':f'baiqi{version}-stageA-v2','source_version':version,'files':len(files),
            'lua_sources_compiled_51_and_53':lua_count,'changed_files':changed,
            'release_bodies_unchanged':False,'gameplay_planning_bodies_unchanged':True,
            'shutdown_subscription_identity_adjusted':True,'release_text_recovers_exactly':True,
            'sample_capacity':4096,'aggregate_zero':False,
            'native_activation_inline_anchor':True,
            'pre_anchor_proof':'Exact single false Controller call; retained whole interval must end before actual Native anchor, pending must resolve. No budget relaxation.',
            'targets':['Admin.Run','Controller.RunNow'],'source':str(source),
            'diagnostic_source':str(target),'executor_sha256':digest(source/EXECUTOR),
            'instrumented_sha256':digest(target/EXECUTOR),'archive_sha256':digest(archive),
            'source_hashes':{name:hashlib.sha256(data).hexdigest() for name,data in contents.items()},
            'instrumented_hashes':{name:digest(target/name) for name in files},
            'helper_hashes':{stem:digest(ROOT/f'tools/lua/{stem}.lua') for stem in HELPERS.values()},
            'installed':False,'limits':'Stage A only; five-window ten-city Native sample quality and performance remain unverified.'}
    (output_dir/'diagnostic-build.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(build(a.output_dir),ensure_ascii=False))


if __name__=='__main__':
    main()
