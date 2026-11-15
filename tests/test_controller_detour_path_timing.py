from pathlib import Path
import tempfile
import unittest

from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
from tools import build_controller_diagnostic as diagnostic
from tests.test_controller_native_path_timing import WORLD, FINE

RAW = b'''local function SettlerOccupiedDetour(unit,target,player,here,path,blockedAt)
  local choice={index=43}
      local ok,edge=pcall(UnitManager.GetMoveToPathEx,unit,choice.index)
  local firstOK,firstEdge=ok,edge
  local pathQuery=UnitManager.GetMoveToPathEx
  local function NativeEdge(index)
    local ok,edge=pcall(pathQuery,unit,index)
    assert(pathQuery==UnitManager.GetMoveToPathEx)
    return ok,edge
  end
  local secondOK,secondEdge=NativeEdge(44)
  return firstOK,firstEdge,secondOK,secondEdge
end
'''


class DetourPathTests(unittest.TestCase):
    def fixture(self, engine):
        lua = engine(unpack_returned_tuples=True)
        lua.execute(WORLD)
        text = diagnostic.instrument_detour_paths(RAW).decode()
        text += 'BaiqiController={RunNow=function(...)return SettlerOccupiedDetour(...)end}\n'
        text += diagnostic.suffix(('SettlerOccupiedDetour',), include_pre_observer=True,
                                  source_version=152, detour_native_timing=True)
        text += '''return {first=function(...)return _P6DetourPath1(...)end,
second=function(...)return _P6DetourPath2(...)end,
setSecond=function(f)_P6DetourPath2=f end,
getFirst=function()return _P6DetourPath1 end,
getSecond=function()return _P6DetourPath2 end}'''
        lua.globals().Access = lua.execute(text)
        return lua

    def test_two_real_pcall_sites_keep_native_identity_results_and_separate_labels(self):
        for engine in (Lua51, Lua53):
            with self.subTest(engine=engine.__module__):
                lua = self.fixture(engine)
                lua.execute('''
local u={};local native=function(actual,index)
 assert(actual==u);T.calls=T.calls+1;return index
end;T.native=native
local h=P6ControllerNested;assert(h.source=='baiqi152-controller-children-v4'and h.SetEnabled(true))
local a,b,c,d=BaiqiController.RunNow(u)
assert(a==true and b==43 and c==true and d==44 and T.calls==2)
assert(UnitManager.GetMoveToPathEx==native and #h.profile.samples==4)
assert(h.profile.samples[1].name=='Native.DetourChoicePath')
assert(h.profile.samples[2].name=='Native.DetourFirstEdgePath')
assert(h.profile.samples[3].name=='SettlerOccupiedDetour')
assert(h.profile.samples[4].name=='Controller.RunNow')
for _,v in ipairs(h.profile.samples)do assert(v.rootId==1)end
''')

    def test_nil_arity_native_errors_and_cached_restore_preserve_behavior(self):
        for engine in (Lua51, Lua53):
            lua = self.fixture(engine)
            lua.execute('''
local function Check(...)assert(select('#',...)==4);local a,b,c,d=...;assert(a==false and b==nil and c==7 and d==nil)end
local fn=function(...)assert(select('#',...)==3);T.calls=T.calls+1;return false,nil,7,nil end
Check(Access.first(fn,false,nil,17));Check(Access.second(fn,false,nil,17))
local h=P6ControllerNested;assert(#h.profile.samples==0 and h.SetEnabled(true))
Check(Access.first(fn,false,nil,17));Check(Access.second(fn,false,nil,17))
assert(#h.profile.samples==0) -- Child timing is owned by a planning root.
local failure={};T.native=function()T.calls=T.calls+1;error(failure)end
local a,b,c,d=BaiqiController.RunNow({});assert(not a and b==failure and not c and d==failure)
local count=#h.profile.samples;local cached=BaiqiController.RunNow
local ok,same=h.Restore();assert(ok and #same==4)
for _,v in ipairs(same)do assert(v)end
assert(Access.getFirst()==h.bindings[3].original and Access.getSecond()==h.bindings[4].original)
assert(#T.callbacks==0 and h.retired and not h.subscribed)
cached({});assert(#h.profile.samples==count)
''')

    def test_foreign_helper_is_preserved_and_shared_capacity_never_blocks_native(self):
        for engine in (Lua51, Lua53):
            lua = self.fixture(engine)
            lua.execute('''
local h=P6ControllerNested
for i=1,h.profile.capacity-1 do h.profile.samples[i]={name='prior'}end
assert(h.SetEnabled(true));T.native=function(_,index)T.calls=T.calls+1;return index end
BaiqiController.RunNow({})
assert(T.calls==2 and #h.profile.samples==4096 and h.profile.totalCalls==4 and h.profile.dropped==3)
local foreign=function()return 'foreign'end;Access.setSecond(foreign)
local ok,same=h.Restore();assert(ok and same[1]and same[2]and same[3]and not same[4])
assert(Access.getSecond()==foreign and Access.second()=='foreign')
''')

    def test_byte_recovery_collision_duplicate_and_incomplete_guards(self):
        raw = (diagnostic.ROOT / 'mod/Baiqi/Lua/BaiqiController.lua').read_bytes()
        private = diagnostic.instrument_detour_paths(raw)
        self.assertEqual(diagnostic.recover_detour_paths(private), raw)
        combined = diagnostic.instrument_detour_paths(diagnostic.native_path_source(raw))
        self.assertEqual(diagnostic.recover_native_path_source(diagnostic.recover_detour_paths(combined)), raw)
        for value in (raw + diagnostic.DETOUR_ANCHOR,
                      raw + diagnostic.DETOUR_SITES[0][0],
                      raw + b'\nlocal _P6DetourPath1=foreign',
                      raw.replace(diagnostic.DETOUR_SITES[1][0], b''), private):
            with self.subTest(length=len(value)), self.assertRaises(ValueError):
                diagnostic.instrument_detour_paths(value)
        for value in (private.replace(diagnostic.DETOUR_DECLARATION, b'-- missing\n'),
                      private.replace(b'end\nlocal function _P6DetourPath2', b'end\n-- split\nlocal function _P6DetourPath2'),
                      private + diagnostic.DETOUR_ANCHOR, private + diagnostic.DETOUR_SITES[1][0]):
            with self.subTest(length=len(value)), self.assertRaises(ValueError):
                diagnostic.recover_detour_paths(value)
        for fn in (diagnostic.instrument_detour_paths, diagnostic.recover_detour_paths):
            with self.assertRaises(TypeError):fn('not bytes')

    def test_actual_combined_twelve_scopes_build_dual_lua_and_only_change_controller(self):
        with tempfile.TemporaryDirectory(dir=diagnostic.ROOT / '.local-model') as temp:
            out = Path(temp) / 'v4'
            result = diagnostic.build(out, children=FINE, include_pre_observer=True,
                                      native_path_timing=True, detour_native_timing=True)
            self.assertEqual(result['mode'], f'baiqi{result["source_version"]}-controller-children-v4')
            self.assertEqual(result['binding_count'], 16)
            self.assertEqual(result['sample_capacity'], 4096)
            self.assertEqual(result['changed_files'], ['Lua/BaiqiController.lua'])
            self.assertTrue(result['lua51_compiled'] and result['lua53_compiled'])

    def test_option_needs_explicit_bool_source152_and_preobserver(self):
        for value in (None, 0, 1, 'true'):
            with self.assertRaises(ValueError):
                diagnostic.suffix(source_version=152, include_pre_observer=True, detour_native_timing=value)
        for version, pre in ((151, True), (152, False)):
            with self.assertRaises(ValueError):
                diagnostic.suffix(source_version=version, include_pre_observer=pre, detour_native_timing=True)


if __name__ == '__main__':
    unittest.main()
