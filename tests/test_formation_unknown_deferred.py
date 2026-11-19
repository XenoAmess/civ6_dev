"""Deferred fault starts only in a qualified, explicitly armed Native window."""
from pathlib import Path
import hashlib,json,tempfile,unittest
from unittest.mock import patch
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
from tools.build_formation_unknown_mod import transform,restore_release,build,SNAPSHOT_SOURCE,ANCHOR
import test_formation_unknown_diagnostic as base

ROOT=Path(__file__).resolve().parents[1]
def helper(runtime):
    lua=runtime(unpack_returned_tuples=True)
    lua.globals().New=lua.execute((ROOT/'tools/lua/diagnostic_formation_unknown_deferred.lua').read_text(encoding='utf-8'))
    return lua

class DeferredFormationTests(unittest.TestCase):
    def test_default_output_and_original_helper_remain_byte_identical(self):
        changed,insertion=transform(SNAPSHOT_SOURCE+ANCHOR,7,3,'UNIT_BUILDER')
        self.assertEqual(hashlib.sha256(changed.encode()).hexdigest(),'e9db2457450323c574186a0ea0f1597a00a06639a774a5fa9ebaa24a7fd0791f')
        self.assertEqual(hashlib.sha256(insertion.encode()).hexdigest(),'5cb96ac22c2e92f27ca0bdebff6b12fb4b479b2a1f1c855932ee51e873b33b06')
        self.assertEqual(hashlib.sha256((ROOT/'tools/lua/diagnostic_formation_unknown.lua').read_bytes()).hexdigest(),'981ce63bc61dc1183e1500e1bb13e664d3374f21745e6590c28301f0c84abe40')

    def test_prearm_passthrough_identity_once_and_copy_on_both_lua_versions(self):
        for runtime in(Lua51,Lua53):
            helper(runtime).execute('''
for _,kind in ipairs({'UNIT_BUILDER','UNIT_SETTLER','UNIT_MISSIONARY'})do
 local n=0;local r={owner=7,id=3,type=kind,formationCount=1,moves=2,plot=43}
 local api=New(function(u,s)assert(u=='unit'and s=='state');n=n+1;return r end,7,3,kind,64)
 assert(api.Invoke('unit','state')==r and n==1 and api.Snapshot().masked==0 and not api.Snapshot().enabled)
 assert(api.Arm(8,3,kind)==false and api.Arm(7,4,kind)==false and api.Arm(7,3,'UNIT_APOSTLE')==false)
 assert(not api.Snapshot().enabled and api.Arm(7,3,kind)==true and api.Arm(7,3,kind)==false)
 local v=api.Invoke('unit','state');assert(n==2 and v~=r and v.formationCount==nil and r.formationCount==1 and v.moves==2 and v.plot==43)
 assert(api.Snapshot().armed and api.Snapshot().masked==1)
end''')

    def test_expiry_and_retirement_are_terminal_without_reset(self):
        for runtime in(Lua51,Lua53):
            helper(runtime).execute('''
for _,limit in ipairs({1,64})do
 local r={owner=7,id=3,type='UNIT_BUILDER',formationCount=1};local api=New(function()return r end,7,3,'UNIT_BUILDER',limit)
 assert(api.Arm(7,3,'UNIT_BUILDER'));for i=1,limit do assert(api.Invoke().formationCount==nil)end
 local s=api.Snapshot();assert(s.expired and not s.enabled and s.masked==limit and #s.rows==limit and s.capacity==64)
 assert(api.Invoke()==r and api.Arm(7,3,'UNIT_BUILDER')==false and api.Snapshot().masked==limit)
 s.rows[1].owner=99;assert(api.Snapshot().rows[1].owner==7)
end
local api=New(function()return{}end,7,3,'UNIT_BUILDER',64);api.Disable();assert(api.Snapshot().retired and not api.Snapshot().armed and api.Arm(7,3,'UNIT_BUILDER')==false)
''')

    def test_original_exception_never_becomes_a_fake_snapshot(self):
        for runtime in(Lua51,Lua53):
            helper(runtime).execute("local n=0;local a=New(function()n=n+1;error('original-failure')end,7,3,'UNIT_BUILDER',64);assert(a.Arm(7,3,'UNIT_BUILDER'));local ok=pcall(a.Invoke);assert(not ok and n==1 and a.Snapshot().masked==0)")

    def test_real_consumers_mask_only_after_arm_and_restore_all_three_types(self):
        for kind in('builder','settler','missionary'):
            with self.subTest(kind=kind),patch.object(base,'transform',lambda *a,**k:transform(*a,**k,defer_start=True)):
                _,w,c,api,logs=base.controller(kind);c.RunNow()
                self.assertEqual(api.Snapshot().masked,0)
                self.assertEqual(len(w.spreadRequests if kind=='missionary'else w.unitRequests),1,logs)
                _,w,c,api,logs=base.controller(kind);s=api.Snapshot();self.assertTrue(api.Arm(s.owner,s.id,s.unitType)[0])
                for _ in range(4):c.RunNow()
                self.assertGreater(api.Snapshot().masked,0)
                self.assertEqual(len(w.spreadRequests if kind=='missionary'else w.unitRequests),0,logs)
                self.assertTrue(api.Retire()[0]);c.RunNow()
                self.assertEqual(len(w.spreadRequests if kind=='missionary'else w.unitRequests),1,logs)

    def test_foreign_binding_cannot_arm_or_be_overwritten(self):
        extra='\nP6TestGetSnapshot=function()return UnitSnapshot end\nP6TestSetSnapshot=function(fn)UnitSnapshot=fn end\n'
        with patch.object(base,'transform',lambda *a,**k:transform(*a,**k,defer_start=True)):
            lua,_,_,api,_=base.controller('builder',extra=extra)
        lua.execute('P6Owned=P6TestGetSnapshot();P6Foreign=function()return{}end;P6TestSetSnapshot(P6Foreign)')
        self.assertEqual(api.Arm(7,3,'UNIT_BUILDER'),(False,'foreign_wrapper'))
        self.assertFalse(api.Snapshot().armed);self.assertEqual(api.Retire(),(False,'foreign_wrapper'))
        self.assertTrue(lua.eval('P6TestGetSnapshot()==P6Foreign'))
        lua.execute('P6TestSetSnapshot(P6Owned)');self.assertEqual(api.Arm(7,3,'UNIT_BUILDER'),(True,'armed'));self.assertTrue(api.Retire()[0])
        self.assertEqual(api.Arm(7,3,'UNIT_BUILDER'),(False,'retired'))
        lua.execute('P6TestSetSnapshot(P6Foreign)')
        self.assertEqual(api.Arm(7,3,'UNIT_BUILDER'),(False,'foreign_wrapper'))

    def test_armed_helper_preserves_nonmatching_escort_and_unknown_snapshots(self):
        for runtime in(Lua51,Lua53):
            helper(runtime).execute('''
for _,r in ipairs({{owner=8,id=3,type='UNIT_BUILDER',formationCount=1},
 {owner=7,id=4,type='UNIT_BUILDER',formationCount=1},
 {owner=7,id=3,type='UNIT_SETTLER',formationCount=1},
 {owner=7,id=3,type='UNIT_BUILDER',formationCount=2},
 {owner=7,id=3,type='UNIT_BUILDER'}})do
 local reads=0;local a=New(function()reads=reads+1;return r end,7,3,'UNIT_BUILDER',64)
 assert(a.Arm(7,3,'UNIT_BUILDER'));assert(a.Invoke()==r and reads==1 and a.Snapshot().masked==0)
end''')

    def test_deferred_build_is_explicit_reversible_and_only_controller_changes(self):
        changed,insertion=transform(base.SOURCE,7,3,'UNIT_BUILDER',defer_start=True)
        self.assertEqual(restore_release(changed,insertion),base.SOURCE)
        for bad in(1,None,'true'):
            with self.assertRaises(ValueError):transform(base.SOURCE,7,3,'UNIT_BUILDER',defer_start=bad)
        with tempfile.TemporaryDirectory()as tmp:
            out=Path(tmp)/'prepared';d=build(out,7,3,'UNIT_BUILDER',defer_start=True)
            self.assertTrue(d['deferred_start']);self.assertEqual(d['changed_files'],['Lua/BaiqiController.lua'])
            self.assertEqual((d['source_version'],d['files'],d['lua_sources_compiled_51_and_53']),(169,119,97))
            self.assertIn('deferred',d['mode']);self.assertEqual(json.loads((out/'diagnostic-build.json').read_text(encoding='utf-8')),d)

if __name__=='__main__':unittest.main()
