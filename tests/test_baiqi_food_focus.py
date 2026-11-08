"""Native city food focus uses desired states, fresh permission and real effects."""
from pathlib import Path
import json
import unittest

from lupa.lua51 import LuaRuntime
from tests import test_baiqi_governor_loyalty as existing

ROOT = Path(__file__).resolve().parents[1]


class FoodFocusPlannerTests(unittest.TestCase):
    def test_bounded_pure_decisions_and_unknown_inputs(self):
        data = json.loads((ROOT / 'tests/fixtures/food_focus_cases.json').read_text(encoding='utf-8'))
        source = (ROOT / 'mod/Baiqi/Lua/BaiqiFoodFocus.lua').read_text(encoding='utf-8')
        for name, check in data['cases'].items():
            with self.subTest(case=name):
                lua = LuaRuntime(unpack_returned_tuples=True)
                lua.execute(data['fixture'])
                lua.globals().M = lua.execute(source)
                lua.execute(check)


class FoodFocusConsumerTests(unittest.TestCase):
    admin_source = None

    def setUp(self):
        self.fixture = existing.GovernorLoyaltyConsumerTests(methodName='runTest')
        self.fixture.setUp()
        self.lua, self.w = self.fixture.lua, self.fixture.w
        if self.admin_source is not None:
            self.lua.execute(self.admin_source)
            self.fixture.admin = self.lua.globals().BaiqiAdmin
        for name in ('BaiqiFoodFocus.lua', 'BaiqiFoodFocusRunner.lua'):
            self.lua.execute((ROOT / 'mod/Baiqi/Lua' / name).read_text(encoding='utf-8'))
        self.lua.execute('''
            local w=TestAdmin;w.gov.base[2]=1
            w.food={[1]=3,[2]=-1};w.fav={[1]=false,[2]=false};w.dis={[1]=false,[2]=false}
            w.focusRequests={};w.focusPending={};w.focusPermissionReads=0;w.focusAllowed=true
            w.busy=false;w.processing=false
            UI.IsGameCoreBusy=function()return w.busy end
            UI.IsProcessingMessages=function()return w.processing end
            YieldTypes={FOOD=0}
            CityCommandTypes={SET_FOCUS=90,PARAM_FLAGS='flags',PARAM_YIELD_TYPE='yield',PARAM_DATA0='data0'}
            for _,c in ipairs(w.gov.cities)do
                local id=c:GetID()
                c.GetX=function()return id+20 end;c.GetY=function()return 30 end
                c.GetGrowth=function()return {GetFoodSurplus=function()
                    if w.foodError then error('unknown')end;return w.food[id]end}end
                c.GetCitizens=function()return {
                    IsFavoredYield=function(_,y)assert(y==0);return w.fav[id]end,
                    IsDisfavoredYield=function(_,y)assert(y==0);return w.dis[id]end}end
            end
            CityManager={}
            CityManager.CanStartCommand=function(c,command,p)
                assert(command==90 and p.yield==0)
                w.focusPermissionReads=w.focusPermissionReads+1
                if w.onFocusPermission then w.onFocusPermission(c,p)end
                if w.permissionError then error('permission unknown')end
                return w.focusAllowed
            end
            CityManager.RequestCommand=function(c,command,p)
                assert(command==90 and p.yield==0)
                local r={city=c:GetID(),flags=p.flags,data0=p.data0}
                w.focusRequests[#w.focusRequests+1]=r;w.focusPending[#w.focusPending+1]=r
                if w.focusError then error('request uncertain')end
                return w.focusReturn
            end
            function w.ApplyFocus()
                for _,r in ipairs(w.focusPending)do
                    if r.flags==0 then w.fav[r.city]=r.data0==1
                    else assert(r.flags==1);w.dis[r.city]=r.data0==1 end
                end
                w.focusPending={}
            end
        ''')

    def run_admin(self, count=2):
        self.fixture.run_admin(count)

    def test_negative_food_submits_desired_focus_once_and_waits_for_effect(self):
        self.run_admin()
        self.assertEqual(len(self.w.focusRequests), 1)
        row = self.w.focusRequests[1]
        self.assertEqual((row.city, row.flags, row.data0), (2, 0, 1))
        self.assertFalse(self.w.fav[2])
        self.w.ApplyFocus()
        self.run_admin()
        self.assertTrue(self.w.fav[2])
        self.assertEqual(len(self.w.focusRequests), 1)

    def test_ignored_food_is_observed_unignored_before_favoring(self):
        self.w.dis[2] = True
        self.run_admin()
        self.assertEqual(len(self.w.focusRequests), 1)
        self.assertEqual((self.w.focusRequests[1].flags, self.w.focusRequests[1].data0), (1, 0))
        self.w.ApplyFocus()
        self.run_admin()
        self.assertEqual(len(self.w.focusRequests), 2)
        self.assertEqual((self.w.focusRequests[2].flags, self.w.focusRequests[2].data0), (0, 1))
        self.w.ApplyFocus()
        self.run_admin()
        self.assertEqual(len(self.w.focusRequests), 2)

    def test_false_void_or_throwing_request_not_replayed_next_turn(self):
        for mode in ('false', 'void', 'throw'):
            with self.subTest(mode=mode):
                self.setUp()
                if mode == 'false':
                    self.w.focusReturn = False
                if mode == 'throw':
                    self.w.focusError = True
                self.run_admin()
                self.w.turn = 2
                self.run_admin()
                self.assertEqual(len(self.w.focusRequests), 1)
                self.assertFalse(self.w.fav[2])

    def test_observed_uncertain_assignment_is_not_toggled_off(self):
        self.w.focusReturn = False
        self.run_admin()
        self.w.ApplyFocus()
        self.w.food[2] = 3
        self.w.turn = 2
        self.run_admin()
        self.assertTrue(self.w.fav[2])
        self.assertEqual(len(self.w.focusRequests), 1)

    def test_nonnegative_food_and_already_favored_do_not_write(self):
        for surplus, favored in ((0, False), (2, False), (-1, True)):
            with self.subTest(surplus=surplus, favored=favored):
                self.setUp()
                self.w.food[2], self.w.fav[2] = surplus, favored
                self.run_admin()
                self.assertEqual(len(self.w.focusRequests), 0)

    def test_permission_denial_or_exception_does_not_stop_research(self):
        for field in ('focusAllowed', 'permissionError'):
            with self.subTest(field=field):
                self.setUp()
                setattr(self.w, field, field == 'permissionError')
                self.run_admin()
                self.assertEqual(len(self.w.focusRequests), 0)
                self.assertGreaterEqual(len(self.w.requests), 2)

    def test_food_recovers_after_permission_before_write(self):
        self.lua.execute('TestAdmin.onFocusPermission=function()TestAdmin.food[2]=0 end')
        self.run_admin()
        self.assertEqual(len(self.w.focusRequests), 0)

    def test_owner_changes_after_permission_before_write(self):
        self.lua.execute('TestAdmin.onFocusPermission=function()TestAdmin.gov.foreign=true end')
        self.run_admin()
        self.assertEqual(len(self.w.focusRequests), 0)

    def test_turn_leader_or_busy_changes_after_permission_before_write(self):
        for code in ('TestAdmin.turn=2', "TestAdmin.leader='LEADER_TRAJAN'", 'TestAdmin.busy=true'):
            with self.subTest(code=code):
                self.setUp()
                self.lua.execute('TestAdmin.onFocusPermission=function()' + code + ' end')
                self.run_admin(1)
                self.assertEqual(len(self.w.focusRequests), 0)

    def test_writer_replaced_during_permission_is_not_called(self):
        self.lua.execute('TestAdmin.onFocusPermission=function()CityManager.RequestCommand=function()error("foreign writer")end end')
        self.run_admin()
        self.assertEqual(len(self.w.focusRequests), 0)

    def test_unknown_food_flags_or_missing_city_ports_preserve_research(self):
        for code in ('TestAdmin.foodError=true', 'TestAdmin.fav[2]=nil', 'TestAdmin.gov.cities[2].GetCitizens=nil'):
            with self.subTest(code=code):
                self.setUp()
                self.lua.execute(code)
                self.run_admin()
                self.assertEqual(len(self.w.focusRequests), 0)
                self.assertGreaterEqual(len(self.w.requests), 2)

    def test_missing_native_command_api_preserves_research(self):
        self.lua.execute('CityManager.CanStartCommand=nil')
        self.run_admin()
        self.assertEqual(len(self.w.focusRequests), 0)
        self.assertGreaterEqual(len(self.w.requests), 2)

    def test_each_own_negative_city_gets_its_own_held_request(self):
        self.w.food[1] = -2
        self.run_admin()
        self.assertEqual(len(self.w.focusRequests), 2)
        self.assertEqual({self.w.focusRequests[i].city for i in (1, 2)}, {1, 2})

    def test_pending_unignore_with_recovered_food_does_not_add_favor_request(self):
        self.w.dis[2] = True
        self.run_admin()
        self.assertEqual(len(self.w.focusRequests), 1)
        self.w.ApplyFocus()
        self.w.food[2] = 0
        self.run_admin()
        self.assertEqual(len(self.w.focusRequests), 1)

    def test_wrong_leader_multiplayer_or_inactive_player_never_writes(self):
        for code in ("TestAdmin.leader='LEADER_TRAJAN'", 'GameConfiguration.IsAnyMultiplayer=function()return true end', 'Players[7].IsTurnActive=function()return false end'):
            with self.subTest(code=code):
                self.setUp()
                self.lua.execute(code)
                self.run_admin()
                self.assertEqual(len(self.w.focusRequests), 0)


if __name__ == '__main__':
    unittest.main()
