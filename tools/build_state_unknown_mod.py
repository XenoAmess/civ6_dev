"""Build a reversible private source183 F07 state-read diagnostic."""
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
from tools.build_formation_unknown_mod import ANCHOR,SNAPSHOT_SOURCE,CONTROLLER

HELPER='tools/lua/diagnostic_state_unknown.lua'
ORIGINAL_READ='UnitManager.CanStartOperation(fresh,operation.Hash,nil)'
PRIVATE_READ='P6TC040183ReadOperation(fresh,operation.Hash,nil)'

def transform(raw:str,owner:int,unit_id:int,limit:int=64)->tuple[str,str]:
    for n in (owner,unit_id):
        if type(n)is not int or not 0<=n<=2147483647:
            raise ValueError('Exact nonnegative owner and full ID required')
    if type(limit)is not int or not 1<=limit<=64:
        raise ValueError('Limit must be1..64')
    if raw.count(SNAPSHOT_SOURCE+ANCHOR)!=1 or raw.count(ANCHOR)!=1 or raw.count(ORIGINAL_READ)!=1:
        raise ValueError('Unknown or duplicate snapshot/missionary qualifier source')
    if 'P6TC040183'in raw:
        raise ValueError('Existing private diagnostic')
    helper=(ROOT/HELPER).read_text(encoding='utf-8')
    insertion='\n'.join([
        '\n-- BAIQI_DIAGNOSTIC_ONLY: F07 missing values after unchanged real SDK reads.',
        'local P6TC040183ReadOperation',
        'assert(P6TC040183==nil,"Existing private state diagnostic")','do',
        ' local originalSnapshot=UnitSnapshot',
        ' local originalQualifier=UnitManager.CanStartOperation',
        ' local New=(function()\n'+helper+'\n end)()',
        f' local api=New(originalSnapshot,originalQualifier,{owner},{unit_id},"UNIT_MISSIONARY",1592408602,{limit})',
        ' UnitSnapshot=api.Snapshot;P6TC040183ReadOperation=api.Qualify',
        ' local originalArm=api.Arm',
        ' function api.Arm(...)',
        '  if UnitSnapshot~=api.Snapshot or P6TC040183ReadOperation~=api.Qualify',
        '    or UnitManager.CanStartOperation~=originalQualifier then return false,"foreign_binding" end',
        '  return originalArm(...)',' end',
        ' function api.Retire()',
        '  if UnitSnapshot==originalSnapshot and P6TC040183ReadOperation==originalQualifier and api.Read().retired then return true,"already_retired" end',
        '  if UnitSnapshot~=api.Snapshot or P6TC040183ReadOperation~=api.Qualify',
        '    or UnitManager.CanStartOperation~=originalQualifier then return false,"foreign_binding_preserved" end',
        '  UnitSnapshot=originalSnapshot;P6TC040183ReadOperation=originalQualifier;api.Disable();return true,"restored"',
        ' end',
        ' P6TC040183=api','end',''])
    changed=raw.replace(ORIGINAL_READ,PRIVATE_READ,1).replace(ANCHOR,insertion+ANCHOR,1)
    if restore_release(changed,insertion)!=raw:
        raise ValueError('Diagnostic inverse failed')
    return changed,insertion

def restore_release(text:str,insertion:str)->str:
    if not insertion or text.count(insertion)!=1 or text.count(PRIVATE_READ)!=1:
        raise ValueError('Unknown diagnostic insertion or qualification site')
    return text.replace(insertion,'',1).replace(PRIVATE_READ,ORIGINAL_READ,1)

def build(output:Path,owner:int,unit_id:int,limit:int=64)->dict:
    source=ROOT/'mod/Baiqi'
    if ET.fromstring((source/'Baiqi.modinfo').read_bytes()).get('version')!='183':
        raise ValueError('This diagnostic is qualified only for actual source183')
    output=output.resolve()
    if output.exists()or output==source.resolve()or output.is_relative_to(source.resolve())or source.resolve().is_relative_to(output):
        raise ValueError('Use a new separate private output directory')
    files=manifest_files(source);contents={n:contained(source,n).read_bytes()for n in files}
    if len(files)!=123:
        raise ValueError('Unexpected current183 manifest')
    changed,insertion=transform(contents[CONTROLLER].decode('utf-8-sig'),owner,unit_id,limit)
    from lupa.lua51 import LuaRuntime as Lua51
    from lupa.lua53 import LuaRuntime as Lua53
    compilers=[Lua51(),Lua53()];count=0
    for n,b in contents.items():
        if n.endswith('.lua'):
            code=changed if n==CONTROLLER else b.decode('utf-8-sig')
            for vm in compilers:vm.compile(code)
            count+=1
    if count!=101 or contents!={n:contained(source,n).read_bytes()for n in manifest_files(source)}:
        raise ValueError('Source changed or Lua count invalid')
    output.mkdir(parents=True,exist_ok=False);target=output/'Baiqi'
    for n,b in contents.items():
        p=contained(target,n);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(changed.encode('utf-8')if n==CONTROLLER else b)
    changes=[n for n in files if contained(target,n).read_bytes()!=contents[n]]
    if manifest_files(target)!=files or changes!=[CONTROLLER]:
        raise ValueError('Unexpected private package changes')
    archive=output/'Baiqi183-state-unknown.zip';assert package(target,archive)==files
    result={'source_version':183,'mode':'baiqi183-private-state-read-unknown-v1','files':123,'Lua_sources_compiled_each_VM':101,'changed_files':changes,'source_hashes':{n:hashlib.sha256(b).hexdigest()for n,b in contents.items()},'instrumented_hashes':{n:digest(target/n)for n in files},'archive_sha256':digest(archive),'helper_sha256':digest(ROOT/HELPER),'insertion_sha256':hashlib.sha256(insertion.encode()).hexdigest(),'target':{'owner':owner,'fullID':unit_id,'unitType':'UNIT_MISSIONARY'},'limit_per_mode':limit,'record_capacity':limit*3,'deferred_start':True,'installed':False,'Native':'NOT_RUN','limits':'Private copied snapshot owner/formation and local consumer qualification-result masks after actual SDK reads. Original SDK getter/qualifier namespace remains unchanged; not an observed engine getter absence. One actual mission eligibility site transformed, no original writer changed; inverse recovers ordinary Controller. No Native/pass/performance claim from compilation.'}
    (output/'diagnostic-build.json').open('x',encoding='utf-8').write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--owner',type=int,required=True);p.add_argument('--unit-id',type=int,required=True);p.add_argument('--limit',type=int,default=64);a=p.parse_args();print(json.dumps(build(a.output,a.owner,a.unit_id,a.limit),ensure_ascii=False))

if __name__=='__main__':main()
