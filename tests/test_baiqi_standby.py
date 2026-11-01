"""A normal no-reward project fills otherwise stranded production without cap bypass."""
from pathlib import Path
import sqlite3
import unittest
import xml.etree.ElementTree as ET
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class StandbyTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_trade.lua',
                     'tests/lua/mock_military.lua', 'tests/lua/mock_standby.lua',
                     'mod/Baiqi/Lua/BaiqiConfig.lua', 'mod/Baiqi/Lua/BaiqiPolicy.lua',
                     'mod/Baiqi/Lua/BaiqiPlanner.lua', 'mod/Baiqi/Lua/BaiqiController.lua'):
            self.lua.execute((ROOT/name).read_text(encoding='utf-8'))
        self.w, self.c = self.lua.globals().TestWorld, self.lua.globals().BaiqiController

    def test_full_army_uses_normal_standby_packet_without_extra_recruitment_or_army_orders(self):
        self.c.RunNow()
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 2)
        for request in self.w.cityRequests.values():
            self.assertEqual((request.op, request.params[5], request.params[6]), (1, 302, 7))
            self.assertIsNone(request.params[4])
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_available_normal_unit_or_project_outranks_standby(self):
        self.lua.execute('TestWorld.armyTypes={}')
        self.c.RunNow()
        self.assertEqual(self.w.cityRequests[1].params[4], 206)
        self.setUp()
        self.w.allowProject = True
        self.c.RunNow()
        self.assertEqual(self.w.cityRequests[1].params[5], 301)

    def test_native_standby_rejection_and_other_leader_do_not_receive_forged_work(self):
        self.w.rejectStandby = True
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)
        self.w.rejectStandby = False
        self.lua.execute("PlayerConfigurations[7].GetLeaderTypeName=function() return 'LEADER_TRAJAN' end")
        self.c.RunNow()
        self.assertEqual(len(self.w.cityRequests), 0)

    def test_pending_needs_real_project_queue_then_native_completion_allows_next_cycle(self):
        logs = []
        self.lua.globals().print = lambda *args: logs.append(' '.join(map(str, args)))
        self.c.RunNow()
        self.assertFalse(any('queue_observed' in line for line in logs))
        self.lua.execute('TestWorld.queues[66]={{ProjectType=1}}')
        self.c.RunNow()
        self.assertEqual(sum('queue_observed' in line for line in logs), 1)
        self.assertEqual(len(self.w.cityRequests), 2)
        # An actual native completion is represented by removing its queue item;
        # this does not pretend that a queue acknowledgement proves completion.
        self.lua.execute('TestWorld.queues[66]={};TestWorld.turn=2')
        self.c.RunNow()
        self.assertEqual((len(self.w.cityRequests), self.w.cityRequests[3].city, self.w.cityRequests[3].params[5]), (3, 66, 302))

    def test_actual_sql_links_only_baiqi_trait_and_has_normal_cost_without_rewards(self):
        with sqlite3.connect(':memory:') as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.executescript('''
CREATE TABLE Types(Type TEXT PRIMARY KEY,Kind TEXT);
CREATE TABLE Districts(DistrictType TEXT PRIMARY KEY);
INSERT INTO Districts VALUES('DISTRICT_CITY_CENTER');
CREATE TABLE Traits(TraitType TEXT PRIMARY KEY);
INSERT INTO Traits VALUES('TRAIT_LEADER_BAIQI_FORERUNNER'),('TRAIT_OTHER');
CREATE TABLE Projects(ProjectType TEXT PRIMARY KEY REFERENCES Types(Type),Name TEXT NOT NULL,
 ShortName TEXT NOT NULL,Description TEXT,Cost INTEGER NOT NULL,PrereqDistrict TEXT REFERENCES Districts(DistrictType),
 UnlocksFromEffect INTEGER NOT NULL DEFAULT 0,AdvisorType TEXT,CostProgressionModel TEXT NOT NULL DEFAULT 'NO_PROGRESSION_MODEL');
CREATE TABLE DynamicModifiers(ModifierType TEXT PRIMARY KEY REFERENCES Types(Type),CollectionType TEXT,EffectType TEXT);
CREATE TABLE Modifiers(ModifierId TEXT PRIMARY KEY,ModifierType TEXT REFERENCES DynamicModifiers(ModifierType));
CREATE TABLE ModifierArguments(ModifierId TEXT REFERENCES Modifiers(ModifierId),Name TEXT,Value TEXT);
CREATE TABLE TraitModifiers(TraitType TEXT REFERENCES Traits(TraitType),ModifierId TEXT REFERENCES Modifiers(ModifierId));
CREATE TABLE Project_YieldConversions(ProjectType TEXT,YieldType TEXT,PercentOfProductionRate INTEGER);
CREATE TABLE Project_GreatPersonPoints(ProjectType TEXT,GreatPersonClassType TEXT,Points INTEGER);
CREATE TABLE ProjectCompletionModifiers(ProjectType TEXT,ModifierId TEXT);
''')
            db.executescript((ROOT/'mod/Baiqi/Data/BaiqiStandby.sql').read_text(encoding='utf-8'))
            self.assertEqual(db.execute('SELECT Cost,PrereqDistrict,UnlocksFromEffect,CostProgressionModel FROM Projects').fetchone(),
                             (30, 'DISTRICT_CITY_CENTER', 1, 'NO_PROGRESSION_MODEL'))
            self.assertEqual(db.execute('SELECT TraitType FROM TraitModifiers').fetchall(), [('TRAIT_LEADER_BAIQI_FORERUNNER',)])
            self.assertEqual(db.execute('SELECT EffectType FROM DynamicModifiers').fetchone()[0], 'EFFECT_ADD_PLAYER_PROJECT_AVAILABILITY')
            self.assertEqual(db.execute('SELECT Value FROM ModifierArguments WHERE Name=\'ProjectType\'').fetchone()[0], 'PROJECT_BAIQI_STANDBY')
            for table in ('Project_YieldConversions', 'Project_GreatPersonPoints', 'ProjectCompletionModifiers'):
                self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0], 0)
            text = ET.parse(ROOT/'mod/Baiqi/Text/BaiqiText.xml').getroot()
            translations = {(row.get('Tag'), row.get('Language')) for row in text.findall('./LocalizedText/Row')}
            for key in db.execute('SELECT Name,ShortName,Description FROM Projects').fetchone():
                for language in ('zh_Hans_CN', 'en_US'):
                    self.assertIn((key, language), translations)

    def test_project_icon_references_existing_installed_atlas(self):
        with sqlite3.connect(':memory:') as db:
            db.executescript('''
CREATE TABLE IconDefinitions(Name TEXT PRIMARY KEY,Atlas TEXT,"Index" INTEGER);
INSERT INTO IconDefinitions VALUES('ICON_CIVILIZATION_CHINA','NATIVE_CIV_ATLAS',1),
 ('ICON_PROJECT_ENHANCE_DISTRICT_ENCAMPMENT','NATIVE_PROJECT_ATLAS',2);
''')
            db.executescript((ROOT/'mod/Baiqi/Data/BaiqiIcons.sql').read_text(encoding='utf-8'))
            self.assertEqual(db.execute('SELECT Atlas,"Index" FROM IconDefinitions WHERE Name=\'ICON_PROJECT_BAIQI_STANDBY\'').fetchone(),
                             ('NATIVE_PROJECT_ATLAS', 2))


if __name__ == '__main__':
    unittest.main()
