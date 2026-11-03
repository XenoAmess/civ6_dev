from pathlib import Path
import unittest

from lupa.lua53 import LuaRuntime
from tools.build_profiled_mod import CHILDREN, diagnostic_suffix

ROOT = Path(__file__).resolve().parents[1]
SELECTED = ('ReadBack', 'UnitSnapshot', 'PathStep', 'Safe', 'TradePath', 'ProcessBuilder', 'ProcessTrader')


class ProfileSelectionTests(unittest.TestCase):
    def suffix(self, **kwargs):
        return diagnostic_suffix(
            (ROOT / 'tools/lua/diagnostic_profile.lua').read_text(encoding='utf-8'),
            (ROOT / 'tools/lua/diagnostic_child_profile.lua').read_text(encoding='utf-8'),
            'a' * 64, **kwargs)

    def test_q11_selection_preserves_calls_root_gate_and_restore(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute("unpack=table.unpack; table.unpack=nil; table.pack=nil; debug=nil; ticks=0; calls=0; Automation={GetTime=function() ticks=ticks+1;return ticks/1000 end}")
        prefix = '\n'.join(f"local function {n}(...) calls=calls+1;return '{n}',... end" for n in SELECTED)
        exports = '\nreturn {' + ','.join(f'{n}=function(...) return {n}(...) end' for n in SELECTED) + '}'
        lua.globals().Selected = lua.execute(prefix + self.suffix(stage='q11', children=SELECTED) + exports)
        lua.execute('''
P6PerfStageA={source='q9',enabled=true,currentEntry={id=3,turnBefore=86,citiesBefore=10}}
Selected.ReadBack(false,nil,9,nil)
assert(calls==1 and ticks==0 and #P6BaiqiInternalProfile.profile.samples==0)
P6PerfStageA.source='q11'
local function verify(name,...)
 assert(select('#',...)==5)
 local a,b,c,d,e=...
 assert(a==name and b==false and c==nil and d==9 and e==nil)
end
for name,fn in pairs(Selected) do verify(name,fn(false,nil,9,nil)) end
local state=P6BaiqiInternalProfile
assert(state.source=='q11-internal' and state.profile.totalCalls==7 and #state.profile.samples==7 and calls==8)
for _,s in ipairs(state.profile.samples) do assert(s.rootId==3 and s.rootTurn==86 and s.rootCities==10) end
local same=state.Restore()
assert(#same==7 and not state.active)
for _,v in ipairs(same) do assert(v) end
for name,fn in pairs(Selected) do verify(name,fn(false,nil,9,nil)) end
assert(calls==15 and state.profile.totalCalls==7)
''')

    def test_default_matches_explicit_selection(self):
        self.assertEqual(self.suffix(), self.suffix(stage='q9', children=CHILDREN))

    def test_stage_type_and_boundary(self):
        for value in [None, True, 11, [], {}, '', 'q0', 'q01', 'q1000', 'q1\n', 'q１', "q11';error('x')"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.suffix(stage=value)
        for value in ['q1', 'q11', 'q999']:
            self.assertIn("source='" + value + "-internal'", self.suffix(stage=value))

    def test_children_container_and_count(self):
        for value in ['ReadBack', {'ReadBack'}, True, None, (), [], ['A'] * 13]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.suffix(children=value)
        self.suffix(children=['ReadBack'])
        self.suffix(children=tuple('Child' + str(i) for i in range(12)))

    def test_invalid_elements_rejected_before_hashing(self):
        for value in [None, True, 1, [], {}, ['ReadBack'], '', '1Bad', 'é', 'A.B', 'A\n']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.suffix(children=[value])

    def test_all_lua_keywords_and_duplicates(self):
        words = 'and break do else elseif end false for function goto if in local nil not or repeat return then true until while'.split()
        for name in words:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.suffix(children=[name])
        with self.assertRaises(ValueError):
            self.suffix(children=['ReadBack', 'ReadBack'])
