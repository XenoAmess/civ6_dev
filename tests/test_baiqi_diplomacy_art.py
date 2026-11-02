"""Exercise native callback boundaries and per-displayed-leader art isolation."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class DiplomacyArtTests(unittest.TestCase):
    def load(self, ruleset='RULESET_EXPANSION_2'):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''
          Native={shows=0,layers=0,loads=0,requests=0,hideAnchor=false,top=false,bottom=false}
          GameConfiguration={GetValue=function() return ... end}
          PlayerConfigurations={
            [0]={GetLeaderTypeName=function() return 'LEADER_GORGO' end},
            [1]={GetLeaderTypeName=function() return 'LEADER_BAIQI' end},
            [2]={GetLeaderTypeName=function() return 'LEADER_AMBIORIX' end}}
          TestPlayer=function(id) return {GetID=function() return id end} end
          Controls={
            LeaderAnchor={SetHide=function(_,v) Native.hideAnchor=v end},
            TopLetterbox={SetHide=function(_,v) Native.top=v end},
            BottomLetterbox={SetHide=function(_,v) Native.bottom=v end}}
          Events={ShowLeaderScreen=function(name,self)
            Native.shows=Native.shows+1;Native.lastLeader=name;Native.self=self
          end}
          OriginalEvents=Events
          NativeRequestSession=function(from,to,key)
            Native.requests=Native.requests+1;return from,to,key
          end
        '''.replace("return ... end", "return '" + ruleset + "' end"))
        native_modules = []

        def include(name):
            if name == 'BaiqiUILoader':
                lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiUILoader.lua').read_text(encoding='utf-8'))
            elif name in ('DiplomacyActionView', 'DiplomacyActionView_Expansion1', 'DiplomacyActionView_Expansion2'):
                native_modules.append(name)
                lua.execute('''
                  -- Native SelectPlayer's event callback resolves ShowLeader globally.
                  function ShowLeader(player)
                    Native.loads=Native.loads+1
                    Events.ShowLeaderScreen(PlayerConfigurations[player:GetID()]:GetLeaderTypeName(),player:GetID()==0)
                  end
                  TestCapturedPlayerSelection=function(player)
                    Controls.LeaderAnchor:SetHide(false)
                    ShowLeader(player)
                  end
                  -- The native session sink is untouched by the art wrapper.
                  TestCapturedTrade=function(from,to) return NativeRequestSession(from,to,'MAKE_DEAL') end
                ''')
            elif name == 'LeaderScene':
                native_modules.append(name)
                lua.execute('''
                  function GenerateLayers(id,marker)
                    Native.layers=Native.layers+1;Native.layerID=id;Native.marker=marker
                  end
                  TestCapturedSceneOpened=function(id,marker) GenerateLayers(id,marker) end
                ''')
            else:
                raise AssertionError(name)

        lua.globals().include = include
        for name in ('BaiqiDiplomacyActionView', 'BaiqiLeaderScene'):
            lua.execute((ROOT / f'mod/Baiqi/UI/{name}.lua').read_text(encoding='utf-8'))
        return lua, native_modules

    def test_baiqi_keeps_native_engine_load_and_player_trade_sink(self):
        lua, _ = self.load()
        g = lua.globals()
        g.TestCapturedPlayerSelection(g.TestPlayer(1))
        self.assertEqual((g.Native.loads, g.Native.shows, g.Native.lastLeader), (1, 1, 'LEADER_BAIQI'))
        self.assertTrue(g.Native.hideAnchor)
        self.assertTrue(lua.eval('Events==OriginalEvents'))
        self.assertEqual(g.TestCapturedTrade(0, 1), (0, 1, 'MAKE_DEAL'))
        self.assertEqual(g.Native.requests, 1)

    def test_baiqi_to_ordinary_to_baiqi_restores_anchor_and_bars(self):
        lua, _ = self.load()
        g = lua.globals()
        for index, hidden in ((1, True), (2, False), (1, True), (0, False)):
            g.TestCapturedPlayerSelection(g.TestPlayer(index))
            g.TestCapturedSceneOpened(index, 'native-open')
            self.assertEqual((g.Native.hideAnchor, g.Native.top, g.Native.bottom), (hidden, hidden, hidden))
            self.assertEqual((g.Native.layerID, g.Native.marker), (index, 'native-open'))
        self.assertEqual((g.Native.shows, g.Native.layers), (4, 4))

    def test_displayed_baiqi_is_static_even_when_human_is_another_leader(self):
        lua, _ = self.load()
        g = lua.globals()
        g.TestCapturedPlayerSelection(g.TestPlayer(1))
        self.assertFalse(g.Native.self)
        self.assertTrue(g.Native.hideAnchor)
        g.TestCapturedSceneOpened(99, 'missing-config')
        self.assertEqual((g.Native.top, g.Native.bottom), (False, False))

    def test_only_most_derived_native_diplomacy_module_loads_once(self):
        for ruleset, module in (('RULESET_EXPANSION_2', 'DiplomacyActionView_Expansion2'),
                                ('RULESET_EXPANSION_1', 'DiplomacyActionView_Expansion1'),
                                ('RULESET_STANDARD', 'DiplomacyActionView')):
            with self.subTest(ruleset=ruleset):
                _, modules = self.load(ruleset)
                self.assertEqual(modules, [module, 'LeaderScene'])

    def test_empty_model_is_scoped_to_baiqi_with_no_foreign_art_packages(self):
        art = ET.parse(ROOT / 'mod/Baiqi/ArtDefs/Leaders.artdef').getroot()
        collection = art.find('./m_RootCollections/Element')
        self.assertEqual(collection.find('m_ReplaceMergedCollectionElements').text, 'false')
        entries = collection.findall('Element')
        self.assertEqual([e.find('m_Name').get('text') for e in entries], ['LEADER_BAIQI'])
        fields = {e.find('m_ParamName').get('text'): e for e in entries[0].findall('./m_Fields/m_Values/Element')}
        for name in ('Leader_BLP_Entry', 'Leader_Background_BLP_Entry', 'Leader_Lightrig_BLP_Entry'):
            self.assertEqual(fields[name].find('m_EntryName').get('text'), '')
            self.assertEqual(fields[name].find('m_BLPPackage').get('text'), '')

    def test_art_action_and_dependency_resolve_packaged_empty_model(self):
        mod = ET.parse(ROOT / 'mod/Baiqi/Baiqi.modinfo').getroot()
        self.assertEqual(mod.find('./InGameActions/UpdateArt/File').text, 'Baiqi.dep')
        dep = ET.parse(ROOT / 'mod/Baiqi/Baiqi.dep').getroot()
        self.assertEqual([e.get('text') for e in dep.findall('./SystemDependencies/Element/ConsumerName')], ['Leaders'])
        self.assertEqual([e.get('text') for e in dep.findall('./ArtDefDependencies/Element/ArtDefPath')], ['Leaders.artdef'])
        inventory = {e.text for e in mod.findall('./Files/File')}
        self.assertTrue({'Baiqi.dep', 'ArtDefs/Leaders.artdef', 'UI/BaiqiDiplomacyActionView.lua', 'UI/BaiqiLeaderScene.lua'} <= inventory)


if __name__ == '__main__':
    unittest.main()
