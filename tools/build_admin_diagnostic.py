"""Build a private source141 Admin diagnostic; never install or edit release."""
from __future__ import annotations
import argparse,json,re,sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
if __package__ in (None,''):sys.path.insert(0,str(ROOT))
from tools.build_mod import contained,digest,manifest_files,package

CHILDREN=('Research','PowerResearchChoice','Governors','GovernorRescue','GovernorLoyaltyDemand',
          'Religion','Government','GreatPeople','Choose')
RUNNERS=('BaiqiFloodPurchase','BaiqiFoodFocusRunner','BaiqiFoodTileRescueRunner')
HELPERS=('diagnostic_profile','diagnostic_child_profile','diagnostic_named_nested_profile')


def suffix(*,source_version=141):
    if type(source_version)is not int or source_version not in (141,142):raise ValueError('Expected source141 or142')
    text='\n-- PRIVATE Admin diagnosis; original release is the exact prefix.\ndo\n'
    text+="assert(P6AdminNested==nil,'Existing Admin diagnostic owner')\n"
    for variable,stem in zip(('NewProfile','WrapChild','NewNamed'),HELPERS):
        text+=f'local {variable}=(function()\n'+(ROOT/f'tools/lua/{stem}.lua').read_text(encoding='utf-8')+'\nend)()\n'
    text+='''local anchors={}
local function Finite(v)return type(v)=='number'and v==v and v>-math.huge and v<math.huge end
local function Integer(v)return Finite(v)and v>=0 and v<=2147483647 and v==math.floor(v)end
local d=NewNamed(NewProfile,WrapChild,Automation.GetTime,function()
 local t=Game.GetCurrentGameTurn();assert(Integer(t))
 if t<87 or t>89 then return nil end
 assert(Game.GetLocalPlayer()==0)
 local active=Players[0]:IsTurnActive();assert(type(active)=='boolean')
 if not active then return nil end
 local now=Automation.GetTime();assert(Finite(now))
 local anchor=anchors[t]
 if anchor~=nil then assert(Finite(anchor)and now>=anchor);if now>=anchor+10 then return nil end end
 local count=Players[0]:GetCities():GetCount();assert(Integer(count))
 return{turnBefore=t,citiesBefore=count}
end,'Admin.Run')
d.source='baiqi141-admin-children-v1';d.anchors=anchors;d.bindings={}
local function OnActivate(pid)
 if not d.enabled or pid~=0 then return end
 local ok=pcall(function()
  assert(Game.GetLocalPlayer()==0)
  local t=Game.GetCurrentGameTurn();local now=Automation.GetTime()
  assert(Integer(t)and Finite(now))
  if t>=85 and t<=90 and anchors[t]==nil then anchors[t]=now end
 end)
 if not ok then d.errors=math.min(2147483647,d.errors+1)end
end
local event,remove
local added=pcall(function()
 event=Events.PlayerTurnActivated;remove=event.Remove
 assert(type(event.Add)=='function'and type(remove)=='function');event.Add(OnActivate)
end)
if added then d.subscribed=true else d.errors=d.errors+1 end
local restorers={}
do
 local original=BaiqiAdmin.Run;local wrapped=d.WrapRoot(original)
 BaiqiAdmin.Run=wrapped;d.bindings[1]={original=original,wrapped=wrapped}
 restorers[1]=function()
  local same=BaiqiAdmin.Run==wrapped;if same then BaiqiAdmin.Run=original end;return same
 end
end
'''
    for index,name in enumerate(CHILDREN,2):
        text+=f'''do
 local original={name};local wrapped=d.WrapChild('{name}',original)
 {name}=wrapped;d.bindings[{index}]={{original=original,wrapped=wrapped}}
 restorers[{index}]=function()
  local same={name}==wrapped;if same then {name}=original end;return same
 end
end
'''
    for index,name in enumerate(RUNNERS,len(CHILDREN)+2):
        text+=f'''do
 local object={name};assert(type(object)=='table'and type(object.Run)=='function','Missing {name}.Run')
 local original=object.Run;local wrapped=d.WrapChild('{name}.Run',original)
 object.Run=wrapped;d.bindings[{index}]={{original=original,wrapped=wrapped}}
 restorers[{index}]=function()
  local same={name}==object and object.Run==wrapped
  if same then object.Run=original end;return same
 end
end
'''
    text+='''local attempted,removed,same=false,false,nil
function d.Restore()
 if attempted then return removed,same end
 attempted=true;d.SetEnabled(false);d.retired=true;same={}
 for index,restore in ipairs(restorers)do same[index]=restore()end
 if added then
  local ok=pcall(remove,OnActivate)
  if ok then removed=true;d.subscribed=false else d.errors=math.min(2147483647,d.errors+1)end
 end
 return removed,same
end
P6AdminNested=d
end
'''
    return text.replace('baiqi141-admin-children-v1',f'baiqi{source_version}-admin-children-v1')


def build(output_dir:Path):
    from lupa.lua51 import LuaRuntime as L51
    from lupa.lua53 import LuaRuntime as L53
    source=ROOT/'mod/Baiqi';names=manifest_files(source)
    version=ET.fromstring((source/'Baiqi.modinfo').read_bytes()).get('version')
    if version not in ('141','142'):raise ValueError('Expected actual source141 or142')
    version=int(version)
    out=output_dir.resolve()
    if not out.is_relative_to(ROOT/'.local-model')or out.exists():raise ValueError('New private output required')
    contents={name:contained(source,name).read_bytes()for name in names};raw=contents['Lua/BaiqiAdmin.lua']
    for name in CHILDREN:
        if len(re.findall(r'\blocal\s+function\s+'+name+r'\s*\(',raw.decode('utf-8-sig')))!=1:raise ValueError('Unknown Admin child '+name)
    prepared=dict(contents);prepared['Lua/BaiqiAdmin.lua']=raw+suffix(source_version=version).encode('utf-8')
    c51=L51().eval('function(s)local f,e=loadstring(s);assert(f,e)end');c53=L53().eval('function(s)local f,e=load(s);assert(f,e)end')
    for name,data in prepared.items():
        if name.endswith('.lua'):c51(data.decode('utf-8-sig'));c53(data.decode('utf-8-sig'))
    if contents!={name:contained(source,name).read_bytes()for name in manifest_files(source)}:raise ValueError('Release source changed')
    out.mkdir(parents=True,exist_ok=False);target=out/'Baiqi'
    for name,data in prepared.items():
        path=contained(target,name);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    archive=out/f'Baiqi-admin{version}-children.zip';assert package(target,archive)==names
    result=dict(mode=f'baiqi{version}-admin-children-v1',source_version=version,files=len(names),
                source_hashes={name:digest(source/name)for name in names},instrumented_hashes={name:digest(target/name)for name in names},
                helper_hashes={stem:digest(ROOT/f'tools/lua/{stem}.lua')for stem in HELPERS},
                changed_files=['Lua/BaiqiAdmin.lua'],archive_sha256=digest(archive),
                children=list(CHILDREN)+[name+'.Run'for name in RUNNERS],profile_count=1,sample_capacity=4096,
                aggregate_zero=False,focus_turns=[87,88,89],include_pre_observer_active_calls=True,
                observed_window_seconds=10,original_admin_exact_prefix=True,lua51_compiled=True,lua53_compiled=True,
                installed=False,limits='Diagnosis only. All active87..89 pre-observer entries plus10seconds after observed anchors retained. Inclusive children cannot be summed. Unselected Admin body remains unattributed. Not formal B_plan or whole performance evidence.')
    (out/'diagnostic-build.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    d=build(a.output_dir);print(json.dumps({k:d[k]for k in('mode','files','archive_sha256','installed')}))
