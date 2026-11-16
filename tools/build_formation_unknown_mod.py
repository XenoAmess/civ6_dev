"""Build a reversible private, bounded unknown-formation snapshot diagnostic."""
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
ANCHOR='\n-- Provisional route facts rank alternatives; they never authorize a command.\n'
TYPES=('UNIT_BUILDER','UNIT_SETTLER','UNIT_MISSIONARY')
SNAPSHOT_SOURCE='''local function UnitSnapshot(unit, state)
  local def = GameInfo.Units[unit:GetUnitType()]
  return {id=unit:GetID(), owner=unit:GetOwner(), type=def and def.UnitType,
    paused=false,
    formationCount=unit.GetFormationUnitCount and unit:GetFormationUnitCount() or nil,
    tradeIdle=def and def.UnitType=="UNIT_TRADER" and UnitManager.GetActivityType~=nil
      and UnitManager.GetActivityType(unit)==ActivityTypes.ACTIVITY_AWAKE,
    moves=unit:GetMovesRemaining(), plot=UnitIndex(unit)}
end
'''


def transform(raw: str, owner: int, unit_id: int, unit_type: str, limit: int=64) -> tuple[str,str]:
    for value in (owner,unit_id):
        if type(value)is not int or not 0<=value<=2147483647:
            raise ValueError('Owner and full unit ID must be exact nonnegative integers')
    if type(limit)is not int or not 1<=limit<=64 or type(unit_type)is not str or unit_type not in TYPES:
        raise ValueError('Unknown target type or interception limit')
    if raw.count(ANCHOR)!=1 or raw.count('local function UnitSnapshot(unit, state)')!=1 or raw.count(SNAPSHOT_SOURCE+ANCHOR)!=1:
        raise ValueError('Unknown or duplicate UnitSnapshot binding')
    helper=(ROOT/'tools/lua/diagnostic_formation_unknown.lua').read_text(encoding='utf-8')
    insertion='\n'.join([
        '\n-- BAIQI_DIAGNOSTIC_ONLY: controlled snapshot unknown; actual getter still runs.',
        'assert(P6FormationUnknown==nil,"Existing formation diagnostic owner")','do',
        ' local original=UnitSnapshot',
        ' local New=(function()\n'+helper+'\n end)()',
        f' local api=New(original,{owner},{unit_id},"{unit_type}",{limit})',
        ' UnitSnapshot=api.Invoke',
        ' function api.Retire()',
        '  if UnitSnapshot==original and api.Snapshot().retired then return true,"already_retired" end',
        '  if UnitSnapshot~=api.Invoke then return false,"foreign_wrapper" end',
        '  UnitSnapshot=original;api.Disable();return true,"restored"',
        ' end',
        ' P6FormationUnknown=api','end',''])
    changed=raw.replace(ANCHOR,insertion+ANCHOR,1)
    if restore_release(changed,insertion)!=raw:
        raise ValueError('Formation diagnostic is not exactly reversible')
    return changed,insertion


def restore_release(text: str,insertion: str) -> str:
    if not insertion or text.count(insertion)!=1:
        raise ValueError('Unknown diagnostic insertion')
    return text.replace(insertion,'',1)


def build(output_dir: Path, owner: int, unit_id: int, unit_type: str, limit: int=64) -> dict:
    source=ROOT/'mod/Baiqi'
    version=ET.fromstring((source/'Baiqi.modinfo').read_bytes()).get('version')
    if version not in ('155','156'):
        raise ValueError('Formation diagnostic requires actual source155 or156')
    version=int(version)
    output_dir=output_dir.resolve()
    if output_dir.exists()or output_dir==source.resolve()or output_dir.is_relative_to(source.resolve())or source.resolve().is_relative_to(output_dir):
        raise ValueError('Output must be a new separate directory')
    files=manifest_files(source);contents={n:contained(source,n).read_bytes()for n in files}
    text,insertion=transform(contents[CONTROLLER].decode('utf-8'),owner,unit_id,unit_type,limit)
    from lupa.lua51 import LuaRuntime as Lua51
    from lupa.lua53 import LuaRuntime as Lua53
    c51=Lua51().eval('function(s)local f,e=loadstring(s);assert(f,e)end')
    c53=Lua53().eval('function(s)local f,e=load(s);assert(f,e)end')
    count=0
    for n,v in contents.items():
        if n.endswith('.lua'):
            code=text if n==CONTROLLER else v.decode('utf-8-sig');c51(code);c53(code);count+=1
    if contents!={n:contained(source,n).read_bytes()for n in manifest_files(source)}:
        raise ValueError('Product changed during diagnostic build')
    output_dir.mkdir(parents=True,exist_ok=False);target=output_dir/'Baiqi'
    for n,v in contents.items():
        p=contained(target,n);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(text.encode('utf-8')if n==CONTROLLER else v)
    changed=[n for n in files if contained(target,n).read_bytes()!=contents[n]]
    if manifest_files(target)!=files or changed!=[CONTROLLER]:raise ValueError('Unexpected package differences')
    archive=output_dir/f'Baiqi-formation{version}-unknown.zip';assert package(target,archive)==files
    result={'source_version':version,'mode':f'baiqi{version}-formation-snapshot-unknown-v1','files':len(files),
        'target':{'owner':owner,'unit_id':unit_id,'unit_type':unit_type},'interception_limit':limit,'record_capacity':64,
        'lua_sources_compiled_51_and_53':count,'changed_files':changed,'release_recovers_exactly':True,
        'source_hashes':{n:hashlib.sha256(v).hexdigest()for n,v in contents.items()},
        'instrumented_hashes':{n:digest(target/n)for n in files},'archive_sha256':digest(archive),
        'helper_sha256':digest(ROOT/'tools/lua/diagnostic_formation_unknown.lua'),
        'insertion_sha256':hashlib.sha256(insertion.encode()).hexdigest(),'installed':False,'Native_status':'UNVERIFIED',
        'limits':'Original UnitSnapshot executes once with original getters; only exact owner/fullID/type and original formation1 is copied with nil formation. At limit original behavior resumes; count-limited diagnostic window must be independently delimited. Not engine getter-missing evidence, no performance pass.'}
    with(output_dir/'diagnostic-build.json').open('x',encoding='utf-8')as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--owner',type=int,required=True);p.add_argument('--unit-id',type=int,required=True)
    p.add_argument('--unit-type',choices=TYPES,required=True);p.add_argument('--limit',type=int,default=64)
    a=p.parse_args();print(json.dumps(build(a.output_dir,a.owner,a.unit_id,a.unit_type,a.limit),ensure_ascii=False))


if __name__=='__main__':main()
