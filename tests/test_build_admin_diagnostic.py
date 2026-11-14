from pathlib import Path
import tempfile,unittest,zipfile
from lupa.lua51 import LuaRuntime
from tools.build_admin_diagnostic import ROOT,CHILDREN,RUNNERS,build,suffix
from tools.build_mod import manifest_files,digest


class AdminDiagnosticTests(unittest.TestCase):
    def test_real_admin_only_append_inventory_and_archive(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.local-model')as temp:
            out=Path(temp)/'prepared';d=build(out);source=ROOT/'mod/Baiqi';target=out/'Baiqi';names=manifest_files(source)
            self.assertEqual(d['files'],119);self.assertEqual(d['profile_count'],1);self.assertEqual(d['sample_capacity'],4096)
            self.assertEqual([n for n in names if digest(source/n)!=digest(target/n)],['Lua/BaiqiAdmin.lua'])
            self.assertEqual((target/'Lua/BaiqiAdmin.lua').read_bytes(),(source/'Lua/BaiqiAdmin.lua').read_bytes()+suffix(source_version=142).encode('utf-8'))
            with zipfile.ZipFile(out/'Baiqi-admin142-children.zip')as z:
                self.assertEqual(set(z.namelist()),{'Baiqi/'+n for n in names})
                for n in names:self.assertEqual(z.read('Baiqi/'+n),(target/n).read_bytes())

    def fixture(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        code='''rawget=nil;rawset=nil;debug=nil
T={time=100,turn=87,active=true,calls=0,callbacks={}}
Automation={GetTime=function()T.time=T.time+.001;return T.time end}
Game={GetCurrentGameTurn=function()return T.turn end,GetLocalPlayer=function()return 0 end}
Players={[0]={IsTurnActive=function()return T.active end,GetCities=function()return{GetCount=function()return 10 end}end}}
Events={PlayerTurnActivated={Add=function(f)T.callbacks[1]=f end,Remove=function(f)assert(T.callbacks[1]==f);T.callbacks={}end}}
'''
        for name in CHILDREN:code+=f'local function {name}(...)T.calls=T.calls+1;return false,nil,... end\n'
        for name in RUNNERS:code+=f'{name}={{Run=function(...)T.calls=T.calls+1;return false,nil,... end}}\n'
        code+='BaiqiAdmin={Run=function(...)Research(...);return BaiqiFoodFocusRunner.Run(...)end}\n'
        lua.execute(code+suffix())
        return lua

    def test_preobserver_anchor_cutoff_and_all13_identity_restoration(self):
        lua=self.fixture();lua.execute('''
local h=P6AdminNested;assert(#h.bindings==13 and h.source=='baiqi141-admin-children-v1'and h.SetEnabled(true))
local cached=BaiqiAdmin.Run
local function check(...)assert(select('#',...)==4);local a,b,c,d=...;assert(a==false and b==nil and c==9 and d==nil)end
check(cached(9,nil));assert(#h.profile.samples==3 and next(h.anchors)==nil)
T.callbacks[1](0);local anchor=h.anchors[87];check(cached(9,nil));assert(#h.profile.samples==6)
T.time=anchor+11;check(cached(9,nil));assert(#h.profile.samples==6)
local ok,same=h.Restore();assert(ok and #same==13 and h.retired and not h.subscribed)
for _,v in ipairs(same)do assert(v)end
check(cached(9,nil));assert(#h.profile.samples==6 and not h.SetEnabled(true))
local ok2,same2=h.Restore();assert(ok2 and same2==same and #T.callbacks==0)
''')

    def test_foreign_root_runner_and_replaced_container_are_not_overwritten(self):
        lua=self.fixture();lua.execute('''
local h=P6AdminNested;local foreign=function()return 19 end
BaiqiAdmin.Run=foreign;BaiqiFloodPurchase.Run=foreign;BaiqiFoodFocusRunner={Run=foreign}
local ok,same=h.Restore();assert(ok and not same[1]and not same[11]and not same[12]and same[13])
assert(BaiqiAdmin.Run==foreign and BaiqiFloodPurchase.Run==foreign and BaiqiFoodFocusRunner.Run==foreign)
''')


if __name__=='__main__':unittest.main()
