"""Private source140 coarse child diagnosis; never installs or edits release."""
from __future__ import annotations
import argparse,json,re,sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
if __package__ in (None,''):sys.path.insert(0,str(ROOT))
from tools.build_mod import manifest_files,contained,digest,package

CHILDREN=('ReadBack','ProcessCity','ProcessBuilder','ProcessSettler',
          'RefreshSettlement','ArchaeologyPendingRead')
HELPERS=('diagnostic_profile','diagnostic_child_profile','diagnostic_nested_profile')


def suffix():
    modules=[(ROOT/f'tools/lua/{name}.lua').read_text(encoding='utf-8')for name in HELPERS]
    text='\n-- PRIVATE coarse diagnosis; original source is the exact prefix.\ndo\n'
    text+="assert(P6ControllerNested==nil,'Existing diagnostic owner')\n"
    for variable,module in zip(('NewProfile','WrapChild','NewNested'),modules):
        text+=f'local {variable}=(function()\n{module}\nend)()\n'
    text+='''
local anchors={}
local function Finite(v)return type(v)=='number'and v==v and v>-math.huge and v<math.huge end
local function Integer(v)return Finite(v)and v>=0 and v<=2147483647 and v==math.floor(v)end
local d=NewNested(NewProfile,WrapChild,Automation.GetTime,function()
 local t=Game.GetCurrentGameTurn();assert(Integer(t))
 if t~=88 and t~=89 then return nil end
 assert(Game.GetLocalPlayer()==0)
 local active=Players[0]:IsTurnActive();assert(type(active)=='boolean')
 if not active or anchors[t]==nil then return nil end
 local now=Automation.GetTime();assert(Finite(now)and now>=anchors[t])
 if now>=anchors[t]+10 then return nil end
 local n=Players[0]:GetCities():GetCount();assert(Integer(n))
 return{turnBefore=t,citiesBefore=n}
end)
d.source='baiqi140-controller-children-v1';d.anchors=anchors;d.bindings={}
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
local root={original=BaiqiController.RunNow}
root.wrapped=d.WrapRoot(root.original);BaiqiController.RunNow=root.wrapped;d.bindings[1]=root
'''
    for index,name in enumerate(CHILDREN,2):
        text+=f'''local binding{index}={{original={name}}}
binding{index}.wrapped=d.WrapChild('{name}',{name});{name}=binding{index}.wrapped;d.bindings[{index}]=binding{index}
'''
    text+='''local attempted,removed,same=false,false,nil
function d.Restore()
 if attempted then return removed,same end
 attempted=true;d.SetEnabled(false);d.retired=true;same={}
 same[1]=BaiqiController.RunNow==root.wrapped
 if same[1]then BaiqiController.RunNow=root.original end
'''
    for index,name in enumerate(CHILDREN,2):
        text+=f''' same[{index}]={name}==binding{index}.wrapped
 if same[{index}]then {name}=binding{index}.original end
'''
    text+=''' if added then
  local ok=pcall(remove,OnActivate)
  if ok then removed=true;d.subscribed=false else d.errors=d.errors+1 end
 end
 return removed,same
end
P6ControllerNested=d
end
'''
    return text


def build(output_dir:Path):
    from lupa.lua51 import LuaRuntime as Lua51
    from lupa.lua53 import LuaRuntime as Lua53
    source=ROOT/'mod/Baiqi';names=manifest_files(source)
    if ET.fromstring((source/'Baiqi.modinfo').read_bytes()).get('version')!='140':
        raise ValueError('Expected current source140')
    out=output_dir.resolve()
    if not out.is_relative_to(ROOT/'.local-model')or out.exists():
        raise ValueError('New private output directory required')
    controller=source/'Lua/BaiqiController.lua';raw=controller.read_bytes()
    for name in CHILDREN:
        if len(re.findall(r'\blocal\s+function\s+'+name+r'\s*\(',raw.decode('utf-8-sig')))!=1:
            raise ValueError('Unknown lexical child '+name)
    hashes={name:digest(contained(source,name))for name in names}
    appended=suffix().encode('utf-8');prepared={name:contained(source,name).read_bytes()for name in names}
    prepared['Lua/BaiqiController.lua']=raw+appended
    c51=Lua51().eval('function(s)local f,e=loadstring(s);assert(f,e)end')
    c53=Lua53().eval('function(s)local f,e=load(s);assert(f,e)end')
    for name,data in prepared.items():
        if name.endswith('.lua'):c51(data.decode('utf-8-sig'));c53(data.decode('utf-8-sig'))
    if hashes!={name:digest(contained(source,name))for name in names}:raise ValueError('Source changed')
    out.mkdir(parents=True,exist_ok=False);target=out/'Baiqi'
    for name,data in prepared.items():
        path=contained(target,name);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    archive=out/'Baiqi-controller140-coarse.zip';package(target,archive)
    result=dict(mode='baiqi140-controller-children-v1',source_version=140,files=len(names),
                changed_files=['Lua/BaiqiController.lua'],source_hashes=hashes,
                instrumented_hashes={name:digest(contained(target,name))for name in names},
                helper_hashes={name:digest(ROOT/f'tools/lua/{name}.lua')for name in HELPERS},
                archive_sha256=digest(archive),children=list(CHILDREN),sample_capacity=4096,
                profile_count=1,aggregate_zero=False,focus_turns=[88,89],observed_window_seconds=10,
                original_controller_exact_prefix=True,lua51_compiled=True,lua53_compiled=True,installed=False,
                limits='Coarse diagnosis only. Starts after this QA observer saw the native anchor; earlier entries intentionally unmeasured. Child instrumentation changes root cost; never a B_plan or all-script performance pass.')
    (out/'diagnostic-build.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True)
    d=build(p.parse_args().output_dir);print(json.dumps({k:d[k]for k in('mode','files','archive_sha256','installed')}))
