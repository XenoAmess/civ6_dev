"""Exercise native-named checkboxes through captured selection and click handlers."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class CityPurchaseControlTests(unittest.TestCase):
    def load_city(self, ruleset='RULESET_EXPANSION_2'):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute((ROOT/'tests/lua/mock_guard.lua').read_text(encoding='utf-8'))
        lua.globals().TestRuleset = ruleset
        lua.execute('''
GameConfiguration.GetValue=function() return TestRuleset end
GameConfiguration.IsHotseat=function() return TestGuard.hotseat==true end
TestCityInput={gold=0,faith=0,information=0,draws=0,nativeDisabled=false}
Controls={}
local names={'ChangeProductionCheck','ProduceWithGoldCheck','ProduceWithFaithCheck',
 'PurchaseTileCheck','ManageCitizensCheck','FoodCheck','ProductionCheck','GoldCheck',
 'ScienceCheck','CultureCheck','FaithCheck','ToggleOverviewPanel'}
for _,name in ipairs(names) do
 local control={disabled=false,checked=false}
 function control:SetDisabled(value) self.disabled=value end
 function control:SetToolTipString(value) self.tooltip=value end
 function control:RegisterCheckHandler(fn) self.handler=fn end
 function control:Click()
  if self.disabled then return false end
  self.checked=not self.checked
  if self.handler then self.handler(self.checked) end
  return true
 end
 Controls[name]=control
end
''')

        def include(module):
            if module in ('CityPanel', 'CityPanel_Expansion1', 'CityPanel_Expansion2'):
                lua.execute('''
TestNativeCityPanel=...
local input=TestCityInput
Controls.ProduceWithGoldCheck:RegisterCheckHandler(function(checked)
 if checked then input.gold=input.gold+1 end
end)
Controls.ProduceWithFaithCheck:RegisterCheckHandler(function(checked)
 if checked then input.faith=input.faith+1 end
end)
Controls.ToggleOverviewPanel:RegisterCheckHandler(function() input.information=input.information+1 end)
ViewMain=function(data)
 input.draws=input.draws+1;input.lastData=data
 for _,control in pairs(Controls) do control:SetDisabled(input.nativeDisabled) end
end
-- Selection/data callbacks capture a caller with a global ViewMain lookup.
TestCapturedCitySelection=function(data) ViewMain(data) end
''', module)
            else:
                lua.execute((ROOT/f'mod/Baiqi/Lua/{module}.lua').read_text(encoding='utf-8'))

        lua.globals().include = include
        lua.execute((ROOT/'mod/Baiqi/UI/BaiqiCityPanel.lua').read_text(encoding='utf-8'))
        return lua

    def test_native_purchase_click_handlers_cannot_open_panels_for_baiqi_in_each_ruleset(self):
        for ruleset, native in (('RULESET_STANDARD', 'CityPanel'),
                                ('RULESET_EXPANSION_1', 'CityPanel_Expansion1'),
                                ('RULESET_EXPANSION_2', 'CityPanel_Expansion2')):
            with self.subTest(ruleset=ruleset):
                lua = self.load_city(ruleset)
                g = lua.globals()
                g.TestCapturedCitySelection('selected')
                self.assertEqual(g.TestNativeCityPanel, native)
                self.assertFalse(lua.eval('Controls.ProduceWithGoldCheck:Click()'))
                self.assertFalse(lua.eval('Controls.ProduceWithFaithCheck:Click()'))
                self.assertEqual((g.TestCityInput.gold, g.TestCityInput.faith), (0, 0))
                self.assertTrue(lua.eval('Controls.ToggleOverviewPanel:Click()'))
                self.assertEqual(g.TestCityInput.information, 1)

    def test_other_leader_multiplayer_hotseat_and_nonhuman_keep_native_purchase_behavior(self):
        for change in ("TestGuard.leader='LEADER_TRAJAN'", 'TestGuard.multi=true',
                       'TestGuard.hotseat=true', 'TestGuard.human=false'):
            with self.subTest(change=change):
                lua = self.load_city()
                lua.execute(change)
                g = lua.globals()
                g.TestCapturedCitySelection('same native data')
                self.assertEqual(g.TestCityInput.lastData, 'same native data')
                self.assertTrue(lua.eval('Controls.ProduceWithGoldCheck:Click()'))
                self.assertTrue(lua.eval('Controls.ProduceWithFaithCheck:Click()'))
                self.assertEqual((g.TestCityInput.gold, g.TestCityInput.faith), (1, 1))

    def test_native_repaint_cannot_restore_baiqi_purchase_controls_but_native_locks_are_preserved(self):
        lua = self.load_city()
        g = lua.globals()
        for frame in range(3):
            g.TestCapturedCitySelection(frame)
            self.assertFalse(lua.eval('Controls.ProduceWithGoldCheck:Click()'))
            self.assertFalse(lua.eval('Controls.ProduceWithFaithCheck:Click()'))
        self.assertEqual((g.TestCityInput.draws, g.TestCityInput.gold, g.TestCityInput.faith), (3, 0, 0))
        lua.execute("TestGuard.leader='LEADER_TRAJAN';TestCityInput.nativeDisabled=true")
        g.TestCapturedCitySelection('native lock')
        self.assertFalse(lua.eval('Controls.ProduceWithGoldCheck:Click()'))
        self.assertFalse(lua.eval('Controls.ProduceWithFaithCheck:Click()'))

    def test_optional_purchase_control_missing_does_not_break_city_inspection(self):
        lua = self.load_city()
        lua.execute('Controls.ProduceWithFaithCheck=nil')
        g = lua.globals()
        g.TestCapturedCitySelection('optional control absent')
        self.assertFalse(lua.eval('Controls.ProduceWithGoldCheck:Click()'))
        self.assertTrue(lua.eval('Controls.ToggleOverviewPanel:Click()'))
        self.assertEqual(g.TestCityInput.draws, 1)


if __name__ == '__main__':
    unittest.main()
