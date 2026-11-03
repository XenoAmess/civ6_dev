from pathlib import Path
import json
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class PurchaseSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ('BaiqiNaturalistUnit','BaiqiNaturalistPurchaseSnapshot'):
            self.module = self.lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
          S={cityID=65536,owner=0,x=16,y=14,faith=400,
            records={{id=200,kind=19,charges=1,x=10,y=12,moves=0,formation=2},
              {id=100,kind=19,charges=1,x=11,y=12,moves=0.5,formation=1},
              {id=300,kind=19,charges=0,x=-9999,y=-9999,dead=true},
              {id=50,kind=5}}}
          GameInfo={Units={[19]={UnitType='UNIT_NATURALIST'},[5]={UnitType='UNIT_WARRIOR'}}}
          local objects={}
          for i,rec in ipairs(S.records) do
            objects[i]={GetID=function() return rec.id end,GetOwner=function() return rec.owner or 0 end,
              GetType=function() return rec.kind end,GetX=function() return rec.x end,GetY=function() return rec.y end,
              GetParkCharges=function() return rec.charges end,GetMovesRemaining=function() return rec.moves end,
              GetFormationUnitCount=function() return rec.formation end,IsDelayedDeath=function() return rec.dead==true end}
          end
          local units={Members=function() return next,objects,nil end,
            FindID=function(_,id) for _,u in pairs(objects) do if u:GetID()==id then return u end end end}
          local city={GetID=function() return S.foundID or S.cityID end,GetOwner=function() return S.owner end,
            GetX=function() return S.x end,GetY=function() return S.y end}
          local cities={FindID=function(_,id) assert(id==65536);return city end}
          local religion={GetFaithBalance=function() return S.faith end}
          Player={GetCities=function() return cities end,GetUnits=function() return units end,
            GetReligion=function() return religion end,SetProperty=function() error('forbidden write') end}
          TestUnits=units;TestObjects=objects
          UnitManager=setmetatable({},{__index=function() error('forbidden action') end})
        ''')
        self.s = self.lua.globals().S

    def read(self, pid=0, city_id=65536):
        return self.module.Read(self.lua.globals().Player, pid, city_id)

    def test_sorted_copied_core_snapshot_excludes_delayed_death(self):
        result = self.read()
        self.assertIsNotNone(result)
        self.assertEqual((result.cityID,result.owner,result.faithBalance), (65536,0,400))
        self.assertEqual([x.unitID for x in result.naturalists.values()], [100,200])
        self.assertEqual((result.naturalists[2].moves,result.naturalists[2].formation), (0,2))
        self.assertIsNone(self.lua.eval('getmetatable')(result))
        result.naturalists[1].charges = 99
        self.assertEqual(self.read().naturalists[1].charges, 1)

    def test_no_living_naturalist_is_a_valid_empty_snapshot(self):
        self.s.records[1].dead = True
        self.s.records[2].dead = True
        self.assertEqual(len(self.read().naturalists), 0)

    def test_unreadable_living_naturalist_is_not_empty_stock(self):
        for field,value in (('x',-1),('charges',float('nan')),('formation',0)):
            with self.subTest(field=field):
                self.setUp()
                self.s.records[1][field] = value
                self.assertIsNone(self.read())

    def test_member_identity_owner_and_type_fail_closed(self):
        for source in ('S.records[1].id=100','S.records[1].owner=1','S.records[1].kind=999',
                       'S.records[1].id=-1','TestObjects[1].IsDelayedDeath=nil'):
            with self.subTest(source=source):
                self.setUp()
                self.lua.execute(source)
                self.assertIsNone(self.read())

    def test_city_or_faith_change_during_members_invalidates_snapshot(self):
        for change in ('S.faith=399','S.owner=1','S.foundID=131072','S.x=17'):
            with self.subTest(change=change):
                self.setUp()
                self.lua.execute('''
                  TestUnits.Members=function()
                    return function() '''+change+''' end
                  end
                ''')
                self.assertIsNone(self.read())

    def test_bad_arguments_and_missing_or_throwing_providers(self):
        for value in (True,-1,0.5,2147483648,float('inf')):
            self.assertIsNone(self.read(pid=value))
            self.assertIsNone(self.read(city_id=value))
        for source in ("Player.GetReligion=nil", "TestUnits.Members=function() error('members') end",
                       "GameInfo.Units=setmetatable({},{__index=function() error('row') end})"):
            with self.subTest(source=source):
                self.setUp()
                self.lua.execute(source)
                self.assertIsNone(self.read())

    def test_member_and_living_naturalist_caps(self):
        self.lua.execute('''
          TestUnits.Members=function()
            local i=0
            return function()
              i=i+1;if i>4097 then return end
              return i,{GetID=function() return i end,GetOwner=function() return 0 end,GetType=function() return 5 end}
            end
          end
        ''')
        self.assertIsNone(self.read())
        self.setUp()
        self.lua.execute('''
          local objects={}
          for i=1,257 do
            local id=5000000+i
            objects[id]={GetID=function() return id end,GetOwner=function() return 0 end,
              GetType=function() return 19 end,GetX=function() return 16 end,GetY=function() return 14 end,
              GetParkCharges=function() return 1 end,GetMovesRemaining=function() return 0 end,
              GetFormationUnitCount=function() return 1 end,IsDelayedDeath=function() return false end}
          end
          TestUnits.Members=function() return next,objects,nil end
          TestUnits.FindID=function(_,id) return objects[id] end
        ''')
        self.assertIsNone(self.read())


class PurchaseJournalTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.j = self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiNaturalistPurchaseJournal.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
          function Armed()
            return {version=1,owner=0,serial=1,operations={['1']={token='purchase:0:1',sequence=1,
              cityID=65536,unitType='UNIT_NATURALIST',unitHash=1877270220,x=16,y=14,cost=300,
              faithBefore=400,reserve=100,turn=92,stage='ARMED',baselineUnitIDs={10,20}}}}
          end
        ''')

    def table(self, value):
        if isinstance(value, dict):
            return self.lua.table_from({k:self.table(v) for k,v in value.items()})
        if isinstance(value, list):
            return self.lua.table_from([self.table(v) for v in value])
        return value

    def test_model_data_against_actual_validator(self):
        data = json.loads((ROOT / 'tests/fixtures/naturalist_purchase_journal_cases.json').read_text(encoding='utf-8'))
        for case in data['cases']:
            with self.subTest(case=case['name']):
                self.assertEqual(self.j.Validate(self.table(case['state']),0), case['valid'])

    def test_serial_bounds_and_exact_operation_fields(self):
        for change in ("s.serial=0", "s.operations['1'].unexpected=true", "s.operations['1'].baselineUnitIDs.extra=1"):
            state = self.lua.eval('Armed')()
            self.lua.globals().s = state
            self.lua.execute(change)
            self.assertFalse(self.j.Validate(state,0))

    def test_baseline_validation_is_independent_of_pairs_order(self):
        self.lua.execute('s=Armed();s.operations["1"].baselineUnitIDs={'+','.join(f'[{i}]={i}' for i in range(1,33))+'}')
        self.assertTrue(self.j.Validate(self.lua.globals().s,0))
        for literal in ('{[1]=10,[3]=30}','{20,10}','{10,10}','{[0]=0,[1]=10}'):
            self.lua.execute('s=Armed();s.operations["1"].baselineUnitIDs='+literal)
            self.assertFalse(self.j.Validate(self.lua.globals().s,0))

    def test_clone_is_deep_and_equal_checks_real_fields(self):
        state = self.lua.eval('Armed')()
        copy = self.j.Clone(state,0)
        self.assertTrue(self.j.Equal(state,copy,0))
        copy.operations['1'].baselineUnitIDs[1] = 11
        self.assertEqual(state.operations['1'].baselineUnitIDs[1], 10)
        self.assertFalse(self.j.Equal(state,copy,0))
        copy = self.j.Clone(state,0)
        copy.operations['1'].cost = 299
        self.assertFalse(self.j.Equal(state,copy,0))

    def test_unknown_metatables_and_numeric_failures(self):
        for change in ("setmetatable(s,{})", "setmetatable(s.operations['1'].baselineUnitIDs,{})",
                       "s.operations['1'].cost=0/0", "s.operations['1'].faithBefore=math.huge",
                       "s.operations['1'].unitHash=4294967296", "s.operations['1'].newUnitID=2"):
            self.lua.execute('s=Armed();'+change)
            state = self.lua.globals().s
            self.assertFalse(self.j.Validate(state,0))
            self.assertIsNone(self.j.Clone(state,0))

    def test_new_key_token_boundaries(self):
        self.assertEqual(self.j.Token(0,2147483647), 'purchase:0:2147483647')
        self.assertEqual(self.j.Key(2147483647), '2147483647')
        self.assertTrue(self.j.Validate(self.j.New(0),0))
        for value in (True,-1,0.5,float('nan'),float('inf'),2147483648):
            self.assertIsNone(self.j.New(value))
            self.assertIsNone(self.j.Token(value,1))
            self.assertIsNone(self.j.Key(value))
        self.assertIsNone(self.j.Key(0))

    def test_observed_requires_new_unit_and_exact_faith_debit(self):
        self.lua.execute("s=Armed();s.operations['1'].stage='OBSERVED';s.operations['1'].newUnitID=30;s.operations['1'].faithAfter=100")
        state = self.lua.globals().s
        self.assertTrue(self.j.Validate(state,0))
        state.operations['1'].newUnitID = 10
        self.assertFalse(self.j.Validate(state,0))
        state.operations['1'].newUnitID = 30
        state.operations['1'].faithAfter = 101
        self.assertFalse(self.j.Validate(state,0))


if __name__ == '__main__':
    unittest.main()
