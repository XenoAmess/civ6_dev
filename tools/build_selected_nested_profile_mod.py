"""Create a bounded private Controller subfunction diagnostic, without installing it."""
from __future__ import annotations
import argparse,json,shutil,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
from tools.build_mod import contained,digest,manifest_files,package
from tools.lua_function_instrument import instrument,lua_string
ROOT=Path(__file__).resolve().parents[1]
TARGETS=('BaiqiController.RunNow','Tick','PlayerContext','RefreshSettlement','ReadBack',
 'NextCityForPlanning','ProcessCity','Economy','FirstHolySiteWanted','ProcessBuilder',
 'AdvanceBuilderRoute','BuilderTargets','ProcessSettler','SettlementSites','ProcessTrader',
 'KnownExpansionSupport','ProcessNaturalistPurchase','missionaryPurchase.Process')
def transform(raw:str,profile:str,selected:str)->tuple[str,list[dict]]:
    body,coverage=instrument(raw,'Lua/BaiqiController.lua')
    for name in TARGETS:
        if sum(row['name']==name for row in coverage)!=1:raise ValueError('Selected definition not unique: '+name)
    names='{'+','.join(lua_string(n)for n in TARGETS)+'}'
    prefix=('local P6OwnWrap=(function()\nlocal NewProfile=(function()\nlocal unpack=unpack or table.unpack\n'+profile+
      '\nend)()\nlocal NewSelected=(function()\n'+selected+'\nend)()\n'+
      "if P6PerfNested183~=nil then local old=P6PerfNested183.Read();assert(old.marker=='baiqi183-selected-nested/v1'and not old.enabled);assert(P6PerfNested183.Retire())end\n"+
      'local wrap,api=NewSelected(NewProfile,Automation.GetTime,Game.GetCurrentGameTurn,Game.GetLocalPlayer,'+names+',512)\nP6PerfNested183=api\nreturn wrap\nend)()\n')
    return prefix+body,coverage
def build(output:Path)->dict:
    from lupa.lua51 import LuaRuntime as L51
    from lupa.lua53 import LuaRuntime as L53
    source=ROOT/'mod/Baiqi';output=output.resolve();files=manifest_files(source)
    if ET.fromstring((source/'Baiqi.modinfo').read_bytes()).get('version')!='183':raise ValueError('Requires exact source183')
    if output.exists()or output==source.resolve()or output.is_relative_to(source.resolve())or source.resolve().is_relative_to(output):raise ValueError('Requires new independent directory')
    hashes={n:digest(contained(source,n))for n in files}
    raw=contained(source,'Lua/BaiqiController.lua').read_text(encoding='utf-8-sig')
    helper_names=['diagnostic_profile','diagnostic_selected_nested'];helpers={n:(ROOT/f'tools/lua/{n}.lua').read_text(encoding='utf-8')for n in helper_names}
    text,coverage=transform(raw,helpers['diagnostic_profile'],helpers['diagnostic_selected_nested'])
    count=0
    for n in files:
        if n.endswith('.lua'):
            original=contained(source,n).read_text(encoding='utf-8-sig');candidate=text if n=='Lua/BaiqiController.lua'else original
            for VM in (L51,L53):VM().compile(original);VM().compile(candidate)
            count+=1
    if hashes!={n:digest(contained(source,n))for n in files}:raise ValueError('Source changed while preparing')
    target=output/'Baiqi';target.mkdir(parents=True)
    for n in files:
        p=contained(target,n);p.parent.mkdir(parents=True,exist_ok=True)
        if n=='Lua/BaiqiController.lua':p.write_text(text,encoding='utf-8',newline='\n')
        else:shutil.copy2(contained(source,n),p)
    actual={n:digest(contained(target,n))for n in files};changed=[n for n in files if actual[n]!=hashes[n]]
    if changed!=['Lua/BaiqiController.lua']or manifest_files(target)!=files:raise ValueError('Unexpected private changes')
    regenerated,_=transform(raw,helpers['diagnostic_profile'],helpers['diagnostic_selected_nested'])
    if contained(target,'Lua/BaiqiController.lua').read_bytes()!=regenerated.encode('utf-8'):raise ValueError('Transform mismatch')
    archive=output/'Baiqi183-selected-nested.zip';package(target,archive)
    with zipfile.ZipFile(archive)as z:
        if len(z.namelist())!=len(files)or set(z.namelist())!={'Baiqi/'+n for n in files}or any(z.read('Baiqi/'+n)!=contained(target,n).read_bytes()for n in files):raise ValueError('ZIP mismatch')
    v={'mode':'baiqi183-private-selected-nested-v1','source_version':183,'files':len(files),'Lua_sources_compiled_each_VM':count,'changed_files':changed,'source_hashes':hashes,'instrumented_hashes':actual,'selected_functions':list(TARGETS),'capacity':512,'canonical_profile_unchanged':True,'helper_hashes':{n:digest(ROOT/f'tools/lua/{n}.lua')for n in helper_names},'archive_sha256':digest(archive),'compiled_Lua_versions':['5.1','5.3'],'coverage':coverage,'actual_transform_and_ZIP_verified':True,'installed':False,'Native':0,'acceptance_budget_credit':False}
    (output/'diagnostic-build.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');return v
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();v=build(a.output_dir);print(json.dumps({k:v[k]for k in ['mode','source_version','files','Lua_sources_compiled_each_VM','changed_files','archive_sha256','installed']}))
