from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class DiagnosticPlanArgumentsTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().Install=self.lua.execute((ROOT/'tools/lua/diagnostic_plan_arguments.lua').read_text(encoding='utf-8'))
        self.lua.execute('''rawget=nil;rawset=nil;Calls=0;Turn=86;Clock=10;Handlers={};Removes=0
function Body(...)Calls=Calls+1;return ...end
Controller={RunNow=Body};Env={GetTurn=function()return Turn end,Now=function()return Clock end,
 Event={Add=function(f)Handlers[f]=true end,Remove=function(f)Removes=Removes+1;Handlers[f]=nil end}}
H=Install(Controller,Env,87)''')

    def test_target_only_false_and_full_argument_return_holes_are_preserved(self):
        self.lua.execute('''Controller.RunNow(false);assert(#H.rows==0 and Calls==1)
Turn=87;local function Count(...)return select('#',...),...end
local n,a,b,c,d=Count(Controller.RunNow(false,nil,9,nil))
assert(n==4 and a==false and b==nil and c==9 and d==nil)
local r=H.rows[1];assert(r.arg_count==4 and r.first_type=='boolean'and r.first_boolean==false)''')

    def test_getter_failures_do_not_block_body_or_mask_original_error(self):
        self.lua.execute('''Env.GetTurn=function()error('qa')end
assert(Controller.RunNow(7)==7 and Calls==1 and H.errorCounter==1)
H.Stop();local sentinel={};Controller.RunNow=function(...)error(sentinel,0)end
local next=Install(Controller,Env,87);local ok,err=pcall(Controller.RunNow,false)
assert(not ok and err==sentinel and next.errorCounter==1)''')

    def test_native_second_boolean_flag_uses_fresh_turn_and_local_pid(self):
        self.lua.execute('''Turn=87
for f in pairs(Handlers)do f(1,false);f(0,false)end
assert(#H.native_events==1 and H.native_events[1].pid==0 and H.native_events[1].turn==87)''')

    def test_row_and_event_caps_keep_exact_dropped_counts(self):
        self.lua.execute('''Turn=87;for i=1,100 do Controller.RunNow(false)end
for i=1,10 do for f in pairs(Handlers)do f(0,false)end end
assert(#H.rows==64 and H.droppedCounter==36 and Calls==100)
assert(#H.native_events==8 and H.nativeDropped==2)''')

    def test_cached_wrapper_is_inert_after_matching_restore(self):
        self.lua.execute('''local cached=Controller.RunNow
assert(H.Stop()and H.bindingsRestored and not H.active and not H.subscribed)
Env.GetTurn=function()error('must-not-read')end
assert(cached(false)==false and Calls==1 and H.errorCounter==0 and Controller.RunNow==Body)
assert(H.Stop()and Removes==1 and next(Handlers)==nil)''')

    def test_add_unknown_and_foreign_targets_are_not_overwritten(self):
        self.lua.execute('''H.Stop();Env.Event.Add=function(f)Handlers[f]=true;error('add-after')end
local bad=Install(Controller,Env,87)
assert(not bad.active and bad.errorCounter==1 and Controller.RunNow==Body and next(Handlers)==nil)
Env.Event.Add=function(f)Handlers[f]=true;Controller.RunNow=function()return 19 end end
local next=Install(Controller,Env,87)
assert(not next.active and next.errorCounter==1 and Controller.RunNow()==19 and not next.bindingsRestored)''')

    def test_unknown_remove_is_not_replayed_and_cached_wrapper_stays_inert(self):
        self.lua.execute('''H.Stop();Env.Event.Remove=function()Removes=Removes+1;error('remove')end
local next=Install(Controller,Env,87);local cached=Controller.RunNow
assert(not next.Stop()and not next.active and next.bindingsRestored and next.errorCounter==1)
local count=Removes;assert(not next.Stop()and Removes==count)
Turn=87;assert(cached(8)==8 and #next.rows==0)''')


if __name__=='__main__':
    unittest.main()
