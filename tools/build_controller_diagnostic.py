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


def selected_children(children):
    reserved=set('and break do else elseif end false for function goto if in local nil not or repeat return then true until while'.split())
    if not isinstance(children,(tuple,list))or not 1<=len(children)<=12:
        raise ValueError('Expected1..12 unique lexical children')
    if any(not isinstance(name,str)or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name)or name in reserved for name in children):
        raise ValueError('Invalid lexical child')
    if len(set(children))!=len(children):raise ValueError('Duplicate lexical child')
    return tuple(children)


def suffix(children=CHILDREN,*,include_pre_observer=False,source_version=140):
    children=selected_children(children)
    if type(source_version)is not int or source_version not in (140,141):raise ValueError('Expected source140 or141')
    if type(include_pre_observer)is not bool:raise ValueError('Expected explicit scope boolean')
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
    scoped=len(children)>6
    if scoped:text+='local restorers={}\n'
    for index,name in enumerate(children,2):
        if scoped:
            text+=f'''do
 local original={name};local wrapped=d.WrapChild('{name}',original)
 {name}=wrapped;d.bindings[{index}]={{original=original,wrapped=wrapped}}
 restorers[{index}]=function()
  local same={name}==wrapped
  if same then {name}=original end
  return same
 end
end
'''
        else:
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
    for index,name in enumerate(children,2):
        if scoped:text+=f' same[{index}]=restorers[{index}]()\n'
        else:text+=f''' same[{index}]={name}==binding{index}.wrapped
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
    if include_pre_observer:
        marker='local d=NewNested(NewProfile,WrapChild,Automation.GetTime,function()\n'
        a=text.index(marker)+len(marker);b=text.index('\nend)\nd.source=',a)
        body=(ROOT/'tools/lua/diagnostic_preobserver_qualifier.lua').read_text(encoding='utf-8')
        text=text[:a]+body.rstrip('\n')+text[b:]
        old="d.source='baiqi140-controller-children-v1'"
        assert text.count(old)==1
        text=text.replace(old,"d.source='baiqi140-controller-children-v2'",1)
    return text.replace('baiqi140-controller-children-',f'baiqi{source_version}-controller-children-')


def build(output_dir:Path,*,children=CHILDREN,include_pre_observer=False):
    from lupa.lua51 import LuaRuntime as Lua51
    from lupa.lua53 import LuaRuntime as Lua53
    children=selected_children(children)
    if type(include_pre_observer)is not bool:raise ValueError('Expected explicit scope boolean')
    source=ROOT/'mod/Baiqi';names=manifest_files(source)
    version=ET.fromstring((source/'Baiqi.modinfo').read_bytes()).get('version')
    if version not in ('140','141'):raise ValueError('Expected actual source140 or141')
    version=int(version)
    out=output_dir.resolve()
    if not out.is_relative_to(ROOT/'.local-model')or out.exists():
        raise ValueError('New private output directory required')
    controller=source/'Lua/BaiqiController.lua';raw=controller.read_bytes()
    for name in children:
        if len(re.findall(r'\blocal\s+function\s+'+name+r'\s*\(',raw.decode('utf-8-sig')))!=1:
            raise ValueError('Unknown lexical child '+name)
    hashes={name:digest(contained(source,name))for name in names}
    appended=suffix(children,include_pre_observer=include_pre_observer,source_version=version).encode('utf-8');prepared={name:contained(source,name).read_bytes()for name in names}
    prepared['Lua/BaiqiController.lua']=raw+appended
    c51=Lua51().eval('function(s)local f,e=loadstring(s);assert(f,e)end')
    c53=Lua53().eval('function(s)local f,e=load(s);assert(f,e)end')
    for name,data in prepared.items():
        if name.endswith('.lua'):c51(data.decode('utf-8-sig'));c53(data.decode('utf-8-sig'))
    if hashes!={name:digest(contained(source,name))for name in names}:raise ValueError('Source changed')
    out.mkdir(parents=True,exist_ok=False);target=out/'Baiqi'
    for name,data in prepared.items():
        path=contained(target,name);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    archive=out/f'Baiqi-controller{version}-coarse.zip';package(target,archive)
    result=dict(mode=f'baiqi{version}-controller-children-v1',source_version=version,files=len(names),
                changed_files=['Lua/BaiqiController.lua'],source_hashes=hashes,
                instrumented_hashes={name:digest(contained(target,name))for name in names},
                helper_hashes={name:digest(ROOT/f'tools/lua/{name}.lua')for name in HELPERS},
                archive_sha256=digest(archive),children=list(children),sample_capacity=4096,
                profile_count=1,aggregate_zero=False,focus_turns=[88,89],observed_window_seconds=10,
                original_controller_exact_prefix=True,lua51_compiled=True,lua53_compiled=True,installed=False,
                limits='Coarse diagnosis only. Starts after this QA observer saw the native anchor; earlier entries intentionally unmeasured. Child instrumentation changes root cost; never a B_plan or all-script performance pass.')
    if include_pre_observer:
        result.update(mode=f'baiqi{version}-controller-children-v2',include_pre_observer_active_calls=True,
                      limits='Diagnosis only. All active88/89 entries before the own native observer plus10seconds after it are retained; classify intervals against actual observed anchors, never invent a physical event timestamp or grant performance pass.')
        result['helper_hashes']['diagnostic_preobserver_qualifier']=digest(ROOT/'tools/lua/diagnostic_preobserver_qualifier.lua')
    (out/'diagnostic-build.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--children',nargs='+',default=CHILDREN)
    p.add_argument('--include-pre-observer',action='store_true');args=p.parse_args()
    d=build(args.output_dir,children=args.children,include_pre_observer=args.include_pre_observer);print(json.dumps({k:d[k]for k in('mode','files','archive_sha256','installed')}))
