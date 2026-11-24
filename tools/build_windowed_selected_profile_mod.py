"""Build a private two-window Controller diagnostic, without installing it."""
from __future__ import annotations
import argparse,json,shutil,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
from tools.build_mod import contained,digest,manifest_files,package
from tools.lua_function_instrument import instrument,lua_string
from tools.build_selected_nested_profile_mod import TARGETS as PREVIOUS_TARGETS

ROOT=Path(__file__).resolve().parents[1]
TARGETS=PREVIOUS_TARGETS+('PrepareBuilderPathPacket','ValidateBuilderPathPacket','PathStep',
    'RequestCivilian','UnitSnapshot','districtRoute.Run','RetryCivilianOverlap','Safe','GetVisibleUnits')
NATIVE_SITES=(
    ('overlap-choice','pcall(UnitManager.GetMoveToPathEx,unit,choice.index)',
     "pcall(P6PerfWindow184.Path,'overlap-choice',UnitManager.GetMoveToPathEx,unit,choice.index)"),
    ('overlap-edge','pcall(pathQuery,unit,index)',
     "pcall(P6PerfWindow184.Path,'overlap-edge',pathQuery,unit,index)"),
    ('path-step','UnitManager.GetMoveToPathEx(unit, target:GetIndex())',
     "P6PerfWindow184.Path('path-step',UnitManager.GetMoveToPathEx,unit,target:GetIndex())"),
    ('builder-packet','pcall(UnitManager.GetMoveToPathEx, unit, targetIndex)',
     "pcall(P6PerfWindow184.Path,'builder-packet',UnitManager.GetMoveToPathEx,unit,targetIndex)"),
    ('district-route','pcall(query,unit,job.endpoint or job.index)',
     "pcall(P6PerfWindow184.Path,'district-route',query,unit,job.endpoint or job.index)"),
)

def native_path_source(raw:str)->str:
    if 'P6PerfWindow184' in raw:raise ValueError('Reserved private diagnostic name')
    for site,before,after in NATIVE_SITES:
        if raw.count(before)!=1:raise ValueError('Native site not unique: '+site)
        raw=raw.replace(before,after)
    return raw

def transform(raw:str,profile:str,windowed:str)->tuple[str,list[dict]]:
    body,coverage=instrument(native_path_source(raw),'Lua/BaiqiController.lua')
    for name in TARGETS:
        if sum(row['name']==name for row in coverage)!=1:
            raise ValueError('Selected definition not unique: '+name)
    names='{'+','.join(lua_string(n)for n in TARGETS)+'}'
    prefix=('local P6OwnWrap=(function()\nlocal NewProfile=(function()\n'
      'local unpack=unpack or table.unpack\n'+profile+'\nend)()\n'
      'local NewWindowed=(function()\n'+windowed+'\nend)()\n'
      "if P6PerfWindow184~=nil then local old=P6PerfWindow184.Read();assert(old.marker=='baiqi184-windowed-selected/v1'and not old.enabled);assert(P6PerfWindow184.Retire())end\n"
      'local wrap,api=NewWindowed(NewProfile,Automation.GetTime,Game.GetCurrentGameTurn,'
      'Game.GetLocalPlayer,'+names+',2048,86,87)\nP6PerfWindow184=api\nreturn wrap\nend)()\n')
    return prefix+body,coverage

def build(output:Path)->dict:
    from lupa.lua51 import LuaRuntime as L51
    from lupa.lua53 import LuaRuntime as L53
    source=ROOT/'mod/Baiqi';output=output.resolve();files=manifest_files(source)
    if ET.fromstring((source/'Baiqi.modinfo').read_bytes()).get('version')!='184':
        raise ValueError('Requires exact current source184')
    if output.exists()or output==source.resolve()or output.is_relative_to(source.resolve())or source.resolve().is_relative_to(output):
        raise ValueError('Requires a new independent output directory')
    hashes={n:digest(contained(source,n))for n in files}
    helper_names=('diagnostic_profile','diagnostic_windowed_selected')
    helpers={n:(ROOT/f'tools/lua/{n}.lua').read_text(encoding='utf-8')for n in helper_names}
    raw=contained(source,'Lua/BaiqiController.lua').read_text(encoding='utf-8-sig')
    text,coverage=transform(raw,helpers['diagnostic_profile'],helpers['diagnostic_windowed_selected'])
    count=0
    for n in files:
        if n.endswith('.lua'):
            original=contained(source,n).read_text(encoding='utf-8-sig')
            for VM in(L51,L53):VM().compile(original);VM().compile(text if n=='Lua/BaiqiController.lua'else original)
            count+=1
    if hashes!={n:digest(contained(source,n))for n in files}:raise ValueError('Source changed')
    target=output/'Baiqi';target.mkdir(parents=True)
    for n in files:
        p=contained(target,n);p.parent.mkdir(parents=True,exist_ok=True)
        if n=='Lua/BaiqiController.lua':p.write_text(text,encoding='utf-8',newline='\n')
        else:shutil.copy2(contained(source,n),p)
    actual={n:digest(contained(target,n))for n in files}
    if [n for n in files if actual[n]!=hashes[n]]!=['Lua/BaiqiController.lua']or manifest_files(target)!=files:
        raise ValueError('Unexpected private file changes')
    regenerated,_=transform(raw,helpers['diagnostic_profile'],helpers['diagnostic_windowed_selected'])
    if contained(target,'Lua/BaiqiController.lua').read_bytes()!=regenerated.encode():raise ValueError('Transform mismatch')
    archive=output/'Baiqi184-windowed-selected.zip';package(target,archive)
    with zipfile.ZipFile(archive)as z:
        if len(z.namelist())!=len(files)or set(z.namelist())!={'Baiqi/'+n for n in files}or any(z.read('Baiqi/'+n)!=contained(target,n).read_bytes()for n in files):raise ValueError('ZIP mismatch')
    v={'mode':'baiqi184-private-windowed-selected-v1','source_version':184,'files':len(files),
       'Lua_sources_compiled_each_VM':count,'changed_files':['Lua/BaiqiController.lua'],
       'source_hashes':hashes,'instrumented_hashes':actual,'selected_functions':list(TARGETS),
       'Native_path_sites':[s[0]for s in NATIVE_SITES],'Native_site_coverage_limit':'Only these five explicit owned callsites; captured path bindings elsewhere are not claimed instrumented.',
       'first_turn':86,'last_turn':87,'seconds_each':10,'capacity':2048,'coverage':coverage,
       'helper_hashes':{n:digest(ROOT/f'tools/lua/{n}.lua')for n in helper_names},
       'archive_sha256':digest(archive),'canonical_profile_and_183_diagnostic_unchanged':True,
       'actual_transform_and_ZIP_verified':True,'installed':False,'Native':0,'acceptance_budget_credit':False}
    (output/'diagnostic-build.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return v

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,required=True)
    v=build(parser.parse_args().output_dir)
    print(json.dumps({k:v[k]for k in('mode','source_version','files','Lua_sources_compiled_each_VM','selected_functions','Native_path_sites','archive_sha256','installed')}))
