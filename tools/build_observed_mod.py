"""Build a private source67/139 diagnostic copy; never install release files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
if __package__ in (None,''):
    sys.path.insert(0,str(ROOT))
from tools.build_mod import contained,digest,manifest_files,package
from tools.lua_function_instrument import instrument,lua_string
from tools.lua_write_instrument import instrument_writes
from tools.diagnostic_quotas import bounded_quotas,MAX_RETAINED_SAMPLES

# Runtime instrumentation schema; retained for compatibility, not a product version.
MARKER='baiqi67-q19'
HELPERS={'NewProfile':'diagnostic_profile','NewRoots':'diagnostic_owned_roots',
         'NewCounter':'diagnostic_queries','NewLeaves':'diagnostic_write_leaves',
         'NewContext':'diagnostic_context'}


def prelude(key: str,quotas: dict | None = None) -> str:
    lines=['-- BAIQI_DIAGNOSTIC_ONLY: source67 owned definitions and Native leaves.',
           'if P6OwnDiag==nil then']
    for name,stem in HELPERS.items():
        text=(ROOT/f'tools/lua/{stem}.lua').read_text(encoding='utf-8')
        lines.append(f' local {name}=(function()\n{text}\nend)()')
    settings=''
    if quotas is not None:
        settings=f',SampleQuota={quotas.get(key,1)},AggregateZero=true,UnknownQuota={str(key not in quotas).lower()}'
    lines.append(f' P6OwnDiag=NewContext({lua_string(key)},{{Game=Game,Automation=Automation,Events=Events,ExposedMembers=ExposedMembers{settings}}},NewProfile,NewRoots,NewCounter,NewLeaves)')
    lines+=['end','local P6Context=P6OwnDiag',
            f'local P6Owned=type(P6Context)=="table" and P6Context.marker=="{MARKER}"',
            'local P6OwnWrap=function(label,fn) if not P6Owned then return fn end;return P6Context:Wrap(label,fn) end',
            'local P6WriteRef=function(label,fn,skipGuard)',
            ' if not P6Owned or (skipGuard and BaiqiUIGuard~=nil) then return fn end',
            ' return P6Context.Leaves:Static(label,fn)','end',
            'local P6WriteMethod=function(label,native,method)',
            ' if not P6Owned then local fn=native[method];if type(fn)~="function" then return fn end;return function(...) return fn(native,...) end end',
            ' return P6Context.Leaves:Method(label,native,method)','end','']
    return '\n'.join(lines)


def transform(source: str,key: str,quotas: dict | None = None) -> tuple[str,dict]:
    writes,write_manifest=instrument_writes(source,key)
    text,function_manifest=instrument(writes,key)
    chunk=f'return P6OwnWrap({lua_string(key+":$chunk")},function(...)\n'+text+'\nend)(...)\n'
    return prelude(key,quotas)+chunk,{'functions':function_manifest,'write_sites':write_manifest,'top_level_chunk_wrapped':True}


def build(output_dir: Path,*,bounded_zero: bool = False) -> dict:
    from lupa.lua53 import LuaRuntime
    source=ROOT/'mod/Baiqi'
    files=manifest_files(source)
    info=ET.fromstring((source/'Baiqi.modinfo').read_bytes())
    version=info.get('version')
    if version not in ('67','139'):
        raise ValueError('Diagnostic assembler requires actual source67 or139')
    if version=='139' and not bounded_zero:
        raise ValueError('Source139 diagnostics require bounded_zero and the frozen4096 cap')
    expected=[e.findtext('Properties/LuaReplace') for e in info.findall('InGameActions/ReplaceUIScript')]
    expected+=['UI/BaiqiExecutor.lua','Lua/BaiqiGameplay.lua']
    quotas=bounded_quotas(expected) if bounded_zero else None
    output_dir=output_dir.resolve()
    if output_dir==source.resolve() or output_dir.is_relative_to(source.resolve()) or source.resolve().is_relative_to(output_dir):
        raise ValueError('Diagnostic output must be separate from release source')
    if output_dir.exists():
        raise ValueError('Diagnostic output must be a new directory')
    lua=LuaRuntime(unpack_returned_tuples=True)
    compile_lua=lua.eval('function(s,n) local f,e=load(s,n);assert(f,e);return true end')
    compile_lua51=None
    if version=='139':
        from lupa.lua51 import LuaRuntime as Lua51Runtime
        lua51=Lua51Runtime(unpack_returned_tuples=True)
        compile_lua51=lua51.eval('function(s,n) local f,e=loadstring(s,n);assert(f,e);return true end')
    prepared={}
    coverage={}
    hashes={name:digest(contained(source,name)) for name in files}
    for name in files:
        if name.endswith('.lua'):
            raw=contained(source,name).read_text(encoding='utf-8-sig')
            compile_lua(raw,name)
            text,coverage[name]=transform(raw,name,quotas)
            if version=='139':
                text=text.replace('-- BAIQI_DIAGNOSTIC_ONLY: source67 owned definitions and Native leaves.',
                                  '-- BAIQI_DIAGNOSTIC_ONLY: source139; runtime instrumentation schema baiqi67-q19.',1)
            compile_lua(text,name+'-q19')
            if compile_lua51:
                compile_lua51(raw,name)
                compile_lua51(text,name+'-q21-bounded')
            prepared[name]=text.encode('utf-8')
    if hashes!={name:digest(contained(source,name)) for name in files}:
        raise ValueError('Release source changed during diagnostic preparation')
    output_dir.mkdir(parents=True,exist_ok=False)
    target=output_dir/'Baiqi'
    for name in files:
        src,dst=contained(source,name),contained(target,name)
        dst.parent.mkdir(parents=True,exist_ok=True)
        if name in prepared:dst.write_bytes(prepared[name])
        else:shutil.copy2(src,dst)
    if manifest_files(target)!=files:
        raise ValueError('Diagnostic inventory changed')
    changed=[name for name in files if digest(contained(target,name))!=hashes[name]]
    if set(changed)!=set(prepared):
        raise ValueError('Unexpected diagnostic source differences')
    mode=f'baiqi{version}-q21-bounded' if bounded_zero else MARKER
    archive=output_dir/(f'Baiqi-diagnostic{version}-q21-bounded.zip' if bounded_zero else 'Baiqi-diagnostic67-q19.zip')
    package(target,archive)
    result={'mode':mode,'source_version':int(version),'files':len(files),'changed_files':changed,
            'expected_entry_keys':sorted(expected),'source_hashes':hashes,
            'aggregate_zero':bounded_zero,'context_quotas':quotas,
            'global_retained_sample_capacity':MAX_RETAINED_SAMPLES if bounded_zero else None,
            'instrumented_hashes':{name:digest(contained(target,name)) for name in files},
            'helper_hashes':{stem:digest(ROOT/f'tools/lua/{stem}.lua') for stem in HELPERS.values()},
            'coverage':coverage,'archive_sha256':digest(archive),'installed':False,
            'limits':'Private inclusive walltime envelope, Native/vanilla callees included. Clock resolution, runtime active contexts and full-window completeness require actual evidence. No product controls.'}
    if version=='139':
        result['runtime_marker']=MARKER
        result['lua_compile_versions']=['5.1','5.3']
    (output_dir/'diagnostic-build.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True,type=Path)
    parser.add_argument('--bounded-zero',action='store_true',help='Aggregate measured-zero normal calls; legacy32 or source11133 context quotas sum to frozen global4096')
    args=parser.parse_args()
    result=build(args.output_dir,bounded_zero=args.bounded_zero)
    print(json.dumps({k:result[k] for k in ('mode','source_version','files','changed_files','expected_entry_keys','archive_sha256','installed')},ensure_ascii=False))
