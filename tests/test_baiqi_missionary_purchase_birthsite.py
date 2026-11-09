import unittest
from missionary_purchase_holy_fixture import make
from missionary_purchase_core_harness import KEY,make_missionary_core


class MissionaryBirthsiteTests(unittest.TestCase):
    def setUp(self):
        self.lua=make();g=self.lua.globals();self.h=g.H;self.b=g.B;self.bridge=g.ExposedMembers.BaiqiMissionaryPurchaseBridge

    def prepare(self):
        self.assertTrue(self.bridge.Prepare(0,65536,16,14,-199,4,75,175,100)[0])

    def op(self):return self.h.store[KEY].operations['1']

    def test_exact_city_holy_site_birth_uses_core_getdistrict_without_members(self):
        self.prepare();self.lua.execute('HolyEffect()')
        self.assertEqual(self.bridge.Inspect(0)[0],'OPEN')
        self.assertEqual((self.op().stage,self.op().newUnitID,self.op().faithAfter),('OBSERVED',6000000,100))

    def test_city_center_path_remains_valid_without_holy_site_ports(self):
        self.prepare();self.lua.execute('City.GetDistricts=nil;Map=nil;H.Add(6000000);S.faith=100')
        self.assertEqual(self.bridge.Inspect(0)[0],'OPEN')

    def test_unknown_foreign_or_unqualified_holy_site_never_confirms(self):
        for change in ('B.owner=1','B.type=1','B.cityOwner=1','B.complete=false','B.complete=1','B.pillaged=true','B.pillaged=nil','B.absent=true','B.throw=true'):
            with self.subTest(change=change):
                self.setUp();self.prepare();self.lua.execute('HolyEffect();'+change)
                self.assertNotEqual(self.bridge.Inspect(0)[0],'OPEN');self.assertEqual((self.op().stage,self.h.writes),('ARMED',1))

    def test_other_city_or_plot_district_identity_cannot_match(self):
        for change in ('B.cityID=65537','B.plotID=1','B.plotOwner=1','B.plotType=1'):
            with self.subTest(change=change):
                self.setUp();self.prepare();self.lua.execute('HolyEffect();'+change)
                self.assertEqual(self.bridge.Inspect(0)[0],'ARMED')

    def test_city_center_identity_drift_preserves_original_guard(self):
        self.prepare();self.lua.execute('H.Add(6000000);S.faith=100;S.x=17')
        self.assertEqual(self.bridge.Inspect(0)[0],'ARMED')

    def test_final_faith_change_after_second_snapshot_prevents_receipt(self):
        self.prepare();self.lua.execute('''
HolyEffect();local read=BaiqiMissionaryPurchaseSnapshot.Read;local n=0
BaiqiMissionaryPurchaseSnapshot.Read=function(...)n=n+1;local s=read(...);if n==2 then S.faith=101 end;return s end
''')
        self.assertEqual(self.bridge.Inspect(0)[0],'ARMED');self.assertEqual(self.h.writes,1)

    def test_unit_moved_during_site_recheck_prevents_receipt(self):
        self.prepare();self.lua.execute('HolyEffect();B.onCity=function()if B.cityReads>=2 then H.newUnit.x=14 end end')
        self.assertEqual(self.bridge.Inspect(0)[0],'ARMED');self.assertEqual(self.h.writes,1)

    def test_repeated_inspection_and_saved_armed_state_do_not_repurchase(self):
        self.prepare();saved=self.h.Copy(self.h.store)
        # A reload is a fresh Lua VM; only persisted permission crosses it.
        import os
        from pathlib import Path
        src=Path(os.environ['BAIQI_BIRTH_INTENT']).read_text(encoding='utf-8') if os.environ.get('BAIQI_BIRTH_INTENT') else None
        lua=make_missionary_core(stored=saved,source=src)
        from missionary_purchase_holy_fixture import FIXTURE
        lua.execute(FIXTURE);lua.execute('HolyEffect()');bridge=lua.globals().ExposedMembers.BaiqiMissionaryPurchaseBridge
        self.assertEqual(bridge.Inspect(0)[0],'OPEN');writes=lua.globals().H.writes
        self.assertEqual(bridge.Inspect(0)[0],'OPEN');self.assertEqual(writes,1);self.assertEqual(lua.globals().H.writes,writes)
        self.assertEqual(lua.globals().H.store[KEY].operations['1'].stage,'OBSERVED')


if __name__=='__main__':unittest.main()
