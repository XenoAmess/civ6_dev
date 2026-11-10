"""Keep Core's actual player-only human port separate from UI configuration."""
import unittest
from tests import test_baiqi_food_tile_rescue as fixture


class FoodTileCoreHumanTests(unittest.TestCase):
    def world(self, core_human='nil', player_human='function()return true end'):
        lua = fixture.FoodTileRescueTests().world()
        lua.execute('''PlayerConfigurations={[0]={
          GetLeaderTypeName=function()return 'LEADER_BAIQI'end}}
          PlayerConfigurations[0].IsHuman=''' + core_human + '''
          Players[0].IsHuman=''' + player_human)
        return lua

    def test_actual_core_missing_config_port_uses_true_player_and_sends_once(self):
        l = self.world()
        l.execute('''local stage=ExposedMembers.BaiqiFoodTileRescueBridge.Inspect(0,458758)
          assert(stage=='OPEN');BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==1 and W.propertyWrites==1)
          assert(W.props.FOOD_TEST_V1.records['458758'].stage=='ARMED')''')

    def test_present_config_false_nil_throw_or_nonboolean_never_uses_player_true(self):
        for result in ['return false', 'return nil', "error('unknown human')", 'return 1', 'return "true"']:
            with self.subTest(result=result):
                l = self.world('function()' + result + ' end')
                l.execute('''local s=ExposedMembers.BaiqiFoodTileRescueBridge.Inspect(0,458758)
                  assert(s=='UNAVAILABLE');BaiqiFoodTileRescueRunner.Run(E,0)
                  assert(#W.requests==0 and (W.propertyWrites or 0)==0)''')

    def test_missing_config_uses_no_uncertain_player_result(self):
        for result in ['return false', 'return nil', "error('unknown player')", 'return 1', 'return "true"']:
            with self.subTest(result=result):
                l = self.world('nil', 'function()' + result + ' end')
                l.execute('''BaiqiFoodTileRescueRunner.Run(E,0)
                  assert(#W.requests==0 and (W.propertyWrites or 0)==0)''')

    def test_both_ports_absent_cannot_authorize_prepare(self):
        l = self.world('nil', 'nil')
        l.execute('''local ok=ExposedMembers.BaiqiFoodTileRescueBridge.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208)
          assert(ok==false and (W.propertyWrites or 0)==0)''')

    def test_present_true_config_remains_authoritative(self):
        l = self.world('function()return true end', "function()error('must not read player')end")
        l.execute('''BaiqiFoodTileRescueRunner.Run(E,0);assert(#W.requests==1 and W.propertyWrites==1)''')


if __name__ == '__main__':
    unittest.main()
