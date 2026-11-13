"""Actual transition helper on canonical Lua5.1 diagnostic contexts."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class WindowApplyTests(unittest.TestCase):
    candidate_source = None

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for stem, name in [('diagnostic_profile', 'NewProfile'), ('diagnostic_owned_roots', 'NewRoots'),
                           ('diagnostic_queries', 'NewCounter'), ('diagnostic_write_leaves', 'NewLeaves'),
                           ('diagnostic_context', 'NewContext')]:
            self.lua.globals()[name] = self.lua.execute((ROOT/f'tools/lua/{stem}.lua').read_text(encoding='utf-8'))
        source = self.candidate_source or (ROOT/'tools/lua/diagnostic_window_timing.lua').read_text(encoding='utf-8')
        self.lua.globals().Apply = self.lua.execute(source)
        self.lua.execute('''
          Clock=10;Turn=85;Rows={};H={};E={};Keys={'UI/A','UI/B'};Handlers={}
          Env={SampleQuota=2,AggregateZero=true,Game={GetCurrentGameTurn=function()return Turn end},
            Automation={GetTime=function()Clock=Clock+0.01;return Clock end},ExposedMembers={},
            Events={PlayerTurnActivated={Add=function(fn)Handlers[fn]=true end,Remove=function(fn)Handlers[fn]=nil end}}}
          for i,key in ipairs(Keys)do
            H[i]=NewContext(key,Env,NewProfile,NewRoots,NewCounter,NewLeaves)
            H[i]:SetEnabled(true)
          end
          R=Env.ExposedMembers.P6BaiqiOwnRegistry;R.enabled=true
          for i,key in ipairs(Keys)do E[i]=R.entries[key]end
          function GetTurn()return Turn end
          function Emit(...)Rows[#Rows+1]={...}end
          function Run(flag)return Apply(R,Keys,flag,85,GetTurn,Emit)end
          function Unchanged()for _,e in ipairs(E)do assert(e.Snapshot().timingEnabled==true and e.Snapshot().stats.timingChanges==0)end end
        ''')

    def test_complete_transition_preserves_recording_and_returns_exact_clock_rows(self):
        self.lua.execute('''
          local ok,n=Run(false);assert(ok==true and n==2 and #Rows==2)
          for i,r in ipairs(Rows)do assert(r[1]==Keys[i]and r[2]==85 and r[3]==false and r[5]>=r[4])
            local s=E[i].Snapshot();assert(s.enabled and s.subscribed and not s.retired and not s.timingEnabled and s.stats.timingChanges==1)
          end
          ok,n=Run(true);assert(ok==true and n==2 and #Rows==4)
          for _,e in ipairs(E)do assert(e.Snapshot().stats.timingChanges==2 and e.Snapshot().timingEnabled)end
        ''')

    def test_non_dense_extra_unknown_or_duplicate_keys_fail_before_any_change(self):
        for code in ("Keys.extra='ignored'", "Keys={[1]='UI/A',[3]='UI/B'}", "Keys={'UI/A','UI/A'}",
                     "Keys={'UI/A','missing'}", "R.entries.extra={}", "Keys={}"):
            with self.subTest(code=code):
                self.setUp(); self.lua.execute(code+";assert(Run(false)==nil);Unchanged();assert(#Rows==0)")

    def test_unknown_second_snapshot_and_wrong_turn_prevalidate_every_context(self):
        for code in ("E[2].Snapshot=function()error('unknown')end", "Turn=86",
                     "local old=E[2].Snapshot;E[2].Snapshot=function()R.entries.extra={};return old()end",
                     "H[2]:SetEnabled(false)"):
            with self.subTest(code=code):
                self.setUp(); self.lua.execute(code+";assert(pcall(function()assert(Run(false)==nil)end));assert(H[1]:Snapshot().stats.timingChanges==0 and #Rows==0)")

    def test_no_increment_or_recording_loss_after_set_is_unknown(self):
        for code in ("local old=E[1].SetTimingEnabled;E[1].SetTimingEnabled=function(v)local ok=old(v);H[1].stats.timingChanges=0;return ok end",
                     "local old=E[1].SetTimingEnabled;E[1].SetTimingEnabled=function(v)local ok=old(v);H[1]:SetEnabled(false);return ok end"):
            with self.subTest(code=code):
                self.setUp(); self.lua.execute(code+";assert(Run(false)==nil and #Rows==0 and H[2]:Snapshot().stats.timingChanges==0)")

    def test_emit_or_clock_exception_is_contained_without_rollback_or_replay(self):
        for code in ("Emit=function()error('sink')end", "E[1].ReadClock=function()error('clock')end"):
            with self.subTest(code=code):
                self.setUp(); self.lua.execute(code+";local ok,status=pcall(Run,false);assert(ok and status==nil and H[2]:Snapshot().stats.timingChanges==0)")
        self.setUp()
        self.lua.execute('''
          Emit=function()return false end;assert(Run(false)==nil)
          assert(H[1]:Snapshot().stats.timingChanges==1 and H[2]:Snapshot().stats.timingChanges==0)
        ''')

    def test_binding_change_and_last_allowed_counter_are_checked(self):
        self.lua.execute('''
          local old=E[1].SetTimingEnabled
          E[1].SetTimingEnabled=function(v)local ok=old(v);E[1].ReadClock=function()return Clock end;return ok end
          assert(Run(false)==nil and #Rows==0 and H[2]:Snapshot().stats.timingChanges==0)
        ''')
        self.setUp()
        self.lua.execute('''
          for i=1,127 do for _,h in ipairs(H)do assert(h:SetTimingEnabled(i%2==0))end end
          assert(Run(true)==true)
          for _,h in ipairs(H)do assert(h:Snapshot().stats.timingChanges==128 and h:Snapshot().timingEnabled==true)end
        ''')


if __name__ == '__main__':
    unittest.main()
