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
NATIVE_PATH_HELPER='_P6ControllerNativePath'
NATIVE_PATH_LABEL='Native.GetMoveToPathEx'
NATIVE_PATH_ANCHOR=b'local function PathStep('
NATIVE_PATH_DECLARATION=b'local function _P6ControllerNativePath(fn,...) return fn(...) end\n\n'
NATIVE_PATH_ORIGINAL=b'  local path = UnitManager.GetMoveToPathEx(unit, target:GetIndex())'
NATIVE_PATH_PRIVATE=b'  local path = _P6ControllerNativePath(UnitManager.GetMoveToPathEx, unit, target:GetIndex())'
DETOUR_ANCHOR=b'local function SettlerOccupiedDetour('
DETOUR_HELPERS=(('_P6DetourPath1','Native.DetourChoicePath'),('_P6DetourPath2','Native.DetourFirstEdgePath'))
DETOUR_DECLARATION=b''.join(f'local function {name}(fn,...) return fn(...) end\n'.encode()for name,_ in DETOUR_HELPERS)+b'\n'
DETOUR_SITES=(
    (b'      local ok,edge=pcall(UnitManager.GetMoveToPathEx,unit,choice.index)',
     b'      local ok,edge=pcall(_P6DetourPath1,UnitManager.GetMoveToPathEx,unit,choice.index)'),
    (b'    local ok,edge=pcall(pathQuery,unit,index)',
     b'    local ok,edge=pcall(_P6DetourPath2,pathQuery,unit,index)'),
)
FOUND_WRITER_HELPER='_P6ControllerFoundWriter'
FOUND_WRITER_LABEL='Native.FoundRequestOperation'
FOUND_WRITER_ANCHOR=b'local function RequestCivilian('
FOUND_WRITER_DECLARATION=b'local function _P6ControllerFoundWriter(fn,...) return fn(...) end\n\n'
FOUND_WRITER_ORIGINAL=b'      local called=pcall(foundingNative.writer,fresh,action,params)'
FOUND_WRITER_PRIVATE=b'      local called=pcall(_P6ControllerFoundWriter,foundingNative.writer,fresh,action,params)'


def found_writer_source(raw:bytes) -> bytes:
    if not isinstance(raw,bytes):raise TypeError('Expected original Controller bytes')
    if FOUND_WRITER_HELPER.encode()in raw or raw.count(FOUND_WRITER_ANCHOR)!=1 or raw.count(FOUND_WRITER_ORIGINAL)!=1:
        raise ValueError('Unknown or nonunique founding writer call site')
    return raw.replace(FOUND_WRITER_ANCHOR,FOUND_WRITER_DECLARATION+FOUND_WRITER_ANCHOR,1).replace(FOUND_WRITER_ORIGINAL,FOUND_WRITER_PRIVATE,1)


def recover_found_writer_source(private:bytes) -> bytes:
    inserted=FOUND_WRITER_DECLARATION+FOUND_WRITER_ANCHOR
    if not isinstance(private,bytes)or private.count(inserted)!=1 or private.count(FOUND_WRITER_ANCHOR)!=1 or private.count(FOUND_WRITER_PRIVATE)!=1:
        raise ValueError('Unknown founding writer instrumentation')
    result=private.replace(inserted,FOUND_WRITER_ANCHOR,1).replace(FOUND_WRITER_PRIVATE,FOUND_WRITER_ORIGINAL,1)
    if FOUND_WRITER_HELPER.encode()in result or result.count(FOUND_WRITER_ORIGINAL)!=1:
        raise ValueError('Foreign founding writer helper reference')
    return result


def validate_found_option(value,include_pre_observer,source_version):
    if type(value)is not bool:raise ValueError('Expected founding writer timing boolean')
    if value and(type(source_version)is not int or source_version not in (157,158) or include_pre_observer is not True):
        raise ValueError('Founding writer timing requires source157/158 and pre-observer scope')


def instrument_detour_paths(raw:bytes) -> bytes:
    if not isinstance(raw,bytes):raise TypeError('Expected original Controller bytes')
    if any(name.encode()in raw for name,_ in DETOUR_HELPERS)or raw.count(DETOUR_ANCHOR)!=1:
        raise ValueError('Unknown detour anchor or helper collision')
    if any(raw.count(old)!=1 for old,_ in DETOUR_SITES):raise ValueError('Nonunique detour Native call site')
    result=raw.replace(DETOUR_ANCHOR,DETOUR_DECLARATION+DETOUR_ANCHOR,1)
    for old,new in DETOUR_SITES:result=result.replace(old,new,1)
    return result


def recover_detour_paths(private:bytes) -> bytes:
    inserted=DETOUR_DECLARATION+DETOUR_ANCHOR
    if not isinstance(private,bytes):raise TypeError('Expected private Controller bytes')
    if private.count(inserted)!=1 or private.count(DETOUR_ANCHOR)!=1 or any(private.count(new)!=1 for _,new in DETOUR_SITES):
        raise ValueError('Unknown detour instrumentation')
    result=private.replace(inserted,DETOUR_ANCHOR,1)
    for old,new in DETOUR_SITES:result=result.replace(new,old,1)
    # A leftover/foreign use must not silently become part of the recovered source.
    if any(name.encode()in result for name,_ in DETOUR_HELPERS):raise ValueError('Foreign detour helper reference')
    if any(result.count(old)!=1 for old,_ in DETOUR_SITES):raise ValueError('Foreign original detour site')
    return result


def validate_native_path_option(value,include_pre_observer,source_version):
    if type(value)is not bool:raise ValueError('Expected native path timing boolean')
    if value and (source_version not in (152,153,154,155,156,157,158) or include_pre_observer is not True):
        raise ValueError('Native path timing requires source152/153 and pre-observer scope')


def native_path_source(raw:bytes) -> bytes:
    """Change one private call site; the live Native function remains an argument."""
    if not isinstance(raw,bytes):raise TypeError('Expected original Controller bytes')
    if NATIVE_PATH_HELPER.encode()in raw or raw.count(NATIVE_PATH_ANCHOR)!=1 or raw.count(NATIVE_PATH_ORIGINAL)!=1:
        raise ValueError('Unknown or nonunique private Native path call site')
    return raw.replace(NATIVE_PATH_ANCHOR,NATIVE_PATH_DECLARATION+NATIVE_PATH_ANCHOR,1).replace(NATIVE_PATH_ORIGINAL,NATIVE_PATH_PRIVATE,1)


def recover_native_path_source(private:bytes) -> bytes:
    if (not isinstance(private,bytes)or private.count(NATIVE_PATH_PRIVATE)!=1
            or private.count(NATIVE_PATH_DECLARATION+NATIVE_PATH_ANCHOR)!=1):
        raise ValueError('Unknown private Native path source')
    return private.replace(NATIVE_PATH_PRIVATE,NATIVE_PATH_ORIGINAL,1).replace(NATIVE_PATH_DECLARATION+NATIVE_PATH_ANCHOR,NATIVE_PATH_ANCHOR,1)


def selected_children(children):
    reserved=set('and break do else elseif end false for function goto if in local nil not or repeat return then true until while'.split())
    if not isinstance(children,(tuple,list))or not 1<=len(children)<=12:
        raise ValueError('Expected1..12 unique lexical children')
    if any(not isinstance(name,str)or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name)or name in reserved for name in children):
        raise ValueError('Invalid lexical child')
    if len(set(children))!=len(children):raise ValueError('Duplicate lexical child')
    return tuple(children)


def validate_turn90(value,source_version,include_pre_observer):
    if type(value)is not bool:raise ValueError('Expected explicit turn90 boolean')
    if value and (source_version not in (153,154,155,156,157,158) or include_pre_observer is not True):
        raise ValueError('Turn90 diagnosis requires source153/154 and pre-observer coverage')


def suffix(children=CHILDREN,*,include_pre_observer=False,source_version=140,native_path_timing=False,detour_native_timing=False,include_turn90=False,found_native_timing=False):
    children=selected_children(children)
    if type(source_version)is not int or source_version not in (140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158):raise ValueError('Expected source140,141,142,143,144,145,146,147,148,149,150,151 or152')
    if type(include_pre_observer)is not bool:raise ValueError('Expected explicit scope boolean')
    validate_native_path_option(native_path_timing,include_pre_observer,source_version)
    validate_native_path_option(detour_native_timing,include_pre_observer,source_version)
    validate_turn90(include_turn90,source_version,include_pre_observer)
    validate_found_option(found_native_timing,include_pre_observer,source_version)
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
    if native_path_timing:
        index=len(children)+2
        text+=f'''do
 local binding={{original={NATIVE_PATH_HELPER}}}
 binding.wrapped=d.WrapChild('{NATIVE_PATH_LABEL}',binding.original)
 {NATIVE_PATH_HELPER}=binding.wrapped;d.bindings[{index}]=binding
end
'''
    if detour_native_timing:
        for offset,(name,label) in enumerate(DETOUR_HELPERS):
            index=len(children)+2+int(native_path_timing)+offset
            text+=f'''do
 local binding={{original={name}}}
 binding.wrapped=d.WrapChild('{label}',binding.original)
 {name}=binding.wrapped;d.bindings[{index}]=binding
end
'''
    if found_native_timing:
        index=len(children)+2+int(native_path_timing)+2*int(detour_native_timing)
        text+=f'''do
 local binding={{original={FOUND_WRITER_HELPER}}}
 binding.wrapped=d.WrapChild('{FOUND_WRITER_LABEL}',binding.original)
 {FOUND_WRITER_HELPER}=binding.wrapped;d.bindings[{index}]=binding
end
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
    if native_path_timing:
        index=len(children)+2
        text+=f''' same[{index}]={NATIVE_PATH_HELPER}==d.bindings[{index}].wrapped
 if same[{index}]then {NATIVE_PATH_HELPER}=d.bindings[{index}].original end
'''
    if detour_native_timing:
        for offset,(name,_) in enumerate(DETOUR_HELPERS):
            index=len(children)+2+int(native_path_timing)+offset
            text+=f''' same[{index}]={name}==d.bindings[{index}].wrapped
 if same[{index}]then {name}=d.bindings[{index}].original end
'''
    if found_native_timing:
        index=len(children)+2+int(native_path_timing)+2*int(detour_native_timing)
        text+=f''' same[{index}]={FOUND_WRITER_HELPER}==d.bindings[{index}].wrapped
 if same[{index}]then {FOUND_WRITER_HELPER}=d.bindings[{index}].original end
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
    if native_path_timing:
        text=text.replace('original source is the exact prefix.',
                          'one private Native call site recovers to the original source.',1)
        old="d.source='baiqi140-controller-children-v2'"
        if text.count(old)!=1:raise ValueError('Unknown Native path diagnostic owner')
        text=text.replace(old,"d.source='baiqi140-controller-children-v3'",1)
    if detour_native_timing:
        prior='v3'if native_path_timing else'v2'
        old=f"d.source='baiqi140-controller-children-{prior}'"
        if text.count(old)!=1:raise ValueError('Unknown detour diagnostic owner')
        text=text.replace(old,"d.source='baiqi140-controller-children-v4'",1)
        text=text.replace('original source is the exact prefix.','private Native call sites recover to original source.',1)
    if include_turn90:
        guard='if t~=88 and t~=89 then return nil end'
        prior='v4'if detour_native_timing else 'v3'if native_path_timing else 'v2'
        label=f"d.source='baiqi140-controller-children-{prior}'"
        if text.count(guard)!=1 or text.count(label)!=1:
            raise ValueError('Unknown turn90 diagnostic anchors')
        text=text.replace(guard,'if t~=88 and t~=89 and t~=90 then return nil end',1)
        text=text.replace(label,"d.source='baiqi140-controller-children-v5'",1)
    if found_native_timing:
        labels=re.findall(r"d\.source='baiqi140-controller-children-v[1-5]'",text)
        if len(labels)!=1:raise ValueError('Unknown founding writer diagnostic owner')
        text=text.replace(labels[0],"d.source='baiqi140-controller-children-v6'",1)
        # Civ6's compiler rejects the real Controller plus the diagnostic's
        # active locals in one frame even when stock Lua compiles it. Capture
        # the original lexical cells; allocate owner locals on a new frame.
        prefix,body=text.split('\ndo\n',1)
        if not prefix.startswith('\n-- PRIVATE coarse diagnosis;')or prefix.count('\n')!=1 or not body.endswith('P6ControllerNested=d\nend\n'):
            raise ValueError('Unknown founding writer scope anchors')
        text=prefix+'\n;(function()\n'+body[:-len('end\n')]+'end)()\n'
    return text.replace('baiqi140-controller-children-',f'baiqi{source_version}-controller-children-')


def build(output_dir:Path,*,children=CHILDREN,include_pre_observer=False,native_path_timing=False,detour_native_timing=False,include_turn90=False,found_native_timing=False):
    from lupa.lua51 import LuaRuntime as Lua51
    from lupa.lua53 import LuaRuntime as Lua53
    children=selected_children(children)
    if type(include_pre_observer)is not bool:raise ValueError('Expected explicit scope boolean')
    source=ROOT/'mod/Baiqi';names=manifest_files(source)
    version=ET.fromstring((source/'Baiqi.modinfo').read_bytes()).get('version')
    if version not in ('140','141','142','143','144','145','146','147','148','149','150','151','152','153','154','155','156','157','158'):raise ValueError('Expected actual source140,141,142,143,144,145,146,147,148,149,150,151 or152')
    version=int(version)
    validate_native_path_option(native_path_timing,include_pre_observer,version)
    validate_native_path_option(detour_native_timing,include_pre_observer,version)
    validate_turn90(include_turn90,version,include_pre_observer)
    validate_found_option(found_native_timing,include_pre_observer,version)
    out=output_dir.resolve()
    if not out.is_relative_to(ROOT/'.local-model')or out.exists():
        raise ValueError('New private output directory required')
    controller=source/'Lua/BaiqiController.lua';raw=controller.read_bytes()
    for name in children:
        if len(re.findall(r'\blocal\s+function\s+'+name+r'\s*\(',raw.decode('utf-8-sig')))!=1:
            raise ValueError('Unknown lexical child '+name)
    hashes={name:digest(contained(source,name))for name in names}
    appended=suffix(children,include_pre_observer=include_pre_observer,source_version=version,native_path_timing=native_path_timing,detour_native_timing=detour_native_timing,include_turn90=include_turn90,found_native_timing=found_native_timing).encode('utf-8');prepared={name:contained(source,name).read_bytes()for name in names}
    private=native_path_source(raw)if native_path_timing else raw
    if native_path_timing and recover_native_path_source(private)!=raw:
        raise ValueError('Private Native path source does not recover exactly')
    if detour_native_timing:
        private=instrument_detour_paths(private)
        recovered=recover_detour_paths(private)
        if native_path_timing:recovered=recover_native_path_source(recovered)
        if recovered!=raw:raise ValueError('Private detour source does not recover exactly')
    if found_native_timing:
        private=found_writer_source(private);recovered=recover_found_writer_source(private)
        if detour_native_timing:recovered=recover_detour_paths(recovered)
        if native_path_timing:recovered=recover_native_path_source(recovered)
        if recovered!=raw:raise ValueError('Private founding writer source does not recover exactly')
    prepared['Lua/BaiqiController.lua']=private+appended
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
    if native_path_timing:
        result.update(mode=f'baiqi{version}-controller-children-v3',native_path_timing=True,
                      native_child=NATIVE_PATH_LABEL,binding_count=len(children)+2,
                      original_controller_exact_prefix=False,release_text_recovers_exactly=True,
                      native_global_binding_modified=False,
                      limits='Diagnosis only. One reversible private PathStep call-site change and an owned lexical Native proxy. Current Native function is evaluated before original arguments, without replacing UnitManager. Restore removes timing aliases and the observer; the private passthrough call site remains until exit. Inclusive Native-proxy timing adds instrumentation overhead and is not B_plan or whole performance evidence.')
    if detour_native_timing:
        result.update(mode=f'baiqi{version}-controller-children-v4',detour_native_timing=True,
                      detour_native_children=[label for _,label in DETOUR_HELPERS],
                      binding_count=len(children)+3+int(native_path_timing),
                      original_controller_exact_prefix=False,release_text_recovers_exactly=True,
                      native_global_binding_modified=False,
                      limits='Diagnosis only. Two reversible detour pcall adapters preserve the current/cached Native function argument and its identity checks. Optional PathStep adapter remains separate. All scopes share the frozen4096 profile; no B_plan or whole performance pass.')
    if include_turn90:
        result.update(mode=f'baiqi{version}-controller-children-v5',include_turn90=True,
                      focus_turns=[88,89,90],binding_count=len(children)+1+int(native_path_timing)+2*int(detour_native_timing),
                      limits='Diagnosis only. Explicit source153 opt-in retains active88/89/90 entries before the own observer and within its ten-second window. Same4096 capacity and exact restoration; instrumentation is not B_plan or whole performance evidence.')
    if found_native_timing:
        result.update(mode=f'baiqi{version}-controller-children-v6',found_native_timing=True,
                      found_native_child=FOUND_WRITER_LABEL,binding_count=len(children)+2+int(native_path_timing)+2*int(detour_native_timing),
                      original_controller_exact_prefix=False,release_text_recovers_exactly=True,native_global_binding_modified=False,
                      limits='Diagnosis only. One reversible private founding pcall passthrough preserves the stored writer lookup, current arguments and once/error semantics. Native bindings and live permission checks remain original. All selected timers share one4096 profile; no B_plan or whole performance pass.')
    (out/'diagnostic-build.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--children',nargs='+',default=CHILDREN)
    p.add_argument('--native-path-timing',action='store_true')
    p.add_argument('--detour-native-timing',action='store_true')
    p.add_argument('--include-turn90',action='store_true')
    p.add_argument('--found-native-timing',action='store_true')
    p.add_argument('--include-pre-observer',action='store_true');args=p.parse_args()
    d=build(args.output_dir,children=args.children,include_pre_observer=args.include_pre_observer,native_path_timing=args.native_path_timing,detour_native_timing=args.detour_native_timing,include_turn90=args.include_turn90,found_native_timing=args.found_native_timing);print(json.dumps({k:d[k]for k in('mode','files','archive_sha256','installed')}))
