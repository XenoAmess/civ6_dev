"""Exercise the real rescue writer, durable bridge, and donor safety boundaries."""
from pathlib import Path
import unittest
from tests import test_baiqi_food_tile_rescue as fixture

ROOT = Path(__file__).resolve().parents[1]
UI_SOURCE = (ROOT / 'mod/Baiqi/Lua/BaiqiFoodTileRescueRunner.lua').read_text(encoding='utf-8')
CORE_SOURCE = (ROOT / 'mod/Baiqi/Lua/BaiqiFoodTileIntentGameplay.lua').read_text(encoding='utf-8')


class FoodSurplusDonorTests(unittest.TestCase):
    def world(self):
        l = fixture.FoodTileRescueTests().world()
        l.execute('''
          YieldTypes=E.YieldTypes
          W.sourceDistance=2;W.sourceHasPlot=true;W.donor=6;W.worked=1
          local source=Players[0]:GetCities():FindID(65536)
          source.GetGrowth=function()return {GetFoodSurplus=function()return W.donor end}end
          local original=E.CityManager.GetCommandTargets
          E.CityManager.GetCommandTargets=function(city,kind,p)
            local r=original(city,kind,p)
            if city==source and kind==E.CityCommandTypes.MANAGE then r[11][7]=W.worked end
            return r
          end
        ''')
        return l

    def test_worked_donor_runs_real_writer_once_after_persistence(self):
        l = self.world()
        l.execute('''BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==1 and W.requests[1].city==458758)
          assert(W.props.FOOD_TEST_V1.records['458758'].stage=='ARMED')
          assert(W.propertyWrites==1 and not W.transferred)
          W.turn=209;BaiqiFoodTileRescueRunner.Run(E,0);assert(#W.requests==1)''')

    def test_old_outside_idle_branch_still_runs_without_optional_core_argument(self):
        l = self.world()
        l.execute('''W.sourceDistance=4;W.sourceHasPlot=false
          BaiqiFoodTileRescueRunner.Run(E,0);assert(#W.requests==1)''')
        l = self.world()
        l.execute('''W.sourceDistance=4;W.sourceHasPlot=false
          assert(ExposedMembers.BaiqiFoodTileRescueBridge.Prepare(
            0,458758,59,32,65536,55,34,2277,57,30,208)==true)''')

    def test_donor_deficit_unknown_and_locked_or_multiple_workers_do_not_send(self):
        cases = ['W.donor=0', 'W.donor=-1', 'W.donor=0/0', 'W.donor=math.huge',
                 'W.donor=nil', 'W.sourceLocked=1', 'W.sourceLocked=nil',
                 'W.worked=0', 'W.worked=2', 'W.worked=-1', 'W.worked=nil',
                 'W.sourceDistance=0', 'W.sourceHasPlot=false', 'W.manageError=true']
        for case in cases:
            with self.subTest(case=case):
                l = self.world()
                l.execute(case + ''';BaiqiFoodTileRescueRunner.Run(E,0)
                  assert(#W.requests==0 and (W.propertyWrites or 0)==0)''')

    def test_exact_donor_surplus_is_enough_but_insufficient_target_gain_is_not(self):
        l = self.world()
        l.execute('''W.donor=1;BaiqiFoodTileRescueRunner.Run(E,0);assert(#W.requests==1)''')
        l = self.world()
        l.execute('''W.surplus=-2;BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==0 and (W.propertyWrites or 0)==0)''')

    def test_post_arm_donor_drift_holds_without_send_or_reload_replay(self):
        l = self.world()
        l.execute('''W.afterPersist=function()W.donor=0 end
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==0 and W.props.FOOD_TEST_V1.records['458758'].stage=='ARMED')''')
        l.execute(UI_SOURCE)
        l.execute('''W.afterPersist=nil;W.donor=6;W.turn=209
          BaiqiFoodTileRescueRunner.Run(E,0);assert(#W.requests==0 and W.propertyWrites==1)''')

    def test_core_accepts_ui_two_core_one_without_assuming_equal_yields(self):
        l = self.world()
        l.execute('''local ok,token,why=ExposedMembers.BaiqiFoodTileRescueBridge.Prepare(
          0,458758,59,32,65536,55,34,2277,57,30,208,2)
          assert(ok==true and type(token)=='string' and why=='armed' and W.propertyWrites==1)''')

    def test_core_donor_cost_and_unknown_ports_fail_before_property_write(self):
        cases = [('W.donor=1', '2'), ('W.donor=0/0', '1'), ('', 'nil'),
                 ('', '0'), ('', '-1'), ('', 'math.huge'), ('', 'true'),
                 ('W.sourceDistance=0', '1'),
                 ('Map.GetPlotByIndex(2277).GetDistrictType=function()return 9 end', '1'),
                 ('Map.GetPlotByIndex(2277).GetYield=function()return 3 end', '2'),
                 ('Map.GetPlotByIndex(2277).GetYield=nil', '2')]
        for change, expected in cases:
            with self.subTest(change=change, expected=expected):
                l = self.world()
                l.execute(change + '''
                  local ok=ExposedMembers.BaiqiFoodTileRescueBridge.Prepare(
                  0,458758,59,32,65536,55,34,2277,57,30,208,''' + expected + ''')
                  assert(ok==false and (W.propertyWrites or 0)==0)''')

    def test_core_second_eligibility_read_checks_source_again(self):
        l = self.world()
        l.execute('''local reads=0
          Players[0]:GetCities():FindID(65536).GetGrowth=function()return {
            GetFoodSurplus=function()reads=reads+1;if reads==1 then return 6 else return 0 end end}end
          assert(ExposedMembers.BaiqiFoodTileRescueBridge.Prepare(
            0,458758,59,32,65536,55,34,2277,57,30,208,1)==false)
          assert(reads==2 and (W.propertyWrites or 0)==0)''')

    def test_observation_requires_both_cities_nonnegative_after_real_effect(self):
        l = self.world()
        l.execute('''BaiqiFoodTileRescueRunner.Run(E,0)
          W.transferred=true;W.surplus=0;W.donor=-1;W.turn=209
          local b=ExposedMembers.BaiqiFoodTileRescueBridge
          assert(b.Inspect(0,458758)=='ARMED' and W.propertyWrites==1)
          W.donor=0;W.surplus=-1;assert(b.Inspect(0,458758)=='ARMED')
          W.surplus=0;assert(b.Inspect(0,458758)=='OBSERVED' and W.propertyWrites==2)
          assert(#W.requests==1)''')

    def test_unknown_donor_receipt_keeps_arm_and_late_receipt_survives_both_reloads(self):
        l = self.world()
        l.execute('''BaiqiFoodTileRescueRunner.Run(E,0)
          W.transferred=true;W.surplus=0;W.donor=nil;W.turn=209
          assert(ExposedMembers.BaiqiFoodTileRescueBridge.Inspect(0,458758)=='ARMED')''')
        l.execute(CORE_SOURCE)
        l.execute(UI_SOURCE)
        l.execute('''W.donor=5;W.turn=210;BaiqiFoodTileRescueRunner.Run(E,0)
          assert(W.props.FOOD_TEST_V1.records['458758'].stage=='OBSERVED')
          assert(#W.requests==1 and W.propertyWrites==2)''')

    def test_final_work_count_or_lock_drift_never_reaches_writer(self):
        for change in ['W.worked=2', 'W.sourceLocked=1', 'W.sourceDistance=0']:
            with self.subTest(change=change):
                l = self.world()
                l.execute('W.afterPersist=function()' + change + ''' end
                  BaiqiFoodTileRescueRunner.Run(E,0)
                  assert(#W.requests==0 and W.props.FOOD_TEST_V1.records['458758'].stage=='ARMED')''')


if __name__ == '__main__':
    unittest.main()
