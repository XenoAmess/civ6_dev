"""Private Native-call timing preserves the actual caller and old diagnostics."""
from pathlib import Path
import hashlib,json,tempfile,unittest,zipfile
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
from tools import build_controller_diagnostic as diagnostic
from tools.build_mod import manifest_files,digest

FROZEN_DEFAULTS = '3595e2fc8e85bf56c04e50300169ba29ab3a9636dca65f7f9de9bd9d43cbc206'
TWELVE = ('PlayerContext','ReadBack','ProcessCity','ProcessBuilder','ProcessSettler',
          'RefreshSettlement','RetryCivilianOverlap','RequestCivilian','AdvanceBuilderRoute',
          'PrepareBuilderPathPacket','ValidateBuilderPathPacket','SettlementSites')
FINE = ('ProcessSettler','SettlementHeld','ExpansionStable','SettlerGoalBridge',
        'KnownExpansionSupport','SettlementSites','PathStep','Safe','GetVisibleUnits',
        'SettlerOccupiedDetour','CivilianMoveTarget','RequestCivilian')
RAW = b'''local function PathStep(unit,target)
  local path = UnitManager.GetMoveToPathEx(unit, target:GetIndex())
  return path
end
'''
WORLD = '''unpack=unpack or table.unpack
T={time=100,turn=88,active=true,callbacks={},calls=0}
Automation={GetTime=function()T.time=T.time+.001;return T.time end}
Game={GetCurrentGameTurn=function()return T.turn end,GetLocalPlayer=function()return 0 end}
Players={[0]={IsTurnActive=function()return T.active end,GetCities=function()return{GetCount=function()return 10 end}end}}
Events={PlayerTurnActivated={Add=function(fn)T.callbacks[#T.callbacks+1]=fn end,
 Remove=function(fn)for i=#T.callbacks,1,-1 do if T.callbacks[i]==fn then table.remove(T.callbacks,i)end end end}}
UnitManager=setmetatable({},{__index=function(_,key)assert(key=='GetMoveToPathEx');return T.native end,
 __newindex=function()error('Diagnostic replaced a Native API binding')end})
'''


class NativePathProxyTests(unittest.TestCase):
    runtime = Lua51

    def fixture(self, *, forward=False):
        lua=self.runtime(unpack_returned_tuples=True)
        lua.execute(WORLD)
        code=diagnostic.native_path_source(RAW).decode()
        if forward:
            code+='BaiqiController={RunNow=function(...)return _P6ControllerNativePath(UnitManager.GetMoveToPathEx,...)end}\n'
        else:
            code+='BaiqiController={RunNow=function(...)return PathStep(...)end}\n'
        code+=diagnostic.suffix(('PathStep',),include_pre_observer=True,source_version=152,native_path_timing=True)
        code+='''return {get=function()return _P6ControllerNativePath end,
set=function(fn)_P6ControllerNativePath=fn end,
call=function(...)return _P6ControllerNativePath(...)end}'''
        lua.globals().Access=lua.execute(code)
        return lua

    def test_current_binding_is_evaluated_before_get_index_once(self):
        lua=self.fixture()
        lua.execute('''local h=P6ControllerNested;assert(h.SetEnabled(true))
T.indices=0;T.first=0;T.second=0;local unit={}
local second=function(u,index)assert(u==unit and index==43);T.second=T.second+1;return 'second'end
local first=function(u,index)assert(u==unit and index==43);T.first=T.first+1;return 'first'end
T.native=first
local target={GetIndex=function()T.indices=T.indices+1;T.native=second;return 43 end}
assert(BaiqiController.RunNow(unit,target)=='first')
assert(T.first==1 and T.second==0 and T.indices==1 and UnitManager.GetMoveToPathEx==second)
assert(BaiqiController.RunNow(unit,target)=='second')
assert(T.first==1 and T.second==1 and T.indices==2 and h.serial==2)
assert(#h.profile.samples==6 and h.errors==0)
for i=1,2 do local base=(i-1)*3
 assert(h.profile.samples[base+1].name=='Native.GetMoveToPathEx')
 assert(h.profile.samples[base+2].name=='PathStep')
 assert(h.profile.samples[base+3].name=='Controller.RunNow')
 for j=1,3 do assert(h.profile.samples[base+j].rootId==i)end
end''')

    def test_arity_nil_errors_disabled_and_cached_retired_calls(self):
        lua=self.fixture(forward=True)
        lua.execute('''local h=P6ControllerNested
local function Check(...)assert(select('#',...)==4);local a,b,c,d=...;assert(a==false and b==nil and c==7 and d==nil)end
T.native=function(...)T.calls=T.calls+1;assert(select('#',...)==3);local a,b,c=...;assert(a==false and b==nil and c==17);return false,nil,7,nil end
Check(BaiqiController.RunNow(false,nil,17));assert(#h.profile.samples==0 and T.calls==1)
assert(h.SetEnabled(true));Check(BaiqiController.RunNow(false,nil,17))
assert(#h.profile.samples==2 and h.profile.samples[1].name=='Native.GetMoveToPathEx')
local failure={};T.native=function()T.calls=T.calls+1;error(failure)end
local ok,err=pcall(BaiqiController.RunNow);assert(not ok and err==failure and T.calls==3)
assert(#h.profile.samples==4 and h.profile.samples[3].failed and h.profile.samples[4].failed)
local cached=BaiqiController.RunNow;local count=#h.profile.samples
local restored,same=h.Restore();assert(restored and #same==3)
for _,v in ipairs(same)do assert(v)end
assert(h.retired and not h.enabled and not h.subscribed and #T.callbacks==0)
assert(Access.get()==h.bindings[3].original)
T.native=function(...)T.calls=T.calls+1;return false,nil,7,nil end
Check(cached(false,nil,17));Check(BaiqiController.RunNow(false,nil,17))
assert(#h.profile.samples==count and T.calls==5 and h.errors==0)
''')

    def test_foreign_native_proxy_and_observer_are_preserved_on_restore(self):
        lua=self.fixture(forward=True)
        lua.execute('''local h=P6ControllerNested;assert(h.SetEnabled(true))
local foreign=function()return 'foreign'end;local observer=function()end
Access.set(foreign);T.callbacks[#T.callbacks+1]=observer
local ok,same=h.Restore();assert(ok and #same==3 and same[1]and same[2]and not same[3])
assert(Access.get()==foreign and #T.callbacks==1 and T.callbacks[1]==observer)
local ok2,same2=h.Restore();assert(ok2 and same2==same and #T.callbacks==1)
assert(BaiqiController.RunNow()=='foreign'and #h.profile.samples==0)''')

    def test_passthrough_exists_before_owner_and_keeps_callable_semantics(self):
        lua=self.runtime(unpack_returned_tuples=True)
        lua.execute(WORLD)
        lua.execute(diagnostic.native_path_source(RAW).decode()+'''
local callable=setmetatable({},{__call=function(self,...)assert(select('#',...)==2);return false,nil,9,nil end})
local function Check(...)assert(select('#',...)==4);local a,b,c,d=...;assert(a==false and b==nil and c==9 and d==nil)end
Check(_P6ControllerNativePath(callable,false,nil))
assert(P6ControllerNested==nil)
''')

    def test_native_and_root_share_capacity_without_changing_result(self):
        lua=self.fixture(forward=True)
        lua.execute('''local h=P6ControllerNested
for i=1,h.profile.capacity-1 do h.profile.samples[i]={name='prior'}end
assert(h.SetEnabled(true))
T.native=function()T.calls=T.calls+1;return false,nil,7,nil end
local function Check(...)assert(select('#',...)==4);local a,b,c,d=...;assert(a==false and b==nil and c==7 and d==nil)end
Check(BaiqiController.RunNow())
assert(T.calls==1 and #h.profile.samples==h.profile.capacity and h.profile.totalCalls==2 and h.profile.dropped==1)
assert(h.profile.samples[h.profile.capacity].name=='Native.GetMoveToPathEx'and h.errors==1)
''')


class NativePathProxyLua53Tests(NativePathProxyTests):
    runtime = Lua53


class NativePathArtifactTests(unittest.TestCase):
    def test_default_28_frozen_suffixes_remain_byte_identical(self):
        rows=[]
        for version in range(140,153):
            for pre in(False,True):
                value=diagnostic.suffix(include_pre_observer=pre,source_version=version)
                self.assertEqual(value,diagnostic.suffix(include_pre_observer=pre,source_version=version,native_path_timing=False))
                rows.append([version,pre,list(diagnostic.CHILDREN),hashlib.sha256(value.encode()).hexdigest()])
        for pre in(False,True):
            value=diagnostic.suffix(TWELVE,include_pre_observer=pre,source_version=152)
            rows.append([152,pre,list(TWELVE),hashlib.sha256(value.encode()).hexdigest()])
        self.assertEqual(hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest(),FROZEN_DEFAULTS)

    def test_invalid_option_or_scope_fails_before_artifact_creation(self):
        for value in(None,0,1,'true'):
            with self.subTest(value=value),self.assertRaises(ValueError):
                diagnostic.suffix(source_version=152,include_pre_observer=True,native_path_timing=value)
        for version,pre in((140,True),(151,True),(152,False)):
            with self.subTest(version=version,pre=pre),self.assertRaises(ValueError):
                diagnostic.suffix(source_version=version,include_pre_observer=pre,native_path_timing=True)
        with tempfile.TemporaryDirectory(dir=diagnostic.ROOT/'.local-model')as temp:
            out=Path(temp)/'invalid'
            with self.assertRaises(ValueError):diagnostic.build(out,native_path_timing=True)
            self.assertFalse(out.exists())

    def test_recovery_and_reserved_missing_duplicate_anchors(self):
        self.assertEqual(diagnostic.recover_native_path_source(diagnostic.native_path_source(RAW)),RAW)
        for raw in(RAW.replace(diagnostic.NATIVE_PATH_ORIGINAL,b''),RAW+diagnostic.NATIVE_PATH_ORIGINAL,
                    RAW+b'\n-- _P6ControllerNativePath',RAW.replace(diagnostic.NATIVE_PATH_ANCHOR,b'local function Other(')):
            with self.subTest(raw=raw),self.assertRaises(ValueError):diagnostic.native_path_source(raw)

    def test_real_twelve_child_package_compiles_and_recovers_release(self):
        source=diagnostic.ROOT/'mod/Baiqi';original=(source/'Lua/BaiqiController.lua').read_bytes()
        with tempfile.TemporaryDirectory(dir=diagnostic.ROOT/'.local-model')as temp:
            out=Path(temp)/'v3';result=diagnostic.build(out,children=FINE,include_pre_observer=True,native_path_timing=True)
            self.assertEqual(result['mode'],'baiqi152-controller-children-v3')
            self.assertEqual(result['binding_count'],14)
            self.assertFalse(result['original_controller_exact_prefix'])
            self.assertTrue(result['release_text_recovers_exactly'])
            self.assertFalse(result['native_global_binding_modified'])
            self.assertTrue(result['lua51_compiled']and result['lua53_compiled'])
            target=out/'Baiqi';names=manifest_files(target);self.assertEqual(len(names),119)
            self.assertEqual(sum(n.endswith('.lua')for n in names),97)
            changed=[n for n in names if digest(source/n)!=digest(target/n)]
            self.assertEqual(changed,['Lua/BaiqiController.lua'])
            appended=diagnostic.suffix(FINE,include_pre_observer=True,source_version=152,native_path_timing=True).encode()
            data=(target/'Lua/BaiqiController.lua').read_bytes();self.assertTrue(data.endswith(appended))
            self.assertEqual(diagnostic.recover_native_path_source(data[:-len(appended)]),original)
            self.assertEqual((source/'Lua/BaiqiController.lua').read_bytes(),original)
            with zipfile.ZipFile(out/'Baiqi-controller152-coarse.zip')as archive:
                self.assertEqual(set(archive.namelist()),{'Baiqi/'+n for n in names})
                for n in names:self.assertEqual(archive.read('Baiqi/'+n),(target/n).read_bytes())


if __name__=='__main__':unittest.main()
