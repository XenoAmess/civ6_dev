from pathlib import Path
import tempfile,json,unittest,zipfile
from lupa.lua51 import LuaRuntime
from tools.build_controller_diagnostic import ROOT,CHILDREN,build,suffix
from tools.build_mod import digest,manifest_files


class ControllerDiagnosticBuildTests(unittest.TestCase):
    def test_real_source_inventory_exact_prefix_and_archive(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.local-model')as temp:
            out=Path(temp)/'prepared';result=build(out);target=out/'Baiqi';source=ROOT/'mod/Baiqi'
            names=manifest_files(source)
            self.assertEqual(result['files'],119);self.assertEqual(result['profile_count'],1)
            self.assertEqual(result['sample_capacity'],4096)
            self.assertEqual([n for n in names if digest(source/n)!=digest(target/n)],['Lua/BaiqiController.lua'])
            self.assertEqual((target/'Lua/BaiqiController.lua').read_bytes(),(source/'Lua/BaiqiController.lua').read_bytes()+suffix().encode('utf-8'))
            with zipfile.ZipFile(out/'Baiqi-controller140-coarse.zip')as z:
                self.assertEqual(set(z.namelist()),{'Baiqi/'+n for n in names})
                for n in names:self.assertEqual(z.read('Baiqi/'+n),(target/n).read_bytes())

    def fixture(self):
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
        code+=suffix()
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


if __name__=='__main__':unittest.main()
