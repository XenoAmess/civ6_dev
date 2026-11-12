"""Core placement evidence remains read-only and independent of unlock ownership."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]

class PowerSitesTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiPowerSitesCore.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
TestSites={turn=278,owner=7,localPlayer=7,team=3,human=true,leader='LEADER_BAIQI',active=true,
 multiplayer=false,hotseat=false,visible=true,revealed=true,answer=true,calls=0,x=11,y=21,cx=10,cy=20}
local w=TestSites
local cfg={GetLeaderTypeName=function()return w.leader end}
local player={IsHuman=function()return w.human end,IsTurnActive=function()return w.active end,GetTeam=function()return w.team end}
local plot={GetIndex=function()return 100 end,GetOwner=function()return w.owner end,GetX=function()return w.x end,GetY=function()return w.y end}
local city={GetID=function()return 66 end,GetOwner=function()return w.owner end,GetX=function()return w.cx end,GetY=function()return w.cy end}
TestSiteEnv={Game={GetLocalPlayer=function()return w.localPlayer end,GetCurrentGameTurn=function()return w.turn end},
 GameConfiguration={IsAnyMultiplayer=function()return w.multiplayer end,IsHotseat=function()return w.hotseat end},
 Players={[7]=player},PlayerConfigurations={[7]=cfg},Map={GetPlotByIndex=function()return plot end},
 Cities={GetPlotPurchaseCity=function()return city end},
 PlayersVisibility={[7]={IsVisible=function()return w.visible end,IsRevealed=function()return w.revealed end}},
 GameInfo={Improvements={IMPROVEMENT_OFFSHORE_WIND_FARM={ImprovementType='IMPROVEMENT_OFFSHORE_WIND_FARM',Index=40,Hash=1058336991,PrereqTech='TECH_PREDICTIVE_SYSTEMS'}}},
 ImprovementBuilder={CanHaveImprovement=function(q,index,team)
  assert(q==plot and index==40 and team==3);w.calls=w.calls+1
  if w.shock then w.shock()end
  if w.throw then error('unknown native placement read')end
  return w.answer
 end}}
TestSiteAPI=BaiqiPowerSitesCore.Create({leader='LEADER_BAIQI'},TestSiteEnv)
''')
        self.w=self.lua.globals().TestSites

    def read(self):
        return self.lua.eval("TestSiteAPI.CanHave(7,278,100,66,'IMPROVEMENT_OFFSHORE_WIND_FARM')")

    def test_nonzero_plot_and_city_actual_team_and_boolean_results(self):
        self.assertIs(self.read(),True);self.w.answer=False;self.assertIs(self.read(),False)
        self.assertEqual(self.w.calls,2)
        # There is deliberately no GetTechs port: ownership must not gate suitability.

    def test_unknown_global_ports_and_context_reject_before_engine(self):
        for change in ('TestSiteEnv.ImprovementBuilder=nil','TestSiteEnv.Cities=nil',
                       'TestSiteEnv.PlayersVisibility=nil','TestSites.human=false',
                       'TestSites.leader="OTHER"','TestSites.active=false','TestSites.localPlayer=8',
                       'TestSites.multiplayer=true','TestSites.hotseat=true','TestSites.team=nil',
                       'TestSites.owner=8','TestSites.visible=false','TestSites.revealed=false'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.assertIsNone(self.read());self.assertEqual(self.w.calls,0)

    def test_error_nonboolean_and_missing_results_stay_unknown(self):
        for change in ('TestSites.throw=true','TestSites.answer=nil','TestSites.answer="false"','TestSites.answer=0'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);self.assertIsNone(self.read());self.assertEqual(self.w.calls,1)

    def test_final_context_identity_metadata_and_port_drift_invalidates_read(self):
        for change in ('TestSites.turn=279','TestSites.team=4','TestSites.x=12','TestSites.cx=12',
                       'TestSites.owner=8','TestSites.visible=false','TestSites.leader="OTHER"',
                       'TestSiteEnv.GameInfo.Improvements.IMPROVEMENT_OFFSHORE_WIND_FARM.Hash=20',
                       'TestSiteEnv.ImprovementBuilder.CanHaveImprovement=function()return true end'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute('TestSites.shock=function()'+change+' end')
                self.assertIsNone(self.read());self.assertEqual(self.w.calls,1)

    def test_input_and_purchase_city_identity_are_not_permissions(self):
        for args in ('7,278,100,67,"IMPROVEMENT_OFFSHORE_WIND_FARM"',
                     '7,278,true,66,"IMPROVEMENT_OFFSHORE_WIND_FARM"',
                     '7,278,100,66,"IMPROVEMENT_FARM"','7,0/0,100,66,"IMPROVEMENT_OFFSHORE_WIND_FARM"'):
            with self.subTest(args=args):
                self.setUp();self.assertIsNone(self.lua.eval('TestSiteAPI.CanHave('+args+')'));self.assertEqual(self.w.calls,0)

    def test_gameplay_registration_preserves_foreign_slot_and_has_no_bootstrap_read(self):
        wrapper=(ROOT/'mod/Baiqi/Lua/BaiqiPowerSitesGameplay.lua').read_text(encoding='utf-8')
        self.lua.execute('''include=function()end;BaiqiConfig={leader='LEADER_BAIQI'}
for k,v in pairs(TestSiteEnv)do _G[k]=v end
ExposedMembers={BaiqiPowerSitesBridge={marker='foreign',version=1}}
''')
        self.lua.execute(wrapper);self.assertEqual(self.lua.globals().ExposedMembers.BaiqiPowerSitesBridge.marker,'foreign')
        self.lua.execute('BaiqiPowerSitesGameplay=nil;ExposedMembers.BaiqiPowerSitesBridge=nil')
        self.lua.execute(wrapper);self.assertEqual(self.lua.globals().ExposedMembers.BaiqiPowerSitesBridge.marker,'baiqi-power-sites-v1')
        self.assertEqual(self.w.calls,0)

if __name__=='__main__':unittest.main()
