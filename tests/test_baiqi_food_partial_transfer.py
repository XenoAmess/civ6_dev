"""Known assignment receipts may authorize a different plan, never a replay."""
from pathlib import Path
import unittest
from tests import test_baiqi_food_tile_rescue as fixture

ROOT = Path(__file__).resolve().parents[1]
UI_SOURCE = (ROOT / 'mod/Baiqi/Lua/BaiqiFoodTileRescueRunner.lua').read_text(encoding='utf-8')
CORE_SOURCE = (ROOT / 'mod/Baiqi/Lua/BaiqiFoodTileIntentGameplay.lua').read_text(encoding='utf-8')


class FoodPartialTransferTests(unittest.TestCase):
    def world(self):
        l = fixture.FoodTileRescueTests().world()
        l.execute((ROOT / 'tests/fixtures/food_two_transfers.lua').read_text(encoding='utf-8'))
        return l

    def arm(self, l):
        l.execute('''local b=ExposedMembers.BaiqiFoodTileRescueBridge
          assert(b.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208,2)==true)''')

    def test_same_turn_two_real_distinct_transfers_then_nonnegative_receipt(self):
        l = self.world()
        l.execute('''BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==1 and W.requests[1].plotID==2276 and W.surplus==-1)
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==2 and W.requests[2].plotID==2277 and W.surplus==0 and W.donor==2)
          BaiqiFoodTileRescueRunner.Run(E,0)
          local j=W.props.FOOD_TEST_V1;local r=j.records['458758']
          assert(j.serial==2 and r.stage=='OBSERVED' and r.observedSurplus==0)
          assert(#W.requests==2 and W.propertyWrites==4)''')

    def test_old_loaded_arm_actual_applied_can_continue_only_a_different_plot(self):
        l = self.world()
        self.arm(l)
        l.execute('''W.applied[2277]=true;W.surplus=-1
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==1 and W.requests[1].plotID==2276)
          assert(W.props.FOOD_TEST_V1.serial==2 and W.surplus==0)''')

    def test_partial_receipt_is_stable_across_turns_until_food_becomes_nonnegative(self):
        l = self.world()
        self.arm(l)
        l.execute('''W.applied[2277]=true;W.surplus=-0.5
          local b=ExposedMembers.BaiqiFoodTileRescueBridge
          assert(b.Inspect(0,458758)=='TRANSFERRED' and W.propertyWrites==2)
          W.turn=209;W.surplus=-0.25
          assert(b.Inspect(0,458758)=='TRANSFERRED' and W.propertyWrites==2)
          local r=W.props.FOOD_TEST_V1.records['458758']
          assert(r.observedTurn==208 and r.observedSurplus==-0.5)
          W.surplus=0;assert(b.Inspect(0,458758)=='OBSERVED' and W.propertyWrites==3)''')

    def test_negative_fraction_validates_but_wrong_sign_bounds_and_unknown_stage_do_not(self):
        l = self.world()
        self.arm(l)
        l.execute('''Saved=CopyProperty(W.props.FOOD_TEST_V1)
          local r=Saved.records['458758'];r.stage='TRANSFERRED';r.observedTurn=208;r.observedSurplus=-0.5
          assert(BaiqiFoodTileJournal.Validate(Saved,0))''')
        for change in ['r.observedSurplus=0', 'r.observedSurplus=1', 'r.observedSurplus=-1000001',
                       'r.observedSurplus=0/0', 'r.observedTurn=207', 'r.observedTurn=208.5',
                       'r.stage="UNKNOWN"', 'r.extra=true']:
            with self.subTest(change=change):
                l.execute('local s=CopyProperty(Saved);local r=s.records["458758"];'
                          + change + ';assert(not BaiqiFoodTileJournal.Validate(s,0))')

    def test_source_negative_or_unknown_identity_prevents_terminal_receipt(self):
        for change in ['W.donor=-1', 'W.donor=nil',
                       'Players[0]:GetCities():FindID(65536).GetX=function()return 99 end',
                       'Cities.GetPlotPurchaseCity=function()return Players[0]:GetCities():FindID(65536)end']:
            with self.subTest(change=change):
                l = self.world()
                self.arm(l)
                l.execute('W.applied[2277]=true;W.surplus=-1;' + change + '''
                  local stage=ExposedMembers.BaiqiFoodTileRescueBridge.Inspect(0,458758)
                  assert(stage~='TRANSFERRED' and stage~='OBSERVED' and W.propertyWrites==1)''')

    def test_same_plot_explicit_denial_even_when_later_purchase_data_returns_to_source(self):
        l = self.world()
        self.arm(l)
        l.execute('''W.applied[2277]=true;W.surplus=-1
          local b=ExposedMembers.BaiqiFoodTileRescueBridge
          assert(b.Inspect(0,458758)=='TRANSFERRED')
          W.applied[2277]=false
          local ok,token,why=b.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208)
          assert(ok==false and why=='same_plot' and W.propertyWrites==2)''')

    def test_unknown_unapplied_arm_stays_once_across_actual_core_and_ui_reload(self):
        l = self.world()
        l.execute('''W.noApply=true;W.requestReturn=false
          BaiqiFoodTileRescueRunner.Run(E,0);assert(#W.requests==1)''')
        l.execute(CORE_SOURCE)
        l.execute(UI_SOURCE)
        l.execute('''W.turn=209;BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==1 and W.props.FOOD_TEST_V1.serial==1)
          assert(W.props.FOOD_TEST_V1.records['458758'].stage=='ARMED')''')

    def test_applied_partial_receipt_survives_both_reloads_and_grants_only_new_plot(self):
        l = self.world()
        l.execute('BaiqiFoodTileRescueRunner.Run(E,0);assert(#W.requests==1)')
        l.execute(CORE_SOURCE)
        l.execute(UI_SOURCE)
        l.execute('''BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==2 and W.requests[1].plotID~=W.requests[2].plotID)
          assert(W.surplus==0)''')

    def test_wrong_or_missing_token_does_not_release_a_known_local_hold(self):
        for token in ['"fake"', 'nil']:
            with self.subTest(token=token):
                l = self.world()
                l.execute('''W.noApply=true;BaiqiFoodTileRescueRunner.Run(E,0)
                  local b=ExposedMembers.BaiqiFoodTileRescueBridge
                  b.Inspect=function()return 'TRANSFERRED',''' + token + ''' end
                  BaiqiFoodTileRescueRunner.Run(E,0);assert(#W.requests==1)''')

    def test_unknown_prepare_reply_without_token_cannot_release_local_hold(self):
        l = self.world()
        l.execute('''local b=ExposedMembers.BaiqiFoodTileRescueBridge;local original=b.Prepare
          b.Prepare=function(...)original(...);error('lost prepare reply')end
          BaiqiFoodTileRescueRunner.Run(E,0);assert(#W.requests==0)
          W.applied[2276]=true;W.surplus=-1;b.Prepare=original
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==0 and W.props.FOOD_TEST_V1.serial==1)''')

    def test_open_nil_and_terminal_string_nil_are_distinct_attempt_scopes(self):
        l = self.world()
        l.execute('''local b=ExposedMembers.BaiqiFoodTileRescueBridge;local phase=1;local calls=0
          b.Inspect=function(pid,id)if id~=458758 then return 'OPEN',nil end
            if phase==1 then return 'OPEN',nil else return 'TRANSFERRED','nil' end end
          b.Prepare=function()calls=calls+1;return false,nil,'invalid_record' end
          BaiqiFoodTileRescueRunner.Run(E,0);BaiqiFoodTileRescueRunner.Run(E,0);assert(calls==1)
          phase=2;BaiqiFoodTileRescueRunner.Run(E,0);BaiqiFoodTileRescueRunner.Run(E,0)
          assert(calls==2 and #W.requests==0)''')

    def test_new_plan_final_drift_keeps_second_arm_without_second_writer(self):
        l = self.world()
        l.execute('''BaiqiFoodTileRescueRunner.Run(E,0);assert(#W.requests==1)
          W.afterPersist=function(j)if j.serial==2 and j.records['458758'].stage=='ARMED'then W.allowed=false end end
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==1 and W.props.FOOD_TEST_V1.serial==2)
          assert(W.props.FOOD_TEST_V1.records['458758'].stage=='ARMED')''')


if __name__ == '__main__':
    unittest.main()
