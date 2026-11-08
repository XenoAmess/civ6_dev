"""A pre-FOUND sensor must preserve the sole original operation and ownership."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tools/lua/diagnostic_found_warning.lua'


class FoundWarningDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
W={calls=0,senses=0}
Actor={GetID=function()return 4063259 end,GetOwner=function()return 0 end,GetUnitType=function()return 1 end}
Params={x=62,y=34}
Original=function(...)
 W.calls=W.calls+1;W.argc=select('#',...)
 if W.throw then error(W.throw)end
 local actor,operation,params=...;assert(actor==Actor and params==Params)
 if W.mutate then params.x=99 end
 if W.void then return end
 return false,nil,42,nil
end
Units={RequestOperation=Original}
O={getTable=function()return Units end,getPublished=function()return W.published end,
 publish=function(v)
  if W.denyBefore and v~=nil then error('DENIED')end
  W.published=v
  if W.denyAfter and v~=nil then error('DENIED_AFTER')end
 end,foundOperation=1463004268,
 sense=function(...)
  W.senses=W.senses+1;W.senseArgc=select('#',...)
  local actor,operation,params=...;assert(actor==Actor and params==Params)
  if W.sensorThrow then error('SENSOR')end
  return {status='CAPTURED',x=params.x,operation=operation}
 end}
''')
        self.module = self.lua.execute(SOURCE.read_text(encoding='utf-8'))
        self.g = self.lua.globals()

    def install(self):
        self.g.H = self.module.Install(self.g.O)
        return self.g.H

    def check(self, source):
        self.lua.execute(source)

    def test_snapshot_before_original_mutation_and_exact_multiple_nil_returns(self):
        h = self.install()
        self.g.W.mutate = True
        self.assertEqual(self.g.Units.RequestOperation(self.g.Actor, 1463004268, self.g.Params, None, 7), (False, None, 42, None))
        self.assertEqual((self.g.W.calls, self.g.W.argc, self.g.W.senseArgc), (1, 5, 5))
        self.assertEqual((h.samples[1].x, self.g.Params.x), (62, 99))

    def test_original_void_return_stays_zero_returns(self):
        self.install()
        self.g.W.void = True
        self.check("assert(select('#',Units.RequestOperation(Actor,1463004268,Params))==0 and W.calls==1 and W.senses==1)")

    def test_nonfound_does_not_sample_or_call_sensor(self):
        h = self.install()
        self.g.Units.RequestOperation(self.g.Actor, 1477390184, self.g.Params)
        self.assertEqual((self.g.W.calls, self.g.W.senses, len(h.samples)), (1, 0, 0))

    def test_sensor_exception_cannot_suppress_original(self):
        h = self.install()
        self.g.W.sensorThrow = True
        self.g.Units.RequestOperation(self.g.Actor, 1463004268, self.g.Params)
        self.assertEqual((self.g.W.calls, h.errors, h.samples[1].status), (1, 1, 'UNKNOWN'))

    def test_nonplain_or_missing_sensor_record_remains_unknown(self):
        for body in ('return nil', 'return false', "return setmetatable({status='FAKE'}, {})"):
            self.setUp()
            self.check('O.sense=function()'+body+' end')
            h = self.install()
            self.g.Units.RequestOperation(self.g.Actor, 1463004268, self.g.Params)
            self.assertEqual((self.g.W.calls, h.errors, h.samples[1].status), (1, 1, 'UNKNOWN'))

    def test_original_exception_object_propagates_once(self):
        self.install()
        self.check("W.throw={tag='ORIGINAL'};local ok,e=pcall(Units.RequestOperation,Actor,1463004268,Params);assert(not ok and e==W.throw and W.calls==1 and W.senses==1)")

    def test_sample_cap_drops_only_diagnostics(self):
        h = self.install()
        self.check('for i=1,17 do Units.RequestOperation(Actor,1463004268,Params)end')
        self.assertEqual((len(h.samples), h.drops, self.g.W.calls, self.g.W.senses), (16, 1, 17, 16))

    def test_foreign_binding_namespace_and_table_refused_before_restore(self):
        for change in ("Units.RequestOperation=function()end", "W.published={foreign=true}", "Units={RequestOperation=function()end}"):
            self.setUp()
            self.install()
            self.check("Saved=Units;Wrapped=Units.RequestOperation;"+change+";local expected=Units.RequestOperation;local ns=W.published;assert(not pcall(H.Restore));assert(Units.RequestOperation==expected and W.published==ns);if Units~=Saved then assert(Saved.RequestOperation==Wrapped)end")

    def test_publish_failure_before_or_after_assignment_rolls_back(self):
        for flag in ('denyBefore', 'denyAfter'):
            self.setUp()
            self.g.W[flag] = True
            self.g.M = self.module
            self.check('local ok=pcall(function()M.Install(O)end);assert(not ok and Units.RequestOperation==Original and W.published==nil)')

    def test_invalid_operation_and_occupied_namespace_never_install(self):
        self.g.M = self.module
        self.check("for _,v in ipairs({0/0,math.huge,1.5,'1463004268',false})do O.foundOperation=v;assert(not pcall(M.Install,O)and Units.RequestOperation==Original and W.published==nil)end")
        self.g.O.foundOperation = 1463004268
        self.install()
        self.check('local before=Units.RequestOperation;assert(not pcall(M.Install,O)and Units.RequestOperation==before and W.published==H)')

    def test_restore_exact_original_and_namespace(self):
        self.install()
        self.check('H.Restore();assert(Units.RequestOperation==Original and W.published==nil)')

    def test_nested_finance_recorder_restores_outer_then_inner(self):
        finance = self.lua.execute((ROOT / 'tools/lua/diagnostic_finance.lua').read_text(encoding='utf-8'))
        self.g.Finance = finance
        self.check('''
Planner={AllowRecruit=function()return true end};Cities={RequestOperation=Original}
Units.RequestCommand=Original
F=Finance.Install({getTables=function()return Planner,Cities,Units end,
 getPublished=function()return W.finance end,publish=function(v)W.finance=v end,
 unpack=unpack,game={GetCurrentGameTurn=function()return 174 end},unitRows={[1]={UnitType='UNIT_SETTLER'}}})
''')
        self.install()
        self.check('Units.RequestOperation(Actor,1463004268,Params);assert(W.calls==1 and W.senses==1 and F.counts.unit_op==1 and F.errors==0 and #F.samples==1);assert(not pcall(F.Restore));H.Restore();F.Restore();assert(Units.RequestOperation==Original and W.published==nil and W.finance==nil)')


if __name__ == '__main__':
    unittest.main()
