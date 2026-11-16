"""Controlled missing snapshot must reach actual Controller denial, then recover."""
from pathlib import Path
import json
import tempfile
import unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
from tools.build_formation_unknown_mod import transform,restore_release,build,SNAPSHOT_SOURCE,ANCHOR
from religious_intent_harness import install_religious_bridge

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
HELPER=(ROOT/'tools/lua/diagnostic_formation_unknown.lua').read_text(encoding='utf-8')


def controller(kind, *, owner=7, unit_id=None, extra=''):
    lua=Lua53(unpack_returned_tuples=True);logs=[]
    lua.globals().print=lambda *args:logs.append(' '.join(map(str,args)))
    if kind=='missionary':
        mocks=['mock_world','mock_missionary']
    else:mocks=['mock_world','mock_movement','mock_path_ranking']
    for n in mocks:lua.execute((ROOT/f'tests/lua/{n}.lua').read_text(encoding='utf-8'))
    if kind=='missionary':install_religious_bridge(lua)
    for n in('BaiqiConfig','BaiqiPolicy','BaiqiPlanner'):
        lua.execute((ROOT/f'mod/Baiqi/Lua/{n}.lua').read_text(encoding='utf-8'))
    target=unit_id if unit_id is not None else{'builder':3,'settler':2,'missionary':4}[kind]
    changed,insertion=transform(SOURCE,owner,target,'UNIT_'+kind.upper())
    if extra:changed=changed.replace(insertion,insertion+extra,1)
    lua.execute(changed);w=lua.globals().TestWorld
    if kind=='settler':w.withBuilder,w.withSettler=False,True
    elif kind=='builder':lua.execute('TestWorld.builderRecommendations={43}')
    else:w.withMissionary=True
    return lua,w,lua.globals().BaiqiController,lua.globals().P6FormationUnknown,logs


class FormationUnknownConsumerTests(unittest.TestCase):
    def test_targeted_real_controller_blocks_then_restores_all_three_types(self):
        for kind in('builder','settler','missionary'):
            with self.subTest(kind=kind):
                lua,w,c,api,logs=controller(kind)
                for _ in range(4):c.RunNow()
                self.assertGreater(api.Snapshot().masked,0)
                self.assertEqual(len(w.unitRequests),0)
                if kind=='missionary':self.assertEqual(len(w.spreadRequests),0)
                else:self.assertEqual(len(w.pathQueries),0)
                self.assertTrue(api.Retire()[0]);c.RunNow()
                requests=w.spreadRequests if kind=='missionary'else w.unitRequests
                self.assertEqual(len(requests),1,logs)
                self.assertFalse(any('|error|'in line for line in logs),logs)

    def test_other_full_id_and_foreign_owner_cannot_mask_actual_controller(self):
        for kind in('builder','settler','missionary'):
            for kw in({'owner':8},{'unit_id':2147483647}):
                with self.subTest(kind=kind,kw=kw):
                    _,w,c,api,logs=controller(kind,**kw);c.RunNow()
                    self.assertEqual(api.Snapshot().masked,0)
                    self.assertEqual(len(w.spreadRequests if kind=='missionary'else w.unitRequests),1,logs)

    def test_retirement_checks_real_local_binding_and_is_idempotent(self):
        extra='\nP6TestGetSnapshot=function()return UnitSnapshot end\nP6TestSetSnapshot=function(fn)UnitSnapshot=fn end\n'
        lua,_,_,api,_=controller('builder',extra=extra)
        lua.execute('P6TestOwned=P6TestGetSnapshot();P6TestForeign=function()return {}end;P6TestSetSnapshot(P6TestForeign)')
        self.assertEqual(api.Retire(),(False,'foreign_wrapper'))
        self.assertFalse(api.Snapshot().retired)
        self.assertTrue(lua.eval('P6TestGetSnapshot()==P6TestForeign'))
        lua.execute('P6TestSetSnapshot(P6TestOwned)')
        self.assertEqual(api.Retire(),(True,'restored'))
        self.assertEqual(api.Retire(),(True,'already_retired'))
        lua.execute('P6TestSetSnapshot(P6TestForeign)')
        self.assertEqual(api.Retire(),(False,'foreign_wrapper'))


class FormationUnknownHelperTests(unittest.TestCase):
    def test_original_exception_propagates_without_fake_snapshot_or_mask(self):
        for runtime in(Lua51,Lua53):
            lua=runtime(unpack_returned_tuples=True);lua.globals().New=lua.execute(HELPER)
            lua.execute('''
local reads=0
local api=New(function()reads=reads+1;error('original-snapshot-failure')end,7,3,'UNIT_BUILDER',64)
local ok,why=pcall(api.Invoke)
assert(not ok and tostring(why):find('original%-snapshot%-failure')and reads==1)
local s=api.Snapshot();assert(s.calls==1 and s.masked==0 and #s.rows==0)
''')

    def test_one_original_read_copy_bounds_expiry_and_no_native_dependencies(self):
        for runtime in(Lua51,Lua53):
            with self.subTest(runtime=runtime):
                lua=runtime(unpack_returned_tuples=True);lua.globals().New=lua.execute(HELPER)
                lua.execute('''
local reads=0
local original={owner=7,id=3,type='UNIT_BUILDER',formationCount=1,moves=2,plot=43}
local object={}
local fn=function(u,s)assert(u==object and s=='state');reads=reads+1;return original end
local api=New(fn,7,3,'UNIT_BUILDER',2)
local first=api.Invoke(object,'state');assert(first~=original and first.formationCount==nil)
assert(original.formationCount==1 and first.moves==2 and first.plot==43 and reads==1)
assert(api.Invoke(object,'state').formationCount==nil and reads==2)
local s=api.Snapshot();assert(s.masked==2 and #s.rows==2 and s.expired and not s.enabled and s.capacity==64)
s.rows[1].owner=99;assert(api.Snapshot().rows[1].owner==7)
assert(api.Invoke(object,'state')==original and reads==3 and api.Snapshot().masked==2)
api.Disable();assert(api.Snapshot().retired and not api.Snapshot().enabled)
assert(api.Invoke(object,'state')==original and reads==4)
''')

    def test_wrong_type_existing_escort_and_already_unknown_are_untouched(self):
        for runtime in(Lua51,Lua53):
            lua=runtime(unpack_returned_tuples=True);lua.globals().New=lua.execute(HELPER)
            lua.execute('''
for _,r in ipairs({{owner=8,id=3,type='UNIT_BUILDER',formationCount=1},
 {owner=7,id=4,type='UNIT_BUILDER',formationCount=1},
 {owner=7,id=3,type='UNIT_SETTLER',formationCount=1},
 {owner=7,id=3,type='UNIT_BUILDER',formationCount=2},
 {owner=7,id=3,type='UNIT_BUILDER'}})do
 local api=New(function()return r end,7,3,'UNIT_BUILDER',64)
 assert(api.Invoke()==r and api.Snapshot().masked==0)
end
''')


class FormationUnknownBuildTests(unittest.TestCase):
    def test_exact_inverse_and_strict_target_anchor_validation(self):
        changed,insertion=transform(SOURCE,7,3,'UNIT_BUILDER')
        self.assertEqual(restore_release(changed,insertion),SOURCE)
        for args in((True,3,'UNIT_BUILDER',64),(7,-1,'UNIT_BUILDER',64),(7,3,'UNIT_APOSTLE',64),(7,3,'UNIT_BUILDER',65),(7,3,'UNIT_BUILDER',False)):
            with self.subTest(args=args),self.assertRaises(ValueError):transform(SOURCE,*args)
        for raw in(SOURCE+ANCHOR,SOURCE.replace(SNAPSHOT_SOURCE,SNAPSHOT_SOURCE.replace('paused=false','paused=true'),1)):
            with self.assertRaises(ValueError):transform(raw,7,3,'UNIT_BUILDER')
        with self.assertRaises(ValueError):restore_release(changed+insertion,insertion)

    def test_actual_119_file_build_only_controller_diff_and_new_output_required(self):
        with tempfile.TemporaryDirectory()as tmp:
            out=Path(tmp)/'prepared';d=build(out,7,3,'UNIT_BUILDER')
            self.assertEqual((d['source_version'],d['files'],d['lua_sources_compiled_51_and_53']),(160,119,97))
            self.assertEqual(d['changed_files'],['Lua/BaiqiController.lua'])
            self.assertEqual(json.loads((out/'diagnostic-build.json').read_text(encoding='utf-8')),d)
            self.assertEqual(sum(d['source_hashes'][n]!=sha for n,sha in d['instrumented_hashes'].items()),1)
            with self.assertRaises(ValueError):build(out,7,3,'UNIT_BUILDER')


if __name__=='__main__':unittest.main()
