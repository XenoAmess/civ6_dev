"""Build a private passive initial-world observer; never install or start a game."""
from pathlib import Path
import argparse,hashlib,json,xml.etree.ElementTree as ET
from tools.build_mod import ROOT,contained,digest,manifest_files,package
CONTROLLER='Lua/BaiqiController.lua'
HELPER=ROOT/'tools/lua/diagnostic_initial_world.lua'
def transform(raw:str)->tuple[str,str]:
    exports=('function BaiqiController.RunNow(', 'function BaiqiController.Update(', 'function BaiqiController.Shutdown(')
    if any(raw.count(token)!=1 for token in exports)or '\nreturn BaiqiController' in raw:raise ValueError('Unknown global Controller exports')
    if 'P6InitialWorld173Trace' in raw:raise ValueError('Observer already present')
    helper=HELPER.read_text(encoding='utf-8')
    insertion='\ndo\nassert(P6InitialWorld173Trace==nil)\nlocal Create=(function()\n'+helper+'\nend)()\nP6InitialWorld173Trace=Create({Game=Game,PlayerConfigurations=PlayerConfigurations,Players=Players,GameInfo=GameInfo,Map=Map,PlayersVisibility=PlayersVisibility,UnitManager=UnitManager,UnitOperationTypes=UnitOperationTypes,OperationResultsTypes=OperationResultsTypes,print=print},BaiqiController)\nend\n'
    changed=raw+insertion
    if restore(changed,insertion)!=raw:raise ValueError('Inexact inverse')
    return changed,insertion
def restore(text:str,insertion:str)->str:
    if not insertion or text.count(insertion)!=1:raise ValueError('Unknown observer insertion')
    return text.replace(insertion,'',1)
def build(output:Path)->dict:
    source=ROOT/'mod/Baiqi';version=ET.fromstring((source/'Baiqi.modinfo').read_bytes()).get('version')
    if version!='173':raise ValueError('Reviewed for source173 only')
    output=output.resolve()
    if output.exists()or output==source.resolve()or output.is_relative_to(source.resolve())or source.resolve().is_relative_to(output):raise ValueError('Output must be new and separate')
    files=manifest_files(source);contents={n:contained(source,n).read_bytes()for n in files}
    text,insertion=transform(contents[CONTROLLER].decode('utf-8'))
    from lupa.lua51 import LuaRuntime as L51
    from lupa.lua53 import LuaRuntime as L53
    for Runtime in (L51,L53):Runtime().compile(text)
    if contents!={n:contained(source,n).read_bytes()for n in manifest_files(source)}:raise ValueError('Source changed during build')
    output.mkdir(parents=True);target=output/'Baiqi'
    for n,raw in contents.items():
        p=contained(target,n);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(text.encode('utf-8')if n==CONTROLLER else raw)
    changed=[n for n in files if contained(target,n).read_bytes()!=contents[n]]
    if manifest_files(target)!=files or changed!=[CONTROLLER]:raise ValueError('Unexpected diagnostic differences')
    archive=output/'Baiqi-initial173-passive.zip';assert package(target,archive)==files
    result={'source_version':173,'mode':'baiqi173-passive-initial-world-v1','files':len(files),'changed_files':changed,'release_recovers_exactly':True,'source_hashes':{n:hashlib.sha256(raw).hexdigest()for n,raw in contents.items()},'instrumented_hashes':{n:digest(target/n)for n in files},'archive_sha256':digest(archive),'helper_sha256':digest(HELPER),'insertion_sha256':hashlib.sha256(insertion.encode()).hexdigest(),'modified_Controller_compiled_Lua51_Lua53':True,'installed':False,'Native_status':'UNVERIFIED','limits':'Passive getter snapshots around unchanged original public calls. No original invocation added, pause/admission change, SDK requests or game setters. Not a performance proof. Runtime presence and first0city snapshot remain required.'}
    with(output/'diagnostic-build.json').open('x',encoding='utf-8')as f:json.dump(result,f,indent=2)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);print(json.dumps(build(p.parse_args().output_dir),indent=2))
