from pathlib import Path
import tempfile,json,unittest,zipfile
from lupa.lua51 import LuaRuntime
from tools.build_controller_diagnostic import ROOT,CHILDREN,build,suffix,selected_children
from tools.build_mod import digest,manifest_files


class ControllerDiagnosticBuildTests(unittest.TestCase):
    def test_real_source_inventory_exact_prefix_and_archive(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.local-model')as temp:
            out=Path(temp)/'prepared';result=build(out);target=out/'Baiqi';source=ROOT/'mod/Baiqi'
            names=manifest_files(source)
            self.assertEqual(result['files'],119);self.assertEqual(result['profile_count'],1)
            self.assertEqual(result['sample_capacity'],4096)
            self.assertEqual([n for n in names if digest(source/n)!=digest(target/n)],['Lua/BaiqiController.lua'])
            self.assertEqual(result['source_version'],141)
            self.assertEqual((target/'Lua/BaiqiController.lua').read_bytes(),(source/'Lua/BaiqiController.lua').read_bytes()+suffix(source_version=141).encode('utf-8'))
            with zipfile.ZipFile(out/'Baiqi-controller141-coarse.zip')as z:
                self.assertEqual(set(z.namelist()),{'Baiqi/'+n for n in names})
                for n in names:self.assertEqual(z.read('Baiqi/'+n),(target/n).read_bytes())

    def fixture(self,*,include_pre_observer=False):
        lua=LuaRuntime(unpack_returned_tuples=True)
        code='''
rawget=nil;rawset=nil;debug=nil
T={turn=88,time=100,active=true,callbacks={},calls=0}
Automation={GetTime=function()T.time=T.time+.001;return T.time end}
Game={GetCurrentGameTurn=function()return T.turn end,GetLocalPlayer=function()return 0 end}
Players={[0]={IsTurnActive=function()return T.active end,GetCities=function()return{GetCount=function()return 10 end}end}}
Events={PlayerTurnActivated={Add=function(fn)T.callbacks[#T.callbacks+1]=fn end,Remove=function(fn)for i=#T.callbacks,1,-1 do if T.callbacks[i]==fn then table.remove(T.callbacks,i)end end end}}
'''
        for name in CHILDREN:
            code+=f"local function {name}(...)T.calls=T.calls+1;assert(select('#',...)==2);return false,nil,7,nil end\n"
        code+='BaiqiController={RunNow=function(...)return ReadBack(...)end}\n'
        code+=suffix(include_pre_observer=include_pre_observer)
        code+='return function()return ReadBack end\n'
        return lua,lua.execute(code)

    def test_actual_suffix_native_anchor_forwarding_and_identity_restore(self):
        lua,get_child=self.fixture()
        lua.globals().get_child=get_child
        lua.execute('''
local h=P6ControllerNested;assert(not h.enabled and #T.callbacks==1)
assert(h.SetEnabled(true));T.callbacks[1](0)
local cached=BaiqiController.RunNow
local function check(...)assert(select('#',...)==4);local a,b,c,d=...;assert(a==false and b==nil and c==7 and d==nil)end
check(cached(false,nil));assert(#h.profile.samples==2 and h.profile.samples[2].rootId==1)
local ok,same=h.Restore();assert(ok and #same==7)
for _,v in ipairs(same)do assert(v)end
assert(h.retired and not h.subscribed and not h.enabled and #T.callbacks==0)
assert(BaiqiController.RunNow==h.bindings[1].original and get_child()==h.bindings[2].original)
assert(h.SetEnabled(true)==false);check(cached(false,nil));assert(#h.profile.samples==2)
''')

    def test_restore_preserves_foreign_root_and_removes_only_own_observer(self):
        lua,_=self.fixture()
        lua.execute('''
local h=P6ControllerNested;local foreign=function()end
BaiqiController.RunNow=foreign;T.callbacks[#T.callbacks+1]=foreign
local ok,same=h.Restore();assert(ok and same[1]==false and BaiqiController.RunNow==foreign)
assert(#T.callbacks==1 and T.callbacks[1]==foreign)
local ok2,same2=h.Restore();assert(ok2 and same2==same and #T.callbacks==1)
''')

    def test_default_and_explicit_selection_are_byte_identical(self):
        self.assertEqual(suffix(),suffix(CHILDREN))
        self.assertEqual(suffix(),suffix(list(CHILDREN)))

    def test_fine_settler_selection_compiles_actual_lexical_consumers(self):
        fine=('ProcessSettler','SettlementSites','PathStep','Safe','KnownExpansionSupport','RequestCivilian')
        with tempfile.TemporaryDirectory(dir=ROOT/'.local-model')as temp:
            out=Path(temp)/'prepared';result=build(out,children=fine)
            self.assertEqual(result['children'],list(fine))
            self.assertEqual(result['profile_count'],1)
            raw=(out/'Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
            for name in fine:self.assertIn("d.WrapChild('"+name+"',"+name+')',raw)

    def test_bad_selections_and_missing_lexical_child_are_rejected(self):
        for value in (None,(),'',('Safe','Safe'),('for',),('a.b',),('Safe',1),tuple('F'+str(i)for i in range(13))):
            with self.subTest(value=value),self.assertRaises(ValueError):selected_children(value)
        with tempfile.TemporaryDirectory(dir=ROOT/'.local-model')as temp:
            out=Path(temp)/'missing'
            with self.assertRaisesRegex(ValueError,'Unknown lexical'):build(out,children=('MissingActualFunction',))
            self.assertFalse(out.exists())

    def test_v2_records_preobserver_and_anchored_entries_without_making_anchor(self):
        lua,_=self.fixture(include_pre_observer=True)
        lua.execute('''
local h=P6ControllerNested;assert(h.source=='baiqi140-controller-children-v2')
assert(h.SetEnabled(true));BaiqiController.RunNow(false,nil)
assert(#h.profile.samples==2 and h.profile.samples[2].rootId==1 and next(h.anchors)==nil)
T.time=101;T.callbacks[1](0);local anchor=h.anchors[88]
assert(h.profile.samples[2].ended<anchor)
BaiqiController.RunNow(true,nil);assert(#h.profile.samples==4 and h.serial==2)
T.time=anchor+11;BaiqiController.RunNow(nil,nil)
assert(#h.profile.samples==4 and T.calls==3 and h.errors==0)
''')

    def test_v2_actual_build_and_default_bytes_stay_separate(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.local-model')as temp:
            out=Path(temp)/'v2';result=build(out,include_pre_observer=True)
            self.assertEqual(result['mode'],'baiqi141-controller-children-v2')
            self.assertTrue(result['include_pre_observer_active_calls'])
            self.assertIn('diagnostic_preobserver_qualifier',result['helper_hashes'])
            self.assertIn("d.source='baiqi140-controller-children-v1'",suffix())
            self.assertNotIn('diagnostic_preobserver_qualifier',build(Path(temp)/'v1')['helper_hashes'])

    def test_scope_flag_requires_actual_bool(self):
        for value in (None,0,1,'true'):
            with self.subTest(value=value),self.assertRaises(ValueError):suffix(include_pre_observer=value)

    def test_twelve_real_children_compile_under_lua51_local_limit(self):
        children=('PlayerContext','RefreshSettlement','ReadBack','ProcessCity','ProcessBuilder','ProcessSettler',
                  'KnownExpansionSupport','SettlementSites','PathStep','ProcessNaturalistPurchase','ProcessDistrictPerson','ProcessCreative')
        with tempfile.TemporaryDirectory(dir=ROOT/'.local-model')as temp:
            out=Path(temp)/'twelve';result=build(out,children=children,include_pre_observer=True)
            self.assertTrue(result['lua51_compiled']);self.assertTrue(result['lua53_compiled'])
            self.assertEqual(result['children'],list(children));self.assertEqual(result['profile_count'],1)
            self.assertTrue((out/'Baiqi/Lua/BaiqiController.lua').read_bytes().startswith((ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_bytes()))

    def test_scoped_child_restorers_preserve_foreign_identity_and_cached_forwarding(self):
        children=tuple('Child'+str(i)for i in range(12))
        lua=LuaRuntime(unpack_returned_tuples=True)
        raw='''T={time=1,calls=0,callbacks={}}
Automation={GetTime=function()T.time=T.time+.001;return T.time end}
Game={GetCurrentGameTurn=function()return 88 end,GetLocalPlayer=function()return 0 end}
Players={[0]={IsTurnActive=function()return true end,GetCities=function()return{GetCount=function()return 10 end}end}}
Events={PlayerTurnActivated={Add=function(f)T.callbacks[1]=f end,Remove=function(f)assert(T.callbacks[1]==f);T.callbacks={}end}}
'''
        for name in children:raw+=f'local function {name}(...)T.calls=T.calls+1;return false,nil,... end\n'
        raw+='BaiqiController={RunNow=function(...)return Child0(...)end}\n'
        raw+=suffix(children,include_pre_observer=True,source_version=141)
        raw+='''local h=P6ControllerNested;assert(#h.bindings==13 and h.SetEnabled(true))
local cached=BaiqiController.RunNow;local foreign=function()return 19 end;Child11=foreign
local function check(...)assert(select('#',...)==4);local a,b,c,d=...;assert(a==false and b==nil and c==9 and d==nil)end
check(cached(9,nil));local samples=#h.profile.samples;assert(samples==2)
local ok,same=h.Restore();assert(ok and #same==13 and not same[13]and Child11==foreign)
for i=1,12 do assert(same[i])end
check(cached(9,nil));assert(#h.profile.samples==samples and T.calls==2)
local ok2,same2=h.Restore();assert(ok2 and same2==same and #T.callbacks==0)
'''
        lua.execute(raw)


if __name__=='__main__':unittest.main()
