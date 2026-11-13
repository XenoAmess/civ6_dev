from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class WindowTimingContextTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for stem, name in [('diagnostic_profile', 'NewProfile'), ('diagnostic_owned_roots', 'NewRoots'),
                           ('diagnostic_queries', 'NewCounter'), ('diagnostic_write_leaves', 'NewLeaves'),
                           ('diagnostic_context', 'NewContext'), ('diagnostic_snapshot_dump', 'Dump')]:
            self.lua.globals()[name] = self.lua.execute((ROOT/f'tools/lua/{stem}.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
          Clock=10;Turn=85;Writes=0;Handlers={};Rows={}
          Env={SampleQuota=2,AggregateZero=true,Game={GetCurrentGameTurn=function()return Turn end},
            Automation={GetTime=function()return Clock end},ExposedMembers={},
            Events={PlayerTurnActivated={Add=function(fn)Handlers[fn]=true end,Remove=function(fn)Handlers[fn]=nil end}}}
          H=NewContext('UI/Test.lua',Env,NewProfile,NewRoots,NewCounter,NewLeaves)
          R=Env.ExposedMembers.P6BaiqiOwnRegistry;E=R.entries['UI/Test.lua']
          Write=H.Leaves:Static('Write',function(...)Writes=Writes+1;return ... end)
          F=H:Wrap('work',function(...)Clock=Clock+0.01;return Write(...)end)
          function Fire()for fn in pairs(Handlers)do fn(0)end end
          function Export()Rows={};return Dump(R,{'UI/Test.lua'},function(...)Rows[#Rows+1]={...}end)end
        ''')

    def test_paused_cached_wrapper_keeps_body_writes_and_anchors(self):
        self.lua.execute('''
          assert(E.Snapshot().timingEnabled==true and E.SetEnabled(true))
          assert(F(9)==9 and H.profile.totalCalls==1)
          assert(E.SetTimingEnabled(false));Turn=86
          local function check(...)assert(select('#',...)==4);local a,b,c,d=...;assert(a==1 and b==nil and c==false and d==nil)end
          check(F(1,nil,false,nil));Fire()
          local s=E.Snapshot();assert(s.enabled and not s.timingEnabled and s.profile.totalCalls==1)
          assert(s.buckets[85]['Write.Call']==1 and s.buckets[86]['Write.Call']==1 and #s.anchors==1)
          assert(E.SetTimingEnabled(true));F();assert(H.profile.totalCalls==2 and #H.profile.samples==2)
          assert(H.profile.dropped==0 and Writes==3 and E.Snapshot().stats.timingChanges==2)
          E.SetEnabled(false);local out=Export();assert(out.errors==0 and out.contexts==1)
          local found=false;for _,r in ipairs(Rows)do if r[1]=='TIMING_CONTROL'then
            assert(r[2]=='UI/Test.lua'and r[3]==2 and r[4]==true);found=true end end;assert(found)
        ''')

    def test_timing_control_never_enables_disabled_or_unknown_context(self):
        self.lua.execute('''
          E.SetTimingEnabled(false);F();E.SetEnabled(true);F()
          assert(Writes==2 and H.profile.totalCalls==0 and E.Snapshot().buckets[85]['Write.Call']==1)
          E.SetEnabled(false);E.SetTimingEnabled(true);F();Fire()
          assert(Writes==3 and H.profile.totalCalls==0 and #E.Snapshot().anchors==0)
          Env.UnknownQuota=true;local other=NewContext('Unknown',Env,NewProfile,NewRoots,NewCounter,NewLeaves)
          assert(not other:SetEnabled(true));assert(other:SetTimingEnabled(true))
          local fn=other:Wrap('body',function()return 4 end);assert(fn()==4 and other.profile.totalCalls==0)
          E.Retire();assert(not E.SetTimingEnabled(false)and not E.SetEnabled(true))
        ''')

    def test_transition_counter_is_bounded_and_invalid_flags_preserve_state(self):
        self.lua.execute('''
          assert(E.SetTimingEnabled(true)and E.Snapshot().stats.timingChanges==0)
          for i=1,128 do assert(E.SetTimingEnabled(i%2==0))end
          assert(E.Snapshot().timingEnabled==true and E.Snapshot().stats.timingChanges==128)
          assert(not E.SetTimingEnabled(false)and E.Snapshot().timingEnabled==true)
          assert(not pcall(E.SetTimingEnabled,1)and E.Snapshot().stats.timingChanges==128)
        ''')

    def test_reset_does_not_silently_restore_paused_timing(self):
        self.lua.execute('''
          E.SetEnabled(true);E.SetTimingEnabled(false);F();E.SetEnabled(false);E.Reset()
          assert(E.Snapshot().stats.timingChanges==0 and E.Snapshot().timingEnabled==false)
          E.SetEnabled(true);F();assert(H.profile.totalCalls==0)
          E.SetEnabled(false);local out=Export();assert(out.errors==0)
          local found=false;for _,r in ipairs(Rows)do if r[1]=='TIMING_CONTROL'then
            assert(r[3]==0 and r[4]==false);found=true end end;assert(found)
        ''')

    def test_paused_throw_is_original_error_without_losing_write_accounting(self):
        self.lua.execute('''
          E.SetEnabled(true);E.SetTimingEnabled(false)
          local bad=H:Wrap('throw',function()Write();error('original-body-error')end)
          local ok,err=pcall(bad);assert(not ok and string.find(err,'original%-body%-error'))
          assert(Writes==1 and E.Snapshot().buckets[85]['Write.Call']==1 and H.profile.totalCalls==0)
          E.SetTimingEnabled(true);bad=H:Wrap('positive',function()Clock=Clock+1 end)
          for i=1,3 do bad()end
          assert(H.profile.capacity==2 and #H.profile.samples==2 and H.profile.dropped==1)
        ''')


if __name__ == '__main__':
    unittest.main()
