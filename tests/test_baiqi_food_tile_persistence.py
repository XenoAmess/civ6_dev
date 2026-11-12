"""Real journal/Core/UI implementations with simulated native effects and reloads."""
from pathlib import Path
import unittest
from tests import test_baiqi_food_tile_rescue as rescue_fixture

ROOT = Path(__file__).resolve().parents[1]
UI_SOURCE = (ROOT / 'mod/Baiqi/Lua/BaiqiFoodTileRescueRunner.lua').read_text(encoding='utf-8')
CORE_SOURCE = (ROOT / 'mod/Baiqi/Lua/BaiqiFoodTileIntentGameplay.lua').read_text(encoding='utf-8')


class FoodTilePersistenceTests(unittest.TestCase):
    def world(self):
        return rescue_fixture.FoodTileRescueTests().world()

    def test_permission_is_persisted_and_verified_before_the_only_native_send(self):
        l = self.world()
        l.execute('''W.oldWriter=E.CityManager.RequestCommand
          E.CityManager.RequestCommand=function(...)
            local s=W.props.FOOD_TEST_V1;local r=s.records['458758']
            assert(s.serial==1 and r.stage=='ARMED' and r.cityX==59 and r.cityY==32)
            assert(r.sourceX==55 and r.sourceY==34 and r.plotX==57 and r.plotY==30)
            return W.oldWriter(...)
          end
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==1 and W.propertyWrites==1 and Map.GetCityPlots==nil)''')

    def test_void_false_and_throw_hold_across_ui_reload_and_future_turns(self):
        for mode in ('W.requestReturn=nil', 'W.requestReturn=false', 'W.throw=true'):
            with self.subTest(mode=mode):
                l = self.world()
                l.execute(mode + ';BaiqiFoodTileRescueRunner.Run(E,0);assert(#W.requests==1)')
                for turn in (209, 210, 215):
                    l.execute(UI_SOURCE)
                    l.execute(f'''W.turn={turn};BaiqiFoodTileRescueRunner.Run(E,0)
                      assert(#W.requests==1 and W.props.FOOD_TEST_V1.serial==1)
                      assert(W.props.FOOD_TEST_V1.records['458758'].stage=='ARMED')''')

    def test_a_loaded_old_arm_is_not_a_fresh_send_grant(self):
        l = self.world()
        l.execute('''local b=ExposedMembers.BaiqiFoodTileRescueBridge
          local ok,token=b.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208)
          assert(ok and type(token)=='string')
          W.turn=209;BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==0 and W.propertyWrites==1)''')

    def test_late_real_effect_is_observed_after_ui_and_core_reload_without_resend(self):
        l = self.world()
        l.execute('BaiqiFoodTileRescueRunner.Run(E,0);assert(#W.requests==1)')
        l.execute(CORE_SOURCE)
        l.execute(UI_SOURCE)
        l.execute('''W.transferred=true;W.surplus=0;W.turn=210
          BaiqiFoodTileRescueRunner.Run(E,0)
          local r=W.props.FOOD_TEST_V1.records['458758']
          assert(r.stage=='OBSERVED' and r.observedTurn==210 and r.observedSurplus==0)
          assert(#W.requests==1 and W.propertyWrites==2)
          BaiqiFoodTileRescueRunner.Run(E,0);assert(W.propertyWrites==2)''')

    def test_ownership_with_negative_food_is_only_a_transfer_receipt(self):
        l = self.world()
        l.execute('''BaiqiFoodTileRescueRunner.Run(E,0)
          W.transferred=true;W.turn=209;BaiqiFoodTileRescueRunner.Run(E,0)
          assert(W.props.FOOD_TEST_V1.records['458758'].stage=='TRANSFERRED' and #W.requests==1)
          W.surplus=0;BaiqiFoodTileRescueRunner.Run(E,0)
          assert(W.props.FOOD_TEST_V1.records['458758'].stage=='OBSERVED' and #W.requests==1)''')

    def test_property_mutation_then_throw_cannot_authorize_a_native_command(self):
        l = self.world()
        l.execute('''W.persistThrows=true;BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==0 and W.props.FOOD_TEST_V1.records['458758'].stage=='ARMED')''')
        l.execute(UI_SOURCE)
        l.execute('''W.persistThrows=false;W.turn=209;BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==0 and W.props.FOOD_TEST_V1.serial==1)''')

    def test_unknown_post_write_readback_is_held_after_reader_recovers(self):
        l = self.world()
        l.execute('''W.afterPersist=function()W.readError=true end
          BaiqiFoodTileRescueRunner.Run(E,0);assert(#W.requests==0)
          W.readError=false;W.afterPersist=nil;W.turn=209
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==0 and W.propertyWrites==1)''')

    def test_uncertain_prepare_without_a_token_never_sends_or_retries_in_context(self):
        l = self.world()
        l.execute('''local b=ExposedMembers.BaiqiFoodTileRescueBridge
          b.Prepare=function()W.prepareCalls=(W.prepareCalls or 0)+1;error('unknown Prepare reply')end
          BaiqiFoodTileRescueRunner.Run(E,0)
          W.turn=209;BaiqiFoodTileRescueRunner.Run(E,0)
          assert(W.prepareCalls==1 and #W.requests==0 and (W.propertyWrites or 0)==0)''')

    def test_observation_mutation_then_throw_does_not_repeat_original_command(self):
        l = self.world()
        l.execute('''BaiqiFoodTileRescueRunner.Run(E,0)
          W.transferred=true;W.surplus=0;W.turn=209
          W.afterPersist=function(s)if s.records['458758'].stage=='OBSERVED'then error('receipt reply lost')end end
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==1 and W.props.FOOD_TEST_V1.records['458758'].stage=='OBSERVED')''')
        l.execute(UI_SOURCE)
        l.execute('''W.afterPersist=nil;BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==1 and W.propertyWrites==2)''')

    def test_unknown_or_missing_bridge_and_corrupt_property_never_fall_back(self):
        for change in ['E.ExposedMembers=nil',
                       'ExposedMembers.BaiqiFoodTileRescueBridge.marker="foreign"',
                       'W.readError=true',
                       'W.props.FOOD_TEST_V1={version=9}',
                       'W.props.FOOD_TEST_V1={version=1,owner=1,serial=0,records={}}']:
            with self.subTest(change=change):
                l = self.world()
                l.execute(change + ''';BaiqiFoodTileRescueRunner.Run(E,0)
                  assert(#W.requests==0 and (W.propertyWrites or 0)==0)''')

    def test_post_arm_permission_identity_or_binding_changes_hold_without_send(self):
        changes = ['W.allowed=false', 'W.busy=true', 'W.owner=1',
                   'E.YieldTypes.FOOD=1',
                   'E.CityManager.RequestCommand=function()W.foreignCalled=true end',
                   'ExposedMembers.BaiqiFoodTileRescueBridge.Prepare=function()return true,"fake","armed"end',
                   'ExposedMembers.BaiqiFoodTileRescueBridge.Inspect=function()return "ARMED","fake"end']
        for change in changes:
            with self.subTest(change=change):
                l = self.world()
                l.execute('W.afterPersist=function() ' + change + ''' end
                  BaiqiFoodTileRescueRunner.Run(E,0)
                  assert(#W.requests==0 and not W.foreignCalled)
                  assert(W.props.FOOD_TEST_V1.records['458758'].stage=='ARMED')''')

    def test_source_city_coordinate_changes_after_arm_are_not_plot_coordinates(self):
        l = self.world()
        l.execute('''W.afterPersist=function()
            Players[0]:GetCities():FindID(65536).GetX=function()return 56 end
            E.Map.GetPlotDistance=function(x,y)if y==34 then return 4 else return 3 end end
          end
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==0 and W.props.FOOD_TEST_V1.records['458758'].sourceX==55)''')

    def test_core_foreign_owner_plot_identity_or_stale_find_denies_before_persist(self):
        for change in ['W.owner=1', 'W.staleFind=true', 'W.sourceID=999',
                       'Map.GetPlotByIndex(2277).GetOwner=function()return 1 end',
                       'Cities.GetPlotPurchaseCity=function()return Players[0]:GetCities():FindID(458758)end']:
            with self.subTest(change=change):
                l = self.world()
                l.execute(change + ''';local b=ExposedMembers.BaiqiFoodTileRescueBridge
                  local ok=b.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208)
                  assert(ok==false and (W.propertyWrites or 0)==0)''')

    def test_foreign_published_bridge_is_preserved_and_old_closure_cannot_write(self):
        l = self.world()
        l.execute('''oldBridge=ExposedMembers.BaiqiFoodTileRescueBridge
          foreignBridge={marker='foreign',version=1};ExposedMembers.BaiqiFoodTileRescueBridge=foreignBridge''')
        l.execute(CORE_SOURCE)
        l.execute('''assert(ExposedMembers.BaiqiFoodTileRescueBridge==foreignBridge)
          local ok=oldBridge.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208)
          assert(ok==false and (W.propertyWrites or 0)==0)''')

    def test_core_rejects_future_arming_and_does_not_expire_existing_past_arm(self):
        l = self.world()
        l.execute('''local b=ExposedMembers.BaiqiFoodTileRescueBridge
          assert(b.Prepare(0,458758,59,32,65536,55,34,2277,57,30,209)==false)
          assert((W.propertyWrites or 0)==0)
          assert(b.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208)==true)
          W.turn=207;assert(b.Inspect(0,458758)=='ARMED')
          W.turn=500;assert(b.Inspect(0,458758)=='ARMED')
          assert(W.propertyWrites==1)''')

    def armed_state(self, l):
        l.execute('''local ok=ExposedMembers.BaiqiFoodTileRescueBridge.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208)
          assert(ok);S=CopyProperty(W.props.FOOD_TEST_V1);R=S.records['458758']''')

    def test_strict_journal_bounds_keys_tokens_and_immutable_clones(self):
        changes = ['S.extra=true', 'S.serial=0/0', 'S.owner=1', 'S.records[1]=R',
                   'R.cityX=nil', 'R.cityY=46', 'R.sourceCityID=R.cityID',
                   'R.token="wrong"', 'R.sequence=math.huge', 'R.plotID=999999',
                   'R.stage="UNKNOWN"', 'R.observedTurn=208', 'setmetatable(R,{})',
                   'setmetatable(S,{})', 'setmetatable(S.records,{})']
        for change in changes:
            with self.subTest(change=change):
                l = self.world()
                self.armed_state(l)
                l.execute(change + ';assert(not BaiqiFoodTileJournal.Validate(S,0))')
        l = self.world()
        self.armed_state(l)
        l.execute('''local c=BaiqiFoodTileJournal.Clone(S,0);assert(BaiqiFoodTileJournal.Equal(S,c,0))
          c.records['458758'].sourceX=54;assert(R.sourceX==55 and not BaiqiFoodTileJournal.Equal(S,c,0))''')

    def test_serial_and_record_capacity_never_discard_unknown_history(self):
        for setup in ['S.serial=2147483647', '''
            S.records={};S.serial=128
            for i=1,128 do local r=CopyProperty(R);r.cityID=100000+i;r.sequence=i
              r.token=BaiqiFoodTileJournal.Token(0,i);S.records[tostring(r.cityID)]=r end''']:
            with self.subTest(setup=setup):
                l = self.world()
                self.armed_state(l)
                l.execute(setup + ''';assert(BaiqiFoodTileJournal.Validate(S,0))
                  W.props.FOOD_TEST_V1=S;local before=W.propertyWrites
                  assert(ExposedMembers.BaiqiFoodTileRescueBridge.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208)==false)
                  assert(W.propertyWrites==before)''')

    def test_another_city_cannot_claim_the_plot_of_an_unresolved_intent(self):
        l = self.world()
        self.armed_state(l)
        l.execute('''S.records={};R.cityID=999;S.records['999']=R;W.props.FOOD_TEST_V1=S
          local before=W.propertyWrites
          local ok,token,why=ExposedMembers.BaiqiFoodTileRescueBridge.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208)
          assert(ok==false and why=='prior_plot_unresolved' and W.propertyWrites==before)''')


if __name__ == '__main__':
    unittest.main()
