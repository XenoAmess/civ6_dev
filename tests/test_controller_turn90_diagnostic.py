from pathlib import Path
import tempfile,unittest,zipfile
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from tools import build_controller_diagnostic as d
from tools.build_mod import manifest_files,digest
from tests.test_controller_native_path_timing import WORLD

CHILDREN=('PlayerContext','RefreshSettlement','ReadBack','ProcessCity','ProcessBuilder',
          'ProcessSettler','ArchaeologyPendingRead','ProcessNaturalistPurchase',
          'KnownExpansionSupport','SettlerGoalBridge','PathStep','RequestCivilian')


class Turn90DiagnosticTests(unittest.TestCase):
    def fixture(self,L):
        lua=L(unpack_returned_tuples=True);lua.execute(WORLD)
        lua.execute('''local function ReadBack(...)return ... end
BaiqiController={RunNow=function(...)T.calls=T.calls+1;return ReadBack(...)end}
'''+d.suffix(('ReadBack',),include_pre_observer=True,source_version=153,include_turn90=True))
        return lua

    def test_turn90_preobserver_and_exact_window_keep_original_results(self):
        for L in (L51,L53):
            lua=self.fixture(L)
            lua.execute('''local h=P6ControllerNested;assert(h.source=='baiqi153-controller-children-v5'and h.SetEnabled(true))
local function Call()local n,a,b,c=(function(...)return select('#',...),... end)(BaiqiController.RunNow(false,nil,7));assert(n==3 and a==false and b==nil and c==7)end
T.turn=87;Call();assert(#h.profile.samples==0)
T.turn=90;Call();assert(#h.profile.samples==2 and h.profile.samples[2].rootTurn==90)
T.callbacks[1](0);assert(h.anchors[90]);Call();assert(#h.profile.samples==4)
T.time=h.anchors[90]+10.1;Call();assert(#h.profile.samples==4)
T.turn=91;Call();assert(#h.profile.samples==4 and T.calls==5 and h.errors==0)
for _,r in ipairs(h.profile.samples)do assert(r.rootTurn==90 and r.rootId>=1)end
''')

    def test_restore_is_exact_once_and_cached_wrapper_still_calls_original(self):
        for L in (L51,L53):
            lua=self.fixture(L)
            lua.execute('''local h=P6ControllerNested;assert(h.SetEnabled(true));T.turn=90
BaiqiController.RunNow();local cached=BaiqiController.RunNow;local count=#h.profile.samples
local ok,same=h.Restore();assert(ok and #same==2 and same[1]and same[2]and #T.callbacks==0)
assert(BaiqiController.RunNow==h.bindings[1].original and h.retired and not h.subscribed)
cached();assert(#h.profile.samples==count and T.calls==2)
local ok2,same2=h.Restore();assert(ok2 and same2==same)
''')

    def test_false_default_is_byte_identical_for_all_held_variants(self):
        for version in range(140,154):
            self.assertEqual(d.suffix(source_version=version),d.suffix(source_version=version,include_turn90=False))
        for native,detour in ((False,False),(True,False),(False,True),(True,True)):
            args=dict(source_version=153,include_pre_observer=True,native_path_timing=native,detour_native_timing=detour)
            self.assertEqual(d.suffix(**args),d.suffix(**args,include_turn90=False))

    def test_bad_types_and_unqualified_combinations_reject_before_output(self):
        for value in (None,0,1,'true'):
            with self.assertRaises(ValueError):d.suffix(source_version=153,include_pre_observer=True,include_turn90=value)
        for version,pre in ((152,True),(153,False)):
            with self.assertRaises(ValueError):d.suffix(source_version=version,include_pre_observer=pre,include_turn90=True)
        with tempfile.TemporaryDirectory(dir=d.ROOT/'.local-model')as temp:
            out=Path(temp)/'invalid'
            with self.assertRaises(ValueError):d.build(out,include_turn90=True)
            self.assertFalse(out.exists())

    def test_real_twelve_scopes_compile_recover_and_keep4096_capacity(self):
        source=d.ROOT/'mod/Baiqi';raw=(source/'Lua/BaiqiController.lua').read_bytes()
        with tempfile.TemporaryDirectory(dir=d.ROOT/'.local-model')as temp:
            out=Path(temp)/'v5';result=d.build(out,children=CHILDREN,include_pre_observer=True,native_path_timing=True,include_turn90=True)
            self.assertEqual((result['mode'],result['focus_turns'],result['binding_count'],result['sample_capacity']),('baiqi153-controller-children-v5',[88,89,90],14,4096))
            self.assertTrue(result['lua51_compiled']and result['lua53_compiled'])
            names=manifest_files(out/'Baiqi');self.assertEqual(len(names),119)
            self.assertEqual([n for n in names if digest(source/n)!=digest(out/'Baiqi'/n)],['Lua/BaiqiController.lua'])
            extra=d.suffix(CHILDREN,include_pre_observer=True,source_version=153,native_path_timing=True,include_turn90=True).encode()
            private=(out/'Baiqi/Lua/BaiqiController.lua').read_bytes();self.assertTrue(private.endswith(extra))
            self.assertEqual(d.recover_native_path_source(private[:-len(extra)]),raw)
            with zipfile.ZipFile(out/'Baiqi-controller153-coarse.zip')as z:
                self.assertEqual(len(z.namelist()),119)
                for n in names:self.assertEqual(z.read('Baiqi/'+n),(out/'Baiqi'/n).read_bytes())


if __name__=='__main__':unittest.main()
