"""Execute the actual compatibility SQL and verify it cannot grant new effects."""
from pathlib import Path
import sqlite3
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RetiredEffectTests(unittest.TestCase):
    def test_all_legacy_ids_are_inert_with_requirements_and_no_attachment_links(self):
        with sqlite3.connect(':memory:') as db:
            db.executescript('''
              CREATE TABLE RequirementSets(RequirementSetId TEXT PRIMARY KEY,RequirementSetType TEXT);
              CREATE TABLE Requirements(RequirementId TEXT PRIMARY KEY,RequirementType TEXT);
              CREATE TABLE RequirementSetRequirements(RequirementSetId TEXT,RequirementId TEXT);
              CREATE TABLE RequirementArguments(RequirementId TEXT,Name TEXT,Value TEXT);
              CREATE TABLE Modifiers(ModifierId TEXT PRIMARY KEY,ModifierType TEXT,OwnerRequirementSetId TEXT);
              CREATE TABLE ModifierArguments(ModifierId TEXT,Name TEXT,Value TEXT);
              CREATE TABLE BuildingModifiers(BuildingType TEXT,ModifierId TEXT);
              CREATE TABLE DistrictModifiers(DistrictType TEXT,ModifierId TEXT);
            ''')
            db.executescript((ROOT / 'mod/Baiqi/Data/BaiqiRetiredEffects.sql').read_text(encoding='utf-8'))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM Modifiers').fetchone()[0], 34)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM ModifierArguments WHERE Name='Amount' AND CAST(Value AS REAL)=0").fetchone()[0], 34)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM BuildingModifiers').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM DistrictModifiers').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM Modifiers m JOIN RequirementSets r ON m.OwnerRequirementSetId=r.RequirementSetId').fetchone()[0], 34)


if __name__ == '__main__':
    unittest.main()
