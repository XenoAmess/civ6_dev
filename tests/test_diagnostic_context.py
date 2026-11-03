from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class DiagnosticContextTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('unpack=table.unpack;table.unpack=nil;table.pack=nil')
        for stem,name in [('diagnostic_profile','NewProfile'),('diagnostic_owned_roots','NewRoots'),
                          ('diagnostic_queries','NewCounter'),('diagnostic_write_leaves','NewLeaves'),('diagnostic_context','New')]:
            self.lua.globals()[name]=self.lua.execute((ROOT/f'tools/lua/{stem}.lua').read_text(encoding='utf-8'))
        self.lua.execute('''Turn=85;Clock=10;Adds=0;Removes=0;Handlers={};Calls=0
Event={Add=function(fn) Adds=Adds+1;Handlers[fn]=true;if AddError then error('add-error') end end,
 Remove=function(fn) Removes=Removes+1;assert(Handlers[fn]);Handlers[fn]=nil end}
Env={Game={GetCurrentGameTurn=function() return Turn end},Automation={GetTime=function() if ClockError then error('clock') end;return Clock end},
 Events={PlayerTurnActivated=Event},ExposedMembers={}}
function Make(key) return New(key,Env,NewProfile,NewRoots,NewCounter,NewLeaves) end
function Fire(pid,flag) for fn in pairs(Handlers) do fn(pid,flag) end end
H=Make('UI/Test.lua');Registry=Env.ExposedMembers.P6BaiqiOwnRegistry;Entry=Registry.entries['UI/Test.lua']''')

    def test_actual_canonical_profile_leaf_and_native_turn_anchor(self):
        self.lua.execute('''assert(Adds==1 and Removes==0 and not H:Snapshot().enabled)
local write=H.Leaves:Static('Leaf',function(...) Calls=Calls+1;return ... end)
local run=H:Wrap('Run',function(...) return write(...) end)
run();Fire(0,true);assert(H.profile.totalCalls==0 and #H:Snapshot().anchors==0)
assert(Entry.SetEnabled(true));run(1,nil,false,nil);Fire(0,false)
local s=Entry.Snapshot();assert(s.profile==H.profile and s.profile.totalCalls==1 and s.buckets[85]['Leaf.Call']==1)
assert(s.anchors[1].turn==85 and s.anchors[1].pid==0 and s.anchors[1].time==10 and Adds==1 and Removes==0)
assert(Entry.ReadClock()==10)''')

    def test_reset_targets_real_objects_preserves_cached_binding(self):
        self.lua.execute('''local f=H.Leaves:Static('F',function() return 4 end);Entry.SetEnabled(true);H:Wrap('Run',f)();Fire(0)
assert(not pcall(Entry.Reset));Entry.SetEnabled(false);Entry.Reset()
local s=Entry.Snapshot();assert(s.profile==H.profile and s.profile.totalCalls==0 and #s.profile.samples==0 and #s.anchors==0)
assert(s.leaves.counters[1].totalCalls==0 and H.Leaves:Static('F',function() end)~=f)
Entry.SetEnabled(true);assert(f()==4 and Entry.Snapshot().buckets[85]['F.Call']==1)''')

    def test_retire_removes_owned_identity_once_and_preserves_foreign_entry(self):
        self.lua.execute('''local foreign={marker='foreign'};Registry.entries['UI/Test.lua']=foreign
assert(H:Retire() and H:Retire() and Removes==1 and Registry.entries['UI/Test.lua']==foreign)
assert(not H:SetEnabled(true) and Entry.Snapshot().retired)''')

    def test_foreign_registry_and_entry_not_overwritten(self):
        self.lua.execute('''local foreign={marker='other'};Env.ExposedMembers.P6BaiqiOwnRegistry=foreign
local h=Make('UI/Foreign.lua');assert(h.stats.registryErrors==1 and Adds==1 and Env.ExposedMembers.P6BaiqiOwnRegistry==foreign)
assert(h:Wrap('still-runs',function() return 7 end)()==7)
Env.ExposedMembers.P6BaiqiOwnRegistry=Registry
Registry.entries['UI/Foreign.lua']=foreign;h=Make('UI/Foreign.lua')
assert(h.stats.registryErrors==1 and Registry.entries['UI/Foreign.lua']==foreign and Adds==1)''')

    def test_owned_replacement_retires_prior_and_new_context_inherits_recording(self):
        self.lua.execute('''Registry.enabled=true
local next=Make('UI/Test.lua');assert(Removes==1 and Adds==2 and Entry.Snapshot().retired)
assert(Registry.entries['UI/Test.lua']~=Entry and next:Snapshot().enabled)
Fire(0,true);assert(#next:Snapshot().anchors==1 and #Entry.Snapshot().anchors==0)''')

    def test_anchor_errors_caps_disabled_and_metadata_add_failure(self):
        self.lua.execute('''Entry.SetEnabled(true);ClockError=true;Fire(0);ClockError=false
assert(H.stats.anchorErrors==1)
for i=1,129 do Fire(0,true) end
assert(#H:Snapshot().anchors==128 and H.stats.anchorDropped==1)
Entry.SetEnabled(false);Fire(0);assert(H.stats.anchorDropped==1 and Adds==1 and Removes==0)
AddError=true;local failed=Make('UI/AddError.lua');assert(failed.stats.anchorErrors==1)
assert(failed:Retire() and Removes==1)''')

    def test_turn_bucket_bound_and_invalid_turn_never_uses_fake_zero(self):
        self.lua.execute('''Entry.SetEnabled(true);local f=H.Leaves:Static('F',function() Calls=Calls+1 end)
for i=1,130 do Turn=i;f() end
assert(Calls==130 and H.stats.bucketDropped==2)
local count=0;for _ in pairs(Entry.Snapshot().buckets) do count=count+1 end;assert(count==128)
Turn=nil;f();Turn=0/0;f();assert(H.stats.bucketErrors==2 and Entry.Snapshot().buckets[0]==nil)''')

    def test_missing_sdk_and_registry_capacity_are_unknown_and_do_not_block_body(self):
        self.lua.execute('''local foreign={marker='baiqi67-q19',entries={},enabled=false}
for i=1,80 do foreign.entries[tostring(i)]={} end
Env.ExposedMembers.P6BaiqiOwnRegistry=foreign
local h=Make('UI/Overflow.lua');assert(h.stats.registryErrors==1 and Adds==1)
Env.ExposedMembers={};Env.Events={};h=Make('UI/Missing.lua')
assert(h.stats.anchorErrors==1 and h:Wrap('body',function() return 1 end)()==1)''')

    def test_explicit_quota_aggregation_and_reset_keep_exact_accounting(self):
        self.lua.execute('''Env.SampleQuota=2;Env.AggregateZero=true
local h=Make('UI/Bound.lua');h:SetEnabled(true)
local z=h:Wrap('zero',function() return 9 end);for i=1,1000 do assert(z()==9) end
local positive=h:Wrap('positive',function() Clock=Clock+0.01 end)
for i=1,3 do positive() end
local p=h:Snapshot().profile
assert(p.capacity==2 and p.aggregateZero and p.zeroSuccess==1000 and #p.samples==2 and p.dropped==1 and p.totalCalls==1003)
h:SetEnabled(false);h:Reset()
assert(p.zeroSuccess==0 and p.totalCalls==0 and #p.samples==0 and p.dropped==0 and p.capacity==2 and p.aggregateZero)''')

    def test_unknown_quota_cannot_enable_recording_but_original_body_runs(self):
        self.lua.execute('''Env.SampleQuota=1;Env.AggregateZero=true;Env.UnknownQuota=true
local h=Make('Unknown.lua');assert(h.stats.registryErrors==1 and not h:SetEnabled(true))
assert(h:Wrap('body',function() return 8 end)()==8 and not h:Snapshot().enabled and h.profile.totalCalls==0)''')


if __name__=='__main__':unittest.main()
