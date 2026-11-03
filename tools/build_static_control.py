"""Assemble source67 private behavior-closed comparison; does not install."""
from __future__ import annotations
import argparse,json,shutil,sys
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
if __package__ in (None,''):sys.path.insert(0,str(ROOT))
from tools.build_mod import contained,digest,manifest_files,package
from tools.static_control_source import transform,edits


def build(output_dir: Path) -> dict:
    from lupa.lua53 import LuaRuntime
    source=ROOT/'mod/Baiqi';files=manifest_files(source)
    if ET.fromstring((source/'Baiqi.modinfo').read_bytes()).get('version')!='67':raise ValueError('Expected actual source67')
    output_dir=output_dir.resolve()
    if output_dir==source.resolve() or output_dir.is_relative_to(source.resolve()) or source.resolve().is_relative_to(output_dir):raise ValueError('Separate output required')
    if output_dir.exists():raise ValueError('New output directory required')
    hashes={n:digest(contained(source,n)) for n in files}
    if not set(edits()).issubset(files):raise ValueError('Missing static control target')
    lua=LuaRuntime(unpack_returned_tuples=True)
    compile_lua=lua.eval('function(s,n) local f,e=load(s,n);assert(f,e);return true end')
    prepared={};coverage={}
    for name in files:
        if not name.endswith('.lua'):continue
        raw=contained(source,name).read_text(encoding='utf-8-sig');compile_lua(raw,name)
        result,report=transform(raw,name);compile_lua(result,name+'-static-control')
        if report:prepared[name]=result.encode('utf-8');coverage[name]=report
    if hashes!={n:digest(contained(source,n)) for n in files}:raise ValueError('Release source changed')
    output_dir.mkdir(parents=True,exist_ok=False);target=output_dir/'Baiqi'
    for name in files:
        src,dst=contained(source,name),contained(target,name);dst.parent.mkdir(parents=True,exist_ok=True)
        if name in prepared:dst.write_bytes(prepared[name])
        else:shutil.copy2(src,dst)
    if manifest_files(target)!=files:raise ValueError('Inventory changed')
    archive=output_dir/'Baiqi-static-control67.zip';package(target,archive)
    result={'mode':'baiqi67-static-control-c1','source_version':67,'files':len(files),'changed_files':list(prepared),'coverage':coverage,'source_hashes':hashes,'control_hashes':{n:digest(contained(target,n)) for n in files},'archive_sha256':digest(archive),'installed':False,'limits':'Private candidate comparison only. Same manifest/assets/readonly UI guards; UI planners/recovery and Core mutation bridges/automatic bootstrap closed lexically before capture. Legacy withdrawn-effect cleanup kept. Compile is not software/Native validity or B_delta evidence.'}
    (output_dir/'static-control-build.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args()
    result=build(args.output_dir);print(json.dumps({k:result[k] for k in ('mode','files','changed_files','archive_sha256','installed')}))
