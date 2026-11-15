from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53

ROOT=Path(__file__).resolve().parents[1]
WRAP='''
do
 local w=TestAdmin;w.domains={};w.trace={}
 local function Mark(name)w.domains[name]=(w.domains[name]or 0)+1;w.trace[#w.trace+1]=name end
 local function Wrap(name,fn)return function(...)Mark(name);return fn(...)end end
 Research=Wrap('research',Research)
 Pantheon=Wrap('religion',Pantheon);Religion=Wrap('religion',Religion);Dedication=Wrap('religion',Dedication)
 Governors=Wrap('governors',Governors);GreatPeople=Wrap('great_people',GreatPeople);Government=Wrap('government',Government)
 BaiqiFloodPurchase={Run=function()Mark('flood')end}
 BaiqiFoodFocusRunner={Run=function()Mark('food')end}
 BaiqiFoodTileRescueRunner={Run=function()Mark('food')end}
end
'''


class AdminSchedulingTests(unittest.TestCase):
    def fixture(self,L):
        lua=L(unpack_returned_tuples=True);lua.execute((ROOT/'tests/lua/mock_admin.lua').read_text(encoding='utf-8'))
        lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiConfig.lua').read_text(encoding='utf-8'))
        lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiAdmin.lua').read_text(encoding='utf-8')+WRAP)
        return lua

    def test_each_callback_visits_one_domain_and_cycle_covers_all_seven(self):
        for L in (L51,L53):
            lua=self.fixture(L)
            lua.execute('''local w=TestAdmin;local expected={'research','flood','food','religion','governors','great_people','government'}
for i=1,7 do w.trace={};BaiqiAdmin.Run();assert(#w.trace>0)
 for _,name in ipairs(w.trace)do assert(name==expected[i])end
end
for _,name in ipairs(expected)do assert(w.domains[name]>0)end
assert(#w.requests==2 and w.policyCalls==1)
''')

    def test_inactive_callback_does_not_consume_work_slot(self):
        for L in (L51,L53):
            lua=self.fixture(L);lua.execute('''local w=TestAdmin;w.active=false;BaiqiAdmin.Run();assert(#w.trace==0)
w.active=true;BaiqiAdmin.Run();assert(w.trace[1]=='research'and #w.trace==1)''')

    def test_new_turn_restarts_with_current_research_context(self):
        for L in (L51,L53):
            lua=self.fixture(L);lua.execute('''local w=TestAdmin
for i=1,3 do BaiqiAdmin.Run()end;w.turn=2;w.trace={};BaiqiAdmin.Run()
assert(#w.trace==1 and w.trace[1]=='research')''')

    def test_policy_window_is_checked_when_its_domain_is_reached(self):
        for L in (L51,L53):
            lua=self.fixture(L);lua.execute('''local w=TestAdmin;BaiqiAdmin.Run();assert(w.policyCalls==0)
w.policyChanged=true;for i=2,7 do BaiqiAdmin.Run()end;assert(w.policyCalls==0)''')

    def test_unknown_research_is_not_replayed_across_cycles_or_turn(self):
        for L in (L51,L53):
            lua=self.fixture(L);lua.execute('''local w=TestAdmin;w.civic=0;w.policyChanged=true
local old=UI.RequestPlayerOperation;UI.RequestPlayerOperation=function(pid,op,params)
 old(pid,op,params);if op==PlayerOperations.RESEARCH then error('unknown after dispatch')end
end
for i=1,14 do BaiqiAdmin.Run()end;w.turn=2;for i=1,7 do BaiqiAdmin.Run()end
assert(#w.requests==1 and w.requests[1].op==PlayerOperations.RESEARCH)''')


if __name__=='__main__':unittest.main()
