"""Finance diagnostics must preserve the calls they observe and restore ownership."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime, LuaError

ROOT = Path(__file__).resolve().parents[1]


class FinanceDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
_G=nil
W={calls=0,turn=114}
S={gold=0,netGold=35,cities=11,cityPopulation=9,builders=3,queuedBuilders=3,
 settlers=1,queuedSettlers=0,reservedSettlers=0,traders=11,queuedTraders=0,
 tradeCapacity=11,army=30,queuedArmy=0,maintenance=0,committedMaintenance=2,
 resourceAffordable=true,archaeologistDemand=false}
C={goldReserve=100,netGoldMin=2,buildersPerCity=.5,maxSettlers=1,settlerMinPop=4,armyPerCity=2}
Planner={AllowRecruit=function(...)
 W.calls=W.calls+1;W.argc=select('#',...)
 if W.throw then error('ORIGINAL_FAILURE') end
 if W.mutate then local role,state=...;state.gold=900 end
 return false,nil,42,nil
end}
Native=function(...)
 W.calls=W.calls+1;W.argc=select('#',...)
 if W.throw then error('ORIGINAL_FAILURE') end
 if W.mutate then local actor,op,params=...;params[14]=99 end
 return 'native',nil,9,nil
end
Cities={RequestOperation=Native};Units={RequestOperation=Native,RequestCommand=Native}
Actor={GetID=function()return 5 end,GetOwner=function()return 0 end,GetUnitType=function()return 1 end}
O={getTables=function()return Planner,Cities,Units end,
 getPublished=function()return W.published end,
 publish=function(v)if W.denyPublish and v~=nil then error('PUBLISH_DENIED')end;W.published=v end,
 unpack=table.unpack,game={GetCurrentGameTurn=function()return W.turn end},
 unitRows={[1]={UnitType='UNIT_BUILDER'}}}
OriginalRecruit=Planner.AllowRecruit
''')
        self.module = self.lua.execute((ROOT / 'tools/lua/diagnostic_finance.lua').read_text(encoding='utf-8'))
        self.g = self.lua.globals()

    def install(self):
        return self.module.Install(self.g.O)

    def test_snapshot_precedes_mutation_and_false_multiple_nil_returns_survive(self):
        s = self.install()
        self.g.W.mutate = True
        result = self.g.Planner.AllowRecruit('builder', self.g.S, self.g.C, None)
        self.assertEqual(result, (False, None, 42, None))
        self.assertEqual((self.g.W.calls, self.g.W.argc, s.counts.recruit), (1, 4, 1))
        self.assertEqual((s.samples[1].state.gold, self.g.S.gold), (0, 900))
        self.assertFalse(s.samples[1].allowed)
        self.assertEqual(s.samples[1].returnCount, 4)

    def test_native_parameters_are_copied_and_real_receiver_varargs_forwarded(self):
        s = self.install()
        params = self.lua.table_from({14: 11, 15: 12})
        self.g.W.mutate = True
        self.assertEqual(self.g.Units.RequestOperation(self.g.Actor, 10, params, None, 7), ('native', None, 9, None))
        self.assertEqual((self.g.W.calls, self.g.W.argc), (1, 5))
        self.assertEqual((s.samples[1].params[14], params[14]), (11, 99))
        self.assertEqual((s.samples[1].actorID, s.samples[1].unitType), (5, 'UNIT_BUILDER'))

    def test_sensor_failure_does_not_change_original_call(self):
        s = self.install()
        self.assertEqual(self.g.Units.RequestCommand(self.lua.table(), 12), ('native', None, 9, None))
        self.assertEqual((s.errors, self.g.W.calls), (1, 1))

    def test_native_userdata_catalog_is_read_without_table_assumption(self):
        row = self.lua.table_from({'UnitType': 'UNIT_BUILDER'})

        class Catalog:
            def __getitem__(self, index):
                return row if index == 1 else None

        catalog = Catalog()
        self.assertEqual(self.lua.eval('type')(catalog), 'userdata')
        self.g.O.unitRows = catalog
        s = self.install()
        self.assertEqual(self.g.Units.RequestOperation(self.g.Actor, 10), ('native', None, 9, None))
        self.assertEqual((s.errors, s.samples[1].unitType), (0, 'UNIT_BUILDER'))
        s.Restore()

    def test_unknown_budget_field_remains_unknown_and_marks_incomplete(self):
        s = self.install()
        self.g.S.gold = None
        self.g.Planner.AllowRecruit('builder', self.g.S, self.g.C)
        self.assertEqual(s.errors, 1)
        self.assertIsNone(s.samples[1].state.gold)
        self.assertEqual(s.samples[1].unknownFields[1], 'state.gold')

    def test_original_exception_propagates_once(self):
        s = self.install()
        self.g.W.throw = True
        with self.assertRaisesRegex(LuaError, 'ORIGINAL_FAILURE'):
            self.g.Planner.AllowRecruit('builder', self.g.S, self.g.C)
        self.assertEqual(self.g.W.calls, 1)
        self.assertFalse(s.samples[1].returned)

    def test_global_cap_drops_only_evidence_and_continues_every_original(self):
        s = self.install()
        self.lua.execute('for i=1,4097 do Planner.AllowRecruit("builder",S,C)end')
        self.assertEqual((len(s.samples), s.drops, self.g.W.calls), (4096, 1, 4097))

    def test_foreign_binding_or_table_aborts_before_any_partial_restore(self):
        s = self.install()
        self.lua.execute('Units.RequestCommand=function()end;Foreign=Units.RequestCommand')
        with self.assertRaisesRegex(LuaError, 'Foreign binding'):
            s.Restore()
        self.assertTrue(self.lua.eval('Planner.AllowRecruit==W.published.entries[1].wrapper and Units.RequestCommand==Foreign'))
        self.setUp()
        s = self.install()
        self.lua.execute('Cities={RequestOperation=function()end}')
        with self.assertRaisesRegex(LuaError, 'Foreign API table'):
            s.Restore()
        self.assertTrue(self.lua.eval('Planner.AllowRecruit==W.published.entries[1].wrapper'))

    def test_publication_failure_rolls_back_all_bindings(self):
        self.g.W.denyPublish = True
        with self.assertRaisesRegex(LuaError, 'PUBLISH_DENIED'):
            self.install()
        self.assertTrue(self.lua.eval('W.published==nil and Planner.AllowRecruit==OriginalRecruit and Cities.RequestOperation==Native and Units.RequestOperation==Native and Units.RequestCommand==Native'))

    def test_reentry_rejected_then_owned_cleanup_restores_exact_functions(self):
        s = self.install()
        with self.assertRaisesRegex(LuaError, 'namespace occupied'):
            self.install()
        s.Restore()
        self.assertTrue(self.lua.eval('W.published==nil and Planner.AllowRecruit==OriginalRecruit and Cities.RequestOperation==Native and Units.RequestOperation==Native and Units.RequestCommand==Native'))


if __name__ == '__main__':
    unittest.main()
