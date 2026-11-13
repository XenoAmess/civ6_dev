"""Skip known no-action reads; every real proposal keeps fresh permission gates."""
import unittest

from tests import test_baiqi_food_focus as focus_fixture
from tests import test_baiqi_food_tile_rescue as rescue_fixture


class FoodDemandReadTests(unittest.TestCase):
    def rescue(self):
        return rescue_fixture.FoodTileRescueTests().world()

    def focus(self):
        fixture = focus_fixture.FoodFocusConsumerTests(methodName='runTest')
        fixture.setUp()
        lua = fixture.lua
        lua.execute('''
          FE={Game=Game,GameConfiguration=GameConfiguration,UI=UI,Players=Players,
            PlayerConfigurations=PlayerConfigurations,CityManager=CityManager,
            CityCommandTypes=CityCommandTypes,YieldTypes=YieldTypes,leader='LEADER_BAIQI'}
        ''')
        return lua

    def test_positive_rescue_rows_do_not_read_planning_flags_or_full_context_per_city(self):
        lua = self.rescue()
        lua.execute('''
          W.surplus=1;local busyReads,flags=0,0
          E.UI.IsGameCoreBusy=function()busyReads=busyReads+1;return false end
          for _,c in E.Players[0]:GetCities():Members()do
            c.GetCitizens=function()flags=flags+1;error('no proposal needed')end
          end
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(busyReads==2 and flags==0 and #W.requests==0 and (W.propertyWrites or 0)==0)
        ''')

    def test_positive_rescue_still_observes_late_old_arm_before_shortcut(self):
        lua = self.rescue()
        lua.execute('''
          local b=ExposedMembers.BaiqiFoodTileRescueBridge
          assert(b.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208))
          W.transferred=true;W.surplus=0;W.turn=210;local flags=0
          E.Players[0]:GetCities():FindID(458758).GetCitizens=function()flags=flags+1;error('no proposal')end
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(W.props.FOOD_TEST_V1.records['458758'].stage=='OBSERVED')
          assert(flags==0 and W.propertyWrites==2 and #W.requests==0)
        ''')

    def test_unknown_demand_never_enters_snapshot_or_sends(self):
        for value in ('nil', 'false', '"-1"', '0/0', 'math.huge', '1000001'):
            with self.subTest(value=value):
                lua = self.rescue()
                lua.execute('''
                  local c=E.Players[0]:GetCities():FindID(458758);local flags=0
                  c.GetGrowth=function()return{GetFoodSurplus=function()return ''' + value + ''' end}end
                  c.GetCitizens=function()flags=flags+1;error('unknown demand')end
                  BaiqiFoodTileRescueRunner.Run(E,0)
                  assert(flags==0 and #W.requests==0 and (W.propertyWrites or 0)==0)
                ''')

    def test_negative_demand_is_freshly_read_again_for_snapshot(self):
        lua = self.rescue()
        lua.execute('''
          local c=E.Players[0]:GetCities():FindID(458758);local reads=0
          c.GetGrowth=function()return{GetFoodSurplus=function()
            reads=reads+1;return reads==1 and -1 or 0
          end,GetTurnsUntilStarvation=function()return 2 end}end
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(reads==2 and #W.requests==0 and (W.propertyWrites or 0)==0)
        ''')

    def test_context_lost_during_negative_demand_prevents_snapshot_and_prepare(self):
        for change in ('W.busy=true', 'W.active=false', 'W.multi=true', 'W.human=false',
                       "W.leader='LEADER_TRAJAN'", 'W.turn=209'):
            with self.subTest(change=change):
                lua = self.rescue()
                lua.execute('''
                  local c=E.Players[0]:GetCities():FindID(458758);local reads,flags=0,0
                  c.GetGrowth=function()return{GetFoodSurplus=function()
                    reads=reads+1;''' + change + ''';return -1
                  end}end
                  c.GetCitizens=function()flags=flags+1;error('must requalify before snapshot')end
                  BaiqiFoodTileRescueRunner.Run(E,0)
                  assert(reads==1 and flags==0 and #W.requests==0 and (W.propertyWrites or 0)==0)
                ''')

    def test_scope_changes_after_batch_are_rejected_before_food_read(self):
        lua = self.rescue()
        lua.execute('''
          local c=E.Players[0]:GetCities():FindID(458758);local y=c.GetY;local visits,food=0,0
          c.GetY=function(self)
            visits=visits+1
            if visits==2 then E.Game.GetLocalPlayer=function()return 1 end end
            return y(self)
          end
          c.GetGrowth=function()food=food+1;error('foreign demand read forbidden')end
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(visits==2 and food==0 and #W.requests==0 and (W.propertyWrites or 0)==0)
        ''')

    def test_focus_positive_without_pending_never_reads_citizen_flags(self):
        lua = self.focus()
        lua.execute('''
          TestAdmin.food[2]=0;local calls=0
          for _,c in ipairs(TestAdmin.gov.cities)do
            c.GetCitizens=function()calls=calls+1;error('no focus proposal')end
          end
          BaiqiFoodFocusRunner.Run(FE,7)
          assert(calls==0 and #TestAdmin.focusRequests==0)
        ''')

    def test_focus_pending_still_observes_positive_or_unknown_food_then_skips(self):
        for food in ('1', 'nil', '0/0'):
            with self.subTest(food=food):
                lua = self.focus()
                lua.execute('''
                  BaiqiFoodFocusRunner.Run(FE,7);assert(#TestAdmin.focusRequests==1)
                  TestAdmin.ApplyFocus();TestAdmin.food[2]=''' + food + '''
                  local c=TestAdmin.gov.cities[2];local citizens=c.GetCitizens;local calls=0
                  c.GetCitizens=function(self)calls=calls+1;return citizens(self)end
                  BaiqiFoodFocusRunner.Run(FE,7);assert(calls==1)
                  TestAdmin.food[2]=1;BaiqiFoodFocusRunner.Run(FE,7)
                  assert(calls==1 and #TestAdmin.focusRequests==1)
                ''')

    def test_focus_unknown_without_pending_never_sends_or_reads_flags(self):
        for food in ('nil', 'false', '"1"', '0/0', 'math.huge'):
            with self.subTest(food=food):
                lua = self.focus()
                lua.execute('''
                  TestAdmin.food[2]=''' + food + ''';local c=TestAdmin.gov.cities[2];local calls=0
                  c.GetCitizens=function()calls=calls+1;error('unknown unheld demand')end
                  BaiqiFoodFocusRunner.Run(FE,7)
                  assert(calls==0 and #TestAdmin.focusRequests==0)
                ''')


if __name__ == '__main__':
    unittest.main()
