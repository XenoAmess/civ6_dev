"""Unknown policy inputs must explain their refusal without producing orders."""
from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime as Lua53
from test_civilian_read_unknown_diagnostics import world
from tools.build_formation_unknown_mod import transform

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
OWNER=(ROOT/'tools/lua/diagnostic_owner_unknown.lua').read_text(encoding='utf-8')
KEY='key=civilian-eligibility:4|'


def denied(kind):
    code=None
    if kind=='formation':code,_=transform(SOURCE,7,4,'UNIT_MISSIONARY',defer_start=True)
    lua,w,c,logs=world(Lua53,controller_source=code)
    api=lua.globals().P6FormationUnknown if kind=='formation'else lua.execute(OWNER)(lua.globals().BaiqiPolicy,7,4,'UNIT_MISSIONARY',64)
    assert api.Arm(7,4,'UNIT_MISSIONARY')[0]
    lua.execute("TestBeforeUnknownReligious=TestRelBridge.Copy(TestRelBridge.store['BAIQI_RELIGIOUS_INTENTS_V1'])")
    return lua,w,c,api,logs


class CivilianUnknownReasonTests(unittest.TestCase):
    def test_unknown_gate_keeps_one_policy_evaluation_per_tick(self):
        for kind in ('owner','formation'):
            with self.subTest(kind=kind):
                _,_,c,api,_=denied(kind)
                before=api.Snapshot().masked;c.RunNow()
                self.assertEqual(api.Snapshot().masked-before,1)

    def test_known_escort_is_explained_without_taking_control(self):
        _,w,c,logs=world(Lua53);w.missionaryFormation=2
        for _ in range(4):c.RunNow()
        waits=[v for v in logs if KEY in v]
        self.assertEqual(len(waits),1,logs)
        self.assertIn('护送编队或编队信息不明',waits[0])
        self.assertEqual((len(w.unitRequests),len(w.spreadRequests)),(0,0))
        self.assertEqual(w.missionaryFormation,2)

    def test_repeated_unknown_refusal_has_one_attributable_reason_and_no_unit_orders(self):
        for kind in ('owner','formation'):
            with self.subTest(kind=kind):
                lua,w,c,api,logs=denied(kind)
                for _ in range(4):c.RunNow()
                waits=[v for v in logs if KEY in v]
                self.assertEqual(len(waits),1,logs)
                self.assertIn('所有权'if kind=='owner'else'编队',waits[0])
                self.assertEqual((len(w.unitRequests),len(w.spreadRequests)),(0,0))
                self.assertEqual((w.missionaryOwner,w.missionaryMoves,w.spreadCharges,w.missionaryFormation),(7,4,3,1))
                self.assertGreater(api.Snapshot().masked,0)
                lua.execute("local function Same(a,b)if type(a)~=type(b)then return false end;if type(a)~='table'then return a==b end;for k,v in pairs(a)do if not Same(v,b[k])then return false end end;for k in pairs(b)do if a[k]==nil then return false end end;return true end;assert(Same(TestBeforeUnknownReligious,TestRelBridge.store['BAIQI_RELIGIOUS_INTENTS_V1']))")

    def test_reason_is_deduplicated_each_turn_while_refusal_remains(self):
        for kind in ('owner','formation'):
            with self.subTest(kind=kind):
                _,w,c,_,logs=denied(kind)
                for _ in range(4):c.Update(1.0)
                w.turn=2
                for _ in range(4):c.Update(1.0)
                waits=[v for v in logs if KEY in v]
                self.assertEqual(len(waits),2,logs)
                self.assertEqual(sum('turn=1|'in v for v in waits),1)
                self.assertEqual(sum('turn=2|'in v for v in waits),1)
                self.assertEqual((len(w.unitRequests),len(w.spreadRequests)),(0,0))

    def test_retiring_unknown_fault_allows_original_controller_work_without_clearing_state(self):
        for kind in ('owner','formation'):
            with self.subTest(kind=kind):
                _,w,c,api,logs=denied(kind);c.RunNow()
                self.assertEqual(len([v for v in logs if KEY in v]),1,logs)
                self.assertTrue(api.Retire()[0]);c.RunNow()
                self.assertEqual(len(w.spreadRequests),1,logs)
                self.assertEqual(len([v for v in logs if KEY in v]),1)
                self.assertIn('已登记传教士',c.GetStatus())
                self.assertFalse(any('|error|'in v for v in logs),logs)

    def test_ordinary_no_moves_does_not_gain_unknown_state_wait_spam(self):
        _,w,c,logs=world(Lua53);w.missionaryMoves=0
        for _ in range(4):c.RunNow()
        self.assertFalse(any(KEY in v for v in logs),logs)
        self.assertEqual((len(w.unitRequests),len(w.spreadRequests)),(0,0))

    def test_missing_plot_preserves_short_circuit_without_extra_policy_calls(self):
        lua,w,c,logs=world(Lua53)
        lua.execute("Map.GetPlot=function()return nil end;local original=BaiqiPolicy.CanCivilian;TestPolicyCalls=0;BaiqiPolicy.CanCivilian=function(...)TestPolicyCalls=TestPolicyCalls+1;return original(...)end")
        c.RunNow()
        self.assertEqual(lua.globals().TestPolicyCalls,0,logs)
        self.assertEqual((len(w.unitRequests),len(w.spreadRequests)),(0,0))
        self.assertFalse(any(KEY in v for v in logs),logs)


if __name__=='__main__':unittest.main()
