from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime
from tools.build_profiled_mod import CHILDREN, diagnostic_suffix

ROOT = Path(__file__).resolve().parents[1]


class DiagnosticBuildTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
unpack=table.unpack;table.unpack=nil;table.pack=nil;debug=nil
ticks=0;calls=0
function Pack(...) return {n=select('#',...),...} end
Automation={GetTime=function() ticks=ticks+1;return ticks/1000 end}
''')
        prefix = '\n'.join(
            f"local function {name}(...) calls=calls+1;return '{name}',... end" for name in CHILDREN)
        suffix = diagnostic_suffix(
            (ROOT / 'tools/lua/diagnostic_profile.lua').read_text(encoding='utf-8'),
            (ROOT / 'tools/lua/diagnostic_child_profile.lua').read_text(encoding='utf-8'), '0' * 64)
        exports = '\nreturn {Get=function() return {' + ','.join(f'{n}={n}' for n in CHILDREN) + '} end,ReplaceReadBack=function(fn) ReadBack=fn end}'
        self.lua.globals().Exports = self.lua.execute(prefix + suffix + exports)

    def test_outside_q9_does_not_profile_or_change_returns(self):
        self.lua.execute('''
P6PerfStageA={source='q8',enabled=true,currentEntry={id=7}}
local r=Pack(Exports.Get().ReadBack(false,nil,9,nil))
assert(r.n==5 and r[1]=='ReadBack' and r[2]==false and r[4]==9 and calls==1)
assert(P6BaiqiInternalProfile.profile.totalCalls==0 and ticks==0)
''')

    def test_all_five_lexical_functions_have_actual_root_identity(self):
        self.lua.execute('''
P6PerfStageA={source='q9',enabled=true,currentEntry={id=7,turnBefore=86,citiesBefore=10}}
for name,fn in pairs(Exports.Get()) do
 local r=Pack(fn(false,nil,9,nil));assert(r.n==5 and r[1]==name and r[2]==false and r[4]==9)
end
local p=P6BaiqiInternalProfile.profile
assert(calls==5 and p.totalCalls==5 and #p.samples==5 and p.dropped==0 and p.invalidClock==0)
for _,sample in ipairs(p.samples) do assert(sample.rootId==7 and sample.rootTurn==86 and sample.rootCities==10) end
''')

    def test_restore_returns_original_functions(self):
        self.lua.execute('''
local state=P6BaiqiInternalProfile;local same=state.Restore()
assert(#same==5 and not state.active)
for name,fn in pairs(Exports.Get()) do assert(fn==state.bindings[name].original) end
for _,ok in ipairs(same) do assert(ok) end
''')

    def test_restore_preserves_foreign_replacement(self):
        self.lua.execute('''
local foreign=function() return 'foreign' end
Exports.ReplaceReadBack(foreign)
local same=P6BaiqiInternalProfile.Restore()
assert(not same[1] and Exports.Get().ReadBack==foreign and not P6BaiqiInternalProfile.active)
for i=2,5 do assert(same[i]) end
''')
