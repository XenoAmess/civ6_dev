from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class SnapshotDumpTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('unpack=table.unpack;table.unpack=nil;table.pack=nil')
        names=[('diagnostic_profile','NewProfile'),('diagnostic_owned_roots','NewRoots'),('diagnostic_queries','NewCounter'),
               ('diagnostic_write_leaves','NewLeaves'),('diagnostic_context','NewContext'),('diagnostic_snapshot_dump','Dump')]
        for stem,key in names:self.lua.globals()[key]=self.lua.execute((ROOT/f'tools/lua/{stem}.lua').read_text(encoding='utf-8'))
        self.lua.execute('''Adds=0;Removes=0;Rows={};Turn=85;Clock=120.125
local callback
Env={Game={GetCurrentGameTurn=function() return Turn end},Automation={GetTime=function() return Clock end},
 ExposedMembers={},Events={PlayerTurnActivated={Add=function(fn) Adds=Adds+1;callback=fn end,Remove=function(fn) assert(fn==callback);Removes=Removes+1 end}}}
H=NewContext('UI/Test.lua',Env,NewProfile,NewRoots,NewCounter,NewLeaves)
R=Env.ExposedMembers.P6BaiqiOwnRegistry
local leaf=H.Leaves:Static('API',function(...) return ... end)
H:SetEnabled(true);H:Wrap('Root',function() for i=1,3 do leaf(i,nil) end end)();callback(0,false);H:SetEnabled(false)
function Emit(...) Rows[#Rows+1]={n=select('#',...),...} end
function Run() return Dump(R,{'UI/Test.lua'},Emit) end''')

    def test_actual_canonical_snapshot_exports_fractional_clock_and_real_counter(self):
        self.lua.execute('''local before=H:Snapshot();local status=Run();local after=H:Snapshot()
assert(status.contexts==1 and status.samples==1 and status.anchors==1 and status.writes==1 and status.errors==0)
assert(Rows[1][1]=='META' and Rows[1][16]==3 and Rows[1][17]==true and Rows[1][18]==false)
assert(Rows[2][1]=='TIMING_CONTROL' and Rows[2][3]==0 and Rows[2][4]==true)
assert(Rows[3][1]=='SAMPLE' and Rows[3][5]==120.125 and Rows[3][8]==false)
assert(Rows[4][1]=='ANCHOR' and Rows[4][5]==85 and Rows[5][1]=='WRITE' and Rows[5][5]==3)
assert(before.profile.samples==after.profile.samples and before.buckets==after.buckets and not after.enabled and Adds==1 and Removes==0)''')

    def test_enabled_registry_or_snapshot_rejected_without_control_mutation(self):
        self.lua.execute('''R.enabled=true;assert(Run().errors==1 and #Rows==0 and R.enabled==true)
R.enabled=false;H:SetEnabled(true);assert(Run().errors==1 and #Rows==0 and H:Snapshot().enabled)
H:SetEnabled(false)''')

    def test_missing_counter_or_metadata_does_not_default_to_zero(self):
        self.lua.execute('''local s=H:Snapshot();local old=s.leaves.counters[1].callbackErrors
s.leaves.counters[1].callbackErrors=nil
assert(Run().errors==1 and #Rows==0)
s.leaves.counters[1].callbackErrors=old;s.profile.invalidClock=nil
assert(Run().errors==1 and #Rows==0)''')

    def test_bad_rows_bounds_and_sparse_keys_flag_incomplete_export(self):
        self.lua.execute('''local s=H:Snapshot();s.profile.samples[1].started=0/0
assert(Run().errors==1)
Rows={};assert(Dump(R,{[1]='UI/Test.lua',[3]='UI/Missing.lua'},Emit).errors==1 and #Rows==0)
s.profile.samples={};for i=1,30001 do s.profile.samples[i]={} end
assert(Run().errors==1)''')

    def test_first_emit_error_stops_without_replay_or_later_context(self):
        self.lua.execute('''local calls=0
local s=Dump(R,{'UI/Test.lua','UI/Missing.lua'},function() calls=calls+1;error('emit') end)
assert(calls==1 and s.errors==1 and s.contexts==0 and s.samples==0)''')

    def test_snapshot_throw_continues_other_context_and_duplicates_rejected(self):
        self.lua.execute('''R.entries['UI/Broken.lua']={marker='baiqi67-q19',Snapshot=function() error('broken') end}
local s=Dump(R,{'UI/Broken.lua','UI/Test.lua','UI/Test.lua'},Emit)
assert(s.errors==2 and s.contexts==1 and s.samples==1 and #Rows==5)''')

    def test_turn_and_api_order_and_count_values_are_not_collapsed(self):
        self.lua.execute('''local s=H:Snapshot();s.buckets[86]={Z=7,A=2};s.buckets[2]={X=1}
local status=Run();local writes={}
for _,row in ipairs(Rows) do if row[1]=='WRITE' then writes[#writes+1]=row end end
assert(status.errors==0 and status.writes==4 and writes[1][3]==2 and writes[2][3]==85)
assert(writes[3][3]==86 and writes[3][4]=='A' and writes[3][5]==2 and writes[4][4]=='Z' and writes[4][5]==7)''')

    def test_explicit_zero_aggregate_and_quota_export_without_raw_zero_rows(self):
        self.lua.execute('''Env.SampleQuota=1;Env.AggregateZero=true
local h=NewContext('UI/Bound.lua',Env,NewProfile,NewRoots,NewCounter,NewLeaves)
local fn=h:Wrap('zero',function() return 4 end);h:SetEnabled(true);fn();fn();h:SetEnabled(false)
Rows={};local status=Dump(R,{'UI/Bound.lua'},Emit)
assert(status.errors==0 and status.contexts==1 and status.samples==0 and #Rows==3)
assert(Rows[1][1]=='META' and Rows[1][3]==2 and Rows[2][1]=='TIMING_CONTROL')
assert(Rows[3][1]=='ZERO' and Rows[3][3]==2 and Rows[3][4]==1)
h.profile.zeroSuccess=nil;Rows={};assert(Dump(R,{'UI/Bound.lua'},Emit).errors==1)''')

    def test_old_context_without_timing_feature_keeps_original_export_shape(self):
        self.lua.execute('''local old=H:Snapshot();old.stats.timingChanges=nil;old.timingEnabled=nil
R.entries['UI/Test.lua'].Snapshot=function()return old end
local s=Run();assert(s.errors==0 and #Rows==4 and Rows[2][1]=='SAMPLE')''')


if __name__=='__main__':unittest.main()
