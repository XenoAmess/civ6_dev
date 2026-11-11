"""Paid flood response through the actual runner and Admin; no terrain simulation."""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]

class FloodPurchaseTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        for name in ('mock_admin','mock_flood'):
            self.lua.execute((ROOT/f'tests/lua/{name}.lua').read_text(encoding='utf-8'))
        self.lua.execute('''InstallFlood(nil,7);TestFlood.definition.Maintenance=1;local w=TestAdmin;w.tech=0;w.civic=0;w.policyChanged=true
w.purchases={};w.price=135;w.balance=2000;w.income=10;w.upkeep=0;w.canVisible=true;w.canFull=true
w.priceReads=0;w.qualifications=0
local c=TestFlood.cities[1]
c.GetGold=function()return {GetPurchaseCost=function(_,y,h)
 assert(y==0 and h==913);w.priceReads=w.priceReads+1
 if w.priceShock then w.priceShock()end;return w.price end}end
c.GetBuildQueue=function()error('Purchase must preserve the active production queue')end
Players[7].GetTreasury=function()return {GetGoldBalance=function()return w.balance end,
 GetGoldYield=function()return w.income end,GetTotalMaintenance=function()return w.upkeep end}end
Players[7]:GetTechs().GetResearchProgress=function()return 1 end
GameInfo.Yields={YIELD_GOLD={Index=0,YieldType='YIELD_GOLD'},YIELD_FAITH={Index=5,YieldType='YIELD_FAITH'}}
CityCommandTypes={PURCHASE=40,PARAM_BUILDING_TYPE=41,PARAM_YIELD_TYPE=42}
CityManager={CanStartCommand=function(city,op,visible,p,reasons)
 assert(city==c and op==40 and p[41]==913 and p[42]==0 and reasons==not visible)
 w.qualifications=w.qualifications+1;if w.qualificationShock then w.qualificationShock()end
 if visible then return w.canVisible else return w.canFull end end,
 RequestCommand=function(city,op,p)
 assert(city==c and op==40 and p[41]==913 and p[42]==0)
 local n=0;for _ in pairs(p)do n=n+1 end;assert(n==2)
 w.purchases[#w.purchases+1]={city=city:GetID(),op=op,params=p,quoted=w.price}
 if w.apply then TestFlood.has=true;w.balance=w.balance-w.price end
 if w.throwWriter then error('unknown after native writer')end end}
''')
        for name in ('BaiqiConfig','BaiqiFlood','BaiqiFloodPurchase'):
            path=Path(os.environ.get('BAIQI_FLOOD_PURCHASE_RUNNER')) if name=='BaiqiFloodPurchase'and os.environ.get('BAIQI_FLOOD_PURCHASE_RUNNER')else ROOT/f'mod/Baiqi/Lua/{name}.lua'
            self.lua.execute(path.read_text(encoding='utf-8'))
        self.lua.execute('E={Game=Game,GameConfiguration=GameConfiguration,UI=UI,Players=Players,PlayerConfigurations=PlayerConfigurations,GameInfo=GameInfo,Map=Map,PlayersVisibility=PlayersVisibility,TerrainManager=TerrainManager,CityManager=CityManager,CityCommandTypes=CityCommandTypes,config=BaiqiConfig}')
        self.w=self.lua.globals().TestAdmin
        self.runner=self.lua.globals().BaiqiFloodPurchase
    def change(self,s):self.lua.execute(s)
    def run_purchase(self):return self.runner.Run(self.lua.globals().E,7)
    def test_actual_gold_command_with_nil_purchase_yield_and_live_queue(self):
        self.assertTrue(self.run_purchase());self.assertEqual(len(self.w.purchases),1)
        self.assertEqual((self.w.purchases[1].op,self.w.purchases[1].params[41],self.w.purchases[1].params[42]),(40,913,0))
        self.assertEqual(self.w.balance,2000) # Request alone is not a debit/effect.
    def test_admin_invokes_runner_during_existing_positive_progress_research(self):
        source=Path(os.environ.get('BAIQI_FLOOD_PURCHASE_ADMIN')or ROOT/'mod/Baiqi/Lua/BaiqiAdmin.lua')
        self.lua.execute(source.read_text(encoding='utf-8'));self.lua.globals().BaiqiAdmin.Run()
        self.assertEqual(len(self.w.purchases),1);self.assertEqual(len(self.w.requests),0)
    def test_both_native_modes_require_explicit_true(self):
        for key,value in (('canVisible',False),('canFull',False),('canVisible',None),('canFull',1)):
            with self.subTest(key=key,value=value):
                self.setUp();self.w[key]=value;self.run_purchase();self.assertEqual(len(self.w.purchases),0)
    def test_price_and_budget_require_known_finite_positive_values(self):
        for key,value in (('price',None),('price',0),('price',-1),('price',float('inf')),('price',float('nan')),
                          ('balance',None),('balance',234.99),('income',None),('income',1),('upkeep',-1)):
            with self.subTest(key=key,value=value):
                self.setUp();self.w[key]=value;self.run_purchase();self.assertEqual(len(self.w.purchases),0)
    def test_exact_gold_reserve_and_net_income_boundary(self):
        self.w.balance=235;self.w.income=3;self.w.apply=True
        self.assertTrue(self.run_purchase());self.assertEqual(self.w.balance,100)
    def test_unknown_or_changed_rule_demand_and_currency_never_authorize(self):
        for change in ('TestFlood.has=true','TestFlood.flooded=nil','TestFlood.submerged=true',
                       'TestFlood.visible=false','TestFlood.throwTerrain=true','TestFlood.definition.Maintenance=-1',
                       'TestFlood.definition.Maintenance=math.huge','TestFlood.definition.Maintenance=0/0',
                       'TestFlood.definition.Maintenance="1"',
                       'GameInfo.Yields.YIELD_GOLD=nil','BaiqiConfig.goldReserve=nil','BaiqiConfig.netGoldMin=nil',
                       'CityCommandTypes.PARAM_YIELD_TYPE=41'):
            with self.subTest(change=change):
                self.setUp();self.change(change);self.run_purchase();self.assertEqual(len(self.w.purchases),0)
    def test_context_requires_own_active_human_baiqi_singleplayer_and_idle_core(self):
        for change in ('TestAdmin.leader="OTHER"','TestAdmin.active=false','TestFlood.owner=8',
                       'PlayerConfigurations[7].IsHuman=function()return false end',
                       'Game.GetLocalPlayer=function()return 8 end','GameConfiguration.IsAnyMultiplayer=function()return true end',
                       'GameConfiguration.IsHotseat=function()return true end','UI.IsGameCoreBusy=function()return true end',
                       'UI.IsProcessingMessages=function()return true end','Game.IsAllowStrategicCommands=function()return false end'):
            with self.subTest(change=change):
                self.setUp();self.change(change);self.run_purchase();self.assertEqual(len(self.w.purchases),0)
    def test_final_qualification_cannot_cover_price_budget_flood_turn_owner_or_queue_change(self):
        for change in ('TestAdmin.price=136','TestAdmin.balance=234','TestAdmin.income=1','TestFlood.definition.Maintenance=2','TestFlood.has=true',
                       'TestFlood.submerged=true','TestFlood.owner=8','TestAdmin.turn=2',
                       'UI.IsGameCoreBusy=function()return true end'):
            with self.subTest(change=change):
                self.setUp();self.change('TestAdmin.qualificationShock=function()if TestAdmin.qualifications==2 then '+change+' end end')
                self.run_purchase();self.assertEqual(len(self.w.purchases),0)
    def test_final_cost_read_cannot_cover_turn_or_identity_change(self):
        for change in ('TestAdmin.turn=2','TestFlood.owner=8','TestFlood.cities[1].GetX=function()return 9 end',
                       'TestFlood.has=true','TestFlood.flooded=false','TestFlood.flooded=nil','TestFlood.definition.Maintenance=2'):
            with self.subTest(change=change):
                self.setUp();self.change('TestAdmin.priceShock=function()if TestAdmin.priceReads==2 then '+change+' end end')
                self.run_purchase();self.assertEqual(len(self.w.purchases),0)
    def test_unknown_native_result_is_not_replayed_across_turns(self):
        self.run_purchase();self.w.turn=2
        for _ in range(4):self.run_purchase()
        self.assertEqual(len(self.w.purchases),1)
    def test_pending_holds_only_its_owned_city_until_observed(self):
        self.run_purchase();self.assertTrue(self.runner.Holds(7,66))
        self.assertFalse(self.runner.Holds(8,66));self.assertFalse(self.runner.Holds(7,67))
        self.change('TestFlood.has=true');self.run_purchase();self.assertFalse(self.runner.Holds(7,66))
    def test_exception_after_writer_stays_pending_until_observed(self):
        self.w.throwWriter=True;self.assertFalse(self.run_purchase());self.w.throwWriter=False;self.w.turn=2
        self.run_purchase();self.assertEqual(len(self.w.purchases),1)
        self.change('TestFlood.has=true');self.assertTrue(self.run_purchase());self.run_purchase()
        self.assertEqual(len(self.w.purchases),1)
    def test_unknown_or_pillaged_building_does_not_release_pending(self):
        self.run_purchase();self.change('TestFlood.has=true;TestFlood.barrierPillaged=nil');self.run_purchase()
        self.change('TestFlood.barrierPillaged=true');self.run_purchase();self.w.turn=2;self.run_purchase()
        self.assertEqual(len(self.w.purchases),1)
    def test_observation_ends_request_without_rebuy_or_queue_mutation(self):
        self.w.apply=True;self.run_purchase();self.assertTrue(self.run_purchase());self.run_purchase();self.w.turn=2;self.run_purchase()
        self.assertEqual(len(self.w.purchases),1);self.assertEqual(self.w.balance,1865)
    def test_foreign_pending_city_is_held_without_another_purchase(self):
        self.run_purchase();self.change('TestFlood.owner=8');self.w.turn=2;self.run_purchase()
        self.assertEqual(len(self.w.purchases),1)
    def test_native_read_exception_does_not_create_a_request(self):
        self.change("TestFlood.cities[1].GetGold=function()error('unavailable')end")
        self.assertFalse(self.run_purchase());self.assertEqual(len(self.w.purchases),0)
    def test_city_scan_has_finite_bound(self):
        self.change('TestFlood.flooded=false;local c=TestFlood.cities[1];Players[7].GetCities=function()return {FindID=function()return c end,Members=function()local n=0;return function()n=n+1;if n<=300 then TestAdmin.lastCity=n;return n,c end end end}end')
        self.run_purchase();self.assertEqual(self.w.lastCity,257);self.assertEqual(len(self.w.purchases),0)
    def test_positive_native_maintenance_is_budgeted_before_purchase(self):
        self.w.income=3;self.assertTrue(self.run_purchase())
        self.setUp();self.w.income=2;self.assertFalse(self.run_purchase());self.assertEqual(len(self.w.purchases),0)
    def test_zero_maintenance_remains_valid_when_current_net_is_exact_minimum(self):
        self.change('TestFlood.definition.Maintenance=0');self.w.income=2
        self.assertTrue(self.run_purchase())
    def test_same_turn_reserves_new_upkeep_even_before_native_treasury_refresh(self):
        self.change('''local w=TestAdmin;local c=TestFlood.cities[1];local c2=setmetatable({GetID=function()return 67 end,GetX=function()return 3 end},{__index=c})
w.built={};local cities={c,c2};for _,city in ipairs(cities)do local id=city:GetID();city.GetBuildings=function()return {HasBuilding=function()return w.built[id]==true end,IsPillaged=function()return false end}end end
Players[7].GetCities=function()return {Members=function()return ipairs(cities)end,FindID=function(_,id)if id==66 then return c elseif id==67 then return c2 end end}end
CityManager.CanStartCommand=function()return true end
CityManager.RequestCommand=function(city,op,p)w.purchases[#w.purchases+1]={city=city:GetID()};w.built[city:GetID()]=true;w.balance=w.balance-w.price end
''')
        self.w.income=3;self.run_purchase();self.run_purchase();self.run_purchase()
        self.assertEqual(len(self.w.purchases),1);self.assertEqual(self.w.upkeep,0)
        self.w.turn=2;self.w.upkeep=1;self.run_purchase();self.assertEqual(len(self.w.purchases),1)
        self.w.income=4;self.run_purchase();self.assertEqual(len(self.w.purchases),2)

if __name__=='__main__':unittest.main()
