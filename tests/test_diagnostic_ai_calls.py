from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'tools/lua/diagnostic_ai_calls.lua'
FIXTURE = r'''
local F={calls=0,now=0,turn=1}
F.run=function(...) F.calls=F.calls+1;if F.body then return F.body(...) end;return ... end
F.E={Controller={RunNow=F.run},Admin={Run=F.run},
 Now=function()if F.clock then return F.clock()end;F.now=F.now+.001;return F.now end,
 Turn=function()return F.turn end}
return F
'''


class DiagnosticAICallsTests(unittest.TestCase):
    def run_case(self, code):
        from lupa.lua51 import LuaRuntime as Lua51
        from lupa.lua53 import LuaRuntime as Lua53
        for name, vm in [('51', Lua51), ('53', Lua53)]:
            with self.subTest(lua=name, case=code[:60]):
                v = vm()
                v.globals().M = v.execute(SOURCE.read_text(encoding='utf-8'))
                v.globals().F = v.execute(FIXTURE)
                v.execute(code)

    def test_nil_arity_errors_and_copies(self):
        self.run_case(r'''
local api=M(F.E,4096);local function p(...)return{n=select('#',...),...}end
local actor={};local r=p(F.E.Controller.RunNow(actor,nil,false,nil))
assert(r.n==4 and r[1]==actor and r[2]==nil and r[3]==false and r[4]==nil)
assert(p(F.E.Admin.Run()).n==0)
local err={};F.body=function()error(err)end
local ok,e=pcall(F.E.Controller.RunNow);assert(not ok and e==err and F.calls==3)
local s=api.Snapshot();assert(not s.invalid and s.active==0 and #s.rows==3)
assert(s.rows[1].return_count==4 and s.rows[2].return_count==0 and not s.rows[3].original_ok)
s.rows[1].label='CHANGED';assert(api.Snapshot().rows[1].label=='Controller')
local saved=F.E.Controller.RunNow;assert(api.Retire()and F.E.Controller.RunNow==F.run)
F.body=nil;saved(1);assert(F.calls==4 and api.Snapshot().total_calls==3)
''')

    def test_nested_capacity_preserves_all_original_calls(self):
        self.run_case(r'''
local api=M(F.E,2);local nested=false
F.body=function(...)if not nested then nested=true;F.E.Admin.Run(nil,false);nested=false end;return ... end
F.E.Controller.RunNow(nil);F.E.Controller.RunNow(false)
local s=api.Snapshot();assert(F.calls==4 and s.total_calls==4 and #s.rows==2 and s.dropped==2)
assert(not s.invalid and s.active==0 and s.rows[1].depth==1 and s.rows[2].depth==2)
assert(s.rows[1].started<s.rows[2].started and s.rows[2].finished<s.rows[1].finished)
''')

    def test_clock_failures_do_not_stop_original(self):
        cases = [
            "F.clock=function()error('clock')end",
            "F.clock=function()return 0/0 end",
            "F.clock=function()return math.huge end",
            "F.clock=function()return -1 end",
            "F.clock=function()return 1,nil end",
            "F.clock=function()return end",
            "F.clock=function()F.now=F.now-1;return 100+F.now end",
            "F.E.Turn=function()return nil end",
            "F.E.Turn=function()return 1.5 end",
            "F.E.Turn=function()F.turn=F.turn+1;return F.turn end",
            "F.clock=function()F.E.Admin.Run();return 1 end",
        ]
        for change in cases:
            self.run_case('local api=M(F.E,8);'+change+r'''
local x=F.E.Controller.RunNow(false);assert(x==false and F.calls>=1)
local s=api.Snapshot();assert(s.invalid and s.active==0 and #s.rows<=8)
F.clock=nil;F.E.Turn=function()return 1 end;F.E.Controller.RunNow()
assert(api.Snapshot().invalid)
''')

    def test_foreign_replacement_and_invalid_setup(self):
        self.run_case(r'''
local api=M(F.E,8);local foreign=function()return 'foreign'end
F.E.Controller.RunNow=foreign;assert(api.Snapshot().invalid)
assert(not api.Retire()and F.E.Controller.RunNow==foreign and F.E.Admin.Run==F.run)
''')
        for value in ['0', '4097', '1.5', '0/0', 'math.huge']:
            self.run_case('assert(not pcall(M,F.E,'+value+'));assert(F.E.Controller.RunNow==F.run and F.E.Admin.Run==F.run)')
        self.run_case("F.E.Admin.Run=nil;assert(not pcall(M,F.E,8)and F.E.Controller.RunNow==F.run)")


if __name__ == '__main__':
    unittest.main()
