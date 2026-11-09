"""Synthetic native include contracts, using actual Baiqi loader and UI guards."""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class GreatPeopleLoaderTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.calls=[]
        self.lua.execute('''
W={ruleset='RULESET_EXPANSION_2',leader='LEADER_BAIQI',human=true,congress=false,
 baseLoads=0,xp1=0,xp2=0,registered=0,opened=0,writes=0}
Game={GetLocalPlayer=function()return 0 end,GetWorldCongress=function()return {IsInSession=function()return W.congress end}end}
GameConfiguration={GetValue=function(k)assert(k=='RULESET');return W.ruleset end,
 IsAnyMultiplayer=function()return W.multiplayer==true end,IsHotseat=function()return W.hotseat==true end}
PlayerConfigurations={[0]={GetLeaderTypeName=function()return W.leader end,IsHuman=function()return W.human end}}
Players={[0]={GetCulture=function()return {}end}}
PlayerOperations={EXECUTE_SCRIPT=1,PATRONIZE_GREAT_PERSON=2,RECRUIT_GREAT_PERSON=3,DIPLOMACY_MAKE_PEACE=4,LEVY_MILITARY=5}
UI={RequestPlayerOperation=function()W.writes=W.writes+1;return true end}
UnitManager={};CityManager={};UnitCommandTypes={};CityCommandTypes={}
LaunchHandlers={}
function FireLaunch()for _,f in ipairs(LaunchHandlers)do f()end end
''')
        self.lua.globals().include=self.include
        self.w=self.lua.globals().W

    def include(self,name,wildcard=False):
        self.calls.append((name,bool(wildcard)))
        if name in ('BaiqiConfig','BaiqiPolicy','BaiqiUIGuard','BaiqiUILoader','BaiqiGPViewData','BaiqiGPViewport'):
            path=ROOT/f'mod/Baiqi/Lua/{name}.lua'
            if name=='BaiqiUILoader' and os.environ.get('BAIQI_GP_LOADER_SOURCE'):
                path=Path(os.environ['BAIQI_GP_LOADER_SOURCE'])
            self.lua.execute(path.read_text(encoding='utf-8'))
        elif name=='GreatPeoplePopup' and not wildcard:
            self.lua.execute('''
W.baseLoads=W.baseLoads+1
assert(W.baseLoads==1,'duplicate base initialization in one context')
function OnOpenViaLaunchBar()W.opened=W.opened+1 end
function IsReadOnly()return false end
LaunchHandlers[#LaunchHandlers+1]=OnOpenViaLaunchBar;W.registered=W.registered+1
function TestPatronage()return UI.RequestPlayerOperation(0,PlayerOperations.PATRONIZE_GREAT_PERSON,{})end
function TestRecruitment()return UI.RequestPlayerOperation(0,PlayerOperations.RECRUIT_GREAT_PERSON,{})end
include('GreatPeoplePopup_',true)
''')
        elif name=='GreatPeoplePopup_' and wildcard:
            if self.w.ruleset in ('RULESET_EXPANSION_1','RULESET_EXPANSION_2'):
                self.include('GreatPeoplePopup_Expansion1')
            if self.w.ruleset=='RULESET_EXPANSION_2':
                self.include('GreatPeoplePopup_Expansion2')
        elif name=='GreatPeoplePopup_Expansion1':
            self.lua.execute("assert(type(OnOpenViaLaunchBar)=='function','XP1 is an extension, not a parent loader');W.xp1=W.xp1+1")
        elif name=='GreatPeoplePopup_Expansion2':
            self.lua.execute("assert(type(OnOpenViaLaunchBar)=='function','XP2 is an extension, not a parent loader');W.xp2=W.xp2+1;function IsReadOnly()return Game.GetWorldCongress():IsInSession()end")
        # Other UI replacements keep their existing parent-include contract.

    def load(self):
        self.lua.execute((ROOT/'mod/Baiqi/UI/BaiqiGreatPeoplePopup.lua').read_text(encoding='utf-8'))

    def test_base_and_installed_extensions_load_in_all_three_rulesets(self):
        for ruleset,expected in (('RULESET_STANDARD',(0,0)),('RULESET_EXPANSION_1',(1,0)),('RULESET_EXPANSION_2',(1,1))):
            with self.subTest(ruleset=ruleset):
                self.setUp();self.w.ruleset=ruleset;self.load()
                self.assertEqual((self.w.baseLoads,self.w.xp1,self.w.xp2),(1,*expected))
                self.assertEqual(self.w.registered,1)

    def test_original_view_event_is_present_and_opens_without_a_game_order(self):
        self.load();self.lua.globals().FireLaunch()
        self.assertEqual(self.w.opened,1);self.assertEqual(self.w.writes,0)

    def test_baiqi_remains_readonly_with_original_handlers_loaded(self):
        for ruleset in ('RULESET_STANDARD','RULESET_EXPANSION_1','RULESET_EXPANSION_2'):
            with self.subTest(ruleset=ruleset):
                self.setUp();self.w.ruleset=ruleset;self.load()
                self.assertTrue(self.lua.globals().IsReadOnly())
                self.assertFalse(self.lua.globals().TestPatronage())
                self.assertFalse(self.lua.globals().TestRecruitment())
                self.assertEqual(self.w.writes,0)

    def test_normal_leader_keeps_native_readonly_and_write_behavior(self):
        self.w.leader='LEADER_TRAJAN';self.load()
        self.assertFalse(self.lua.globals().IsReadOnly())
        self.assertTrue(self.lua.globals().TestPatronage())
        self.assertTrue(self.lua.globals().TestRecruitment())
        self.assertEqual(self.w.writes,2)

    def test_congress_readonly_remains_after_extension_and_baiqi_wrapper(self):
        self.w.leader='LEADER_TRAJAN';self.w.congress=True;self.load()
        self.assertTrue(self.lua.globals().IsReadOnly())
        self.w.congress=False;self.assertFalse(self.lua.globals().IsReadOnly())
        self.w.leader='LEADER_BAIQI';self.assertTrue(self.lua.globals().IsReadOnly())

    def test_nonhuman_multiplayer_hotseat_keep_existing_scope(self):
        for key,value in (('human',False),('multiplayer',True),('hotseat',True)):
            with self.subTest(key=key):
                self.setUp();self.w[key]=value;self.load()
                self.assertFalse(self.lua.globals().IsReadOnly())

    def test_other_ui_replacement_selection_is_unchanged(self):
        self.load();self.lua.globals().BaiqiUILoader.Load('CityPanel')
        self.lua.globals().BaiqiUILoader.Load('DiplomacyActionView')
        self.assertIn(('CityPanel_Expansion2',False),self.calls)
        self.assertIn(('DiplomacyActionView_Expansion2',False),self.calls)

    def test_one_wrapper_initializes_base_and_events_exactly_once(self):
        self.load()
        self.assertEqual(self.calls.count(('GreatPeoplePopup',False)),1)
        self.assertEqual(self.calls.count(('GreatPeoplePopup_',True)),1)
        self.assertEqual((self.w.baseLoads,self.w.registered,self.w.xp1,self.w.xp2),(1,1,1,1))


if __name__=='__main__':
    unittest.main()
