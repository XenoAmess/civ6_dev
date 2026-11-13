"""Assemble versioned private behavior-closed comparison; does not install."""
from __future__ import annotations
import argparse,json,shutil,sys
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
if __package__ in (None,''):sys.path.insert(0,str(ROOT))
from tools.build_mod import contained,digest,manifest_files,package
from tools.static_control_source import transform,edits


def clock_prelude() -> str:
    module=(ROOT/'tools/lua/benchmark_turn_clock.lua').read_text(encoding='utf-8')
    return '''-- PRIVATE matched-turn diagnostic, identical in both variants.
if P6PairClock~=nil then
 assert(type(P6PairClock)=='table' and P6PairClock.marker=='baiqi67-paired-clock-v1')
 assert(P6PairClock:Retire())
end
local _P6PairNew=(function()
'''+module+'''
end)()
P6PairClock=_P6PairNew(Automation.GetTime,Game.GetCurrentGameTurn,Game.GetLocalPlayer,Events.PlayerTurnActivated,16)
assert(P6PairClock:Snapshot().subscribed and P6PairClock:Snapshot().errors==0)
'''


def build(output_dir: Path,*,paired_clock: bool = False,variant: str = 'control') -> dict:
    from lupa.lua53 import LuaRuntime
    if type(paired_clock) is not bool or variant not in ('control','enabled'):raise ValueError('Invalid private variant')
    if variant=='enabled' and not paired_clock:raise ValueError('Enabled variant requires matched stopwatch')
    source=ROOT/'mod/Baiqi';files=manifest_files(source)
    version=ET.fromstring((source/'Baiqi.modinfo').read_bytes()).get('version')
    if version not in ('67','68','69','70','71','72','73','74','75','76','77','78','79','80','81','82','83','84','85','86','87','88','89','90','91','92','93','94','95','96','97','98','99','100','101','102','103','104','105','106','107','108','109','110','111','112','113','114','115','116','117','118','119','120','121','122','123','124','125','126','127','128','129','130','131','132','133','134','135','136','137','138','139'):raise ValueError('Expected actual source67 through136')
    version=int(version)
    output_dir=output_dir.resolve()
    if output_dir==source.resolve() or output_dir.is_relative_to(source.resolve()) or source.resolve().is_relative_to(output_dir):raise ValueError('Separate output required')
    if output_dir.exists():raise ValueError('New output directory required')
    hashes={n:digest(contained(source,n)) for n in files}
    if not set(edits(version)).issubset(files):raise ValueError('Missing static control target')
    lua=LuaRuntime(unpack_returned_tuples=True)
    compile_lua=lua.eval('function(s,n) local f,e=load(s,n);assert(f,e);return true end')
    prepared={};coverage={};prefix=clock_prelude() if paired_clock else ''
    for name in files:
        if not name.endswith('.lua'):continue
        raw=contained(source,name).read_text(encoding='utf-8-sig');compile_lua(raw,name)
        result,report=transform(raw,name,version) if variant=='control' else (raw,[])
        if paired_clock and name=='UI/BaiqiExecutor.lua':
            if 'P6PairClock' in result or '_P6PairNew' in result:raise ValueError('Paired-clock name collision')
            result=prefix+result
            report=report+[{'prefix':'identical paired stopwatch; before original includes/event registration'}]
        compile_lua(result,name+'-static-control')
        if report:prepared[name]=result.encode('utf-8');coverage[name]=report
    if hashes!={n:digest(contained(source,n)) for n in files}:raise ValueError('Release source changed')
    output_dir.mkdir(parents=True,exist_ok=False);target=output_dir/'Baiqi'
    for name in files:
        src,dst=contained(source,name),contained(target,name);dst.parent.mkdir(parents=True,exist_ok=True)
        if name in prepared:dst.write_bytes(prepared[name])
        else:shutil.copy2(src,dst)
    if manifest_files(target)!=files:raise ValueError('Inventory changed')
    archive=output_dir/(f'Baiqi-paired{version}-{variant}.zip' if paired_clock else f'Baiqi-static-control{version}.zip');package(target,archive)
    import hashlib
    result={'mode':f'baiqi{version}-paired-{variant}-c2' if paired_clock else f'baiqi{version}-static-control-c1','variant':variant,'paired_clock':paired_clock,'clock_prefix_sha256':hashlib.sha256(prefix.encode('utf-8')).hexdigest() if paired_clock else None,'clock_source_sha256':digest(ROOT/'tools/lua/benchmark_turn_clock.lua') if paired_clock else None,'source_version':version,'files':len(files),'changed_files':list(prepared),'coverage':coverage,'source_hashes':hashes,'control_hashes':{n:digest(contained(target,n)) for n in files},'archive_sha256':digest(archive),'installed':False,'limits':'Private candidate comparison only. Same manifest/assets/readonly UI guards. Control closes UI planners/recovery and Core mutation bridges/automatic bootstrap lexically before capture; enabled preserves original bodies. Legacy withdrawn-effect cleanup kept. Optional identical stopwatch before Executor callbacks, no game actions. Compile is not software/Native validity or B_delta evidence.'}
    (output_dir/'static-control-build.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True);parser.add_argument('--paired-clock',action='store_true');parser.add_argument('--variant',choices=('control','enabled'),default='control');args=parser.parse_args()
    result=build(args.output_dir,paired_clock=args.paired_clock,variant=args.variant);print(json.dumps({k:result[k] for k in ('mode','files','changed_files','archive_sha256','installed')}))
