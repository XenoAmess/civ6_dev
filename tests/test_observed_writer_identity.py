"""Real write-leaf wrappers must preserve same-context captured SDK identity."""
from pathlib import Path
import unittest
from unittest.mock import patch

from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from tests import test_baiqi_found_city_live_dispatch as live
from tests import test_baiqi_found_city_receipt as receipt
from tools.build_observed_mod import transform

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / 'mod/Baiqi/Lua/BaiqiController.lua'


class ObservedWriterIdentityTests(unittest.TestCase):
    def test_same_static_native_at_different_sites_keeps_identity_and_counts_once(self):
        for engine in (L51, L53):
            lua = engine(unpack_returned_tuples=True)
            for name, key in (('diagnostic_queries', 'Counter'), ('diagnostic_write_leaves', 'Leaves')):
                lua.globals()[key] = lua.execute((ROOT / f'tools/lua/{name}.lua').read_text(encoding='utf-8'))
            lua.execute('''
local bucket={};local calls=0;local fn=function(...)calls=calls+1;return ... end
local h=Leaves(Counter,function()return true end,function()return bucket end,{maxEntries=1})
local captured=h:Static('capture877',fn)
local current=h:Static('bound901',fn)
assert(captured==current,'Same Native function must have one static identity')
local a,b,c,d=current(1,nil,false,nil);assert(a==1 and b==nil and c==false and d==nil)
assert(calls==1 and h.stats.entries==1 and h.stats.dropped==0)
assert(bucket['capture877.Call']==1 and bucket['bound901.Call']==nil)
local changed=function()end;assert(h:Static('changed',changed)~=captured)
assert(h.stats.dropped==1)
''')

    def test_method_label_receiver_and_method_separation_is_unchanged(self):
        for engine in (L51, L53):
            lua = engine(unpack_returned_tuples=True)
            for name, key in (('diagnostic_queries', 'Counter'), ('diagnostic_write_leaves', 'Leaves')):
                lua.globals()[key] = lua.execute((ROOT / f'tools/lua/{name}.lua').read_text(encoding='utf-8'))
            lua.execute('''
local h=Leaves(Counter,function()return false end,function()return {}end)
local fn=function(self)return self end
local a={x=fn,y=fn};local b={x=fn}
local m=h:Method('M',a,'x')
assert(m==h:Method('M',a,'x'))
assert(m~=h:Method('N',a,'x'))
assert(m~=h:Method('M',b,'x'))
assert(m~=h:Method('M',a,'y'))
assert(m~=h:Static('M',fn)and m()==a)
''')

    def test_actual_transformed_controller_can_dispatch_all_existing_live_grant_cases(self):
        private, _ = transform(CONTROLLER.read_text(encoding='utf-8-sig'), 'Lua/BaiqiController.lua',
                               {'Lua/BaiqiController.lua': 4096})
        setup = '''
ExposedMembers=ExposedMembers or {}
Events=Events or {};Events.PlayerTurnActivated={Add=function()end,Remove=function()end}
Automation={GetTime=function()return 1 end}
'''
        original_read = Path.read_text

        def read(path, *args, **kwargs):
            return setup + private if path == CONTROLLER else original_read(path, *args, **kwargs)

        for engine in (L51, L53):
            for method in unittest.defaultTestLoader.getTestCaseNames(live.FoundCityLiveDispatchTests):
                with self.subTest(engine=engine.__module__, method=method):
                    with patch.object(Path, 'read_text', read), patch.object(receipt, 'LuaRuntime', engine):
                        case = live.FoundCityLiveDispatchTests(method)
                        result = unittest.TestResult();case.run(result)
                    self.assertEqual(result.errors + result.failures, [])

    def test_actual_transformed_controller_counts_its_found_writer_once_when_enabled(self):
        private, _ = transform(CONTROLLER.read_text(encoding='utf-8-sig'), 'Lua/BaiqiController.lua',
                               {'Lua/BaiqiController.lua': 4096})
        original_read = Path.read_text

        def read(path, *args, **kwargs):
            if path != CONTROLLER:
                return original_read(path, *args, **kwargs)
            return '''unpack=unpack or table.unpack
ExposedMembers=ExposedMembers or {};Events=Events or {}
Events.PlayerTurnActivated={Add=function()end,Remove=function()end}
Automation={GetTime=function()return 1 end}
''' + private

        for engine in (L51, L53):
            with self.subTest(engine=engine.__module__):
                with patch.object(Path, 'read_text', read), patch.object(receipt, 'LuaRuntime', engine):
                    case = receipt.FoundCityReceiptTests();case.setUp()
                    case.lua.execute("assert(P6OwnDiag:SetEnabled(true))")
                    case.issue();case.run_now(3)
                    state = case.lua.globals().P6OwnDiag.Snapshot(case.lua.globals().P6OwnDiag)
                    self.assertEqual(sum(state.buckets[1].values()), 1)
                    self.assertEqual(case.found_count(), 1)
                    self.assertEqual(state.leaves.dropped, 0)


if __name__ == '__main__':
    unittest.main()
