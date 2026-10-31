"""Exercise shipped Lua sources, including negative control and cost boundaries."""
from pathlib import Path
import unittest

from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class BaiqiPlannerTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        for name in ("BaiqiConfig", "BaiqiPolicy", "BaiqiPlanner"):
            self.lua.execute((ROOT / f"mod/Baiqi/Lua/{name}.lua").read_text(encoding="utf-8"))
        self.policy, self.planner = self.lua.globals().BaiqiPolicy, self.lua.globals().BaiqiPlanner
        self.config = self.lua.globals().BaiqiConfig

    def table(self, **fields):
        return self.lua.table_from(fields)

    def test_nonzero_local_player_and_unknown_context(self):
        ctx = self.table(isBaiqi=True, activeTurn=True, enabled=True, player=7, localPlayer=7)
        self.assertTrue(self.policy.Context(ctx))
        for field in ("isBaiqi", "activeTurn", "enabled", "localPlayer", "player"):
            old = ctx[field]
            for bad in (None, "true", False):
                ctx[field] = bad
                self.assertFalse(self.policy.Context(ctx), (field, bad))
            ctx[field] = old
        ctx.localPlayer = 0
        self.assertFalse(self.policy.Context(ctx))

    def test_unit_control_denies_military_foreign_formation_and_unknown(self):
        ctx = self.table(isBaiqi=True, activeTurn=True, enabled=True, player=7, localPlayer=7)
        unit = self.table(owner=7, type="UNIT_SETTLER", paused=False, formationCount=1, moves=2)
        self.assertTrue(self.policy.CanCivilian(ctx, unit)[0])
        for field, values in {"owner": [0, None], "type": ["UNIT_WARRIOR", "UNIT_SCOUT", "UNIT_SPY"],
                              "formationCount": [2, 0, None],
                              "moves": [0, -1, None, float("nan"), float("inf")]}.items():
            old = unit[field]
            for value in values:
                unit[field] = value
                self.assertFalse(self.policy.CanCivilian(ctx, unit)[0], (field, value))
            unit[field] = old
        unit.paused = True
        self.assertTrue(self.policy.CanCivilian(ctx, unit)[0])
        for kind in ("UNIT_WARRIOR", "UNIT_SCOUT", "UNIT_SPY", "UNIT_GREAT_GENERAL"):
            for action in ("MOVE_TO", "FOUND_CITY", "BUILD_IMPROVEMENT", "REPAIR", "RANGE_ATTACK"):
                self.assertFalse(self.policy.ActionAllowed(kind, action))
        self.assertTrue(self.policy.ActionAllowed("UNIT_BUILDER", "REPAIR"))
        self.assertFalse(self.policy.ActionAllowed("UNIT_SETTLER", "REPAIR"))

    def test_manual_queue_repair_priority_and_finite_scores(self):
        city = self.table(paused=False, queueEmpty=True)
        candidates = self.lua.table_from([
            self.table(index=1, score=900, legal=False),
            self.table(index=2, score=40, legal=True, repair=True),
            self.table(index=3, score=100, legal=True),
            self.table(index=4, score=float("inf"), legal=True),
        ])
        self.assertEqual(self.planner.Choose(city, candidates).index, 2)
        self.assertEqual(candidates[2].score, 40)
        city.queueEmpty = False
        self.assertIsNone(self.planner.Choose(city, candidates))
        city.queueEmpty, city.paused = True, None
        self.assertIsNone(self.planner.Choose(city, candidates))

    def test_recruit_budget_counts_queued_maintenance_and_units(self):
        state = self.table(gold=100, netGold=6, cities=2, maintenance=1, committedMaintenance=3,
                           army=0, queuedArmy=0, resourceAffordable=True)
        self.assertTrue(self.planner.AllowRecruit("military", state, self.config))
        state.committedMaintenance = 4
        self.assertFalse(self.planner.AllowRecruit("military", state, self.config))
        state.committedMaintenance, state.queuedArmy = 0, 4
        self.assertFalse(self.planner.AllowRecruit("military", state, self.config))
        state.queuedArmy, state.resourceAffordable = 0, None
        self.assertFalse(self.planner.AllowRecruit("military", state, self.config))

    def test_settler_population_site_and_duplicate_production(self):
        state = self.table(gold=100, netGold=5, cities=1, maintenance=0, committedMaintenance=0,
                           cityPopulation=4, resourceAffordable=True, hasSafeSite=True,
                           settlers=0, queuedSettlers=0, reservedSettlers=0)
        self.assertTrue(self.planner.AllowRecruit("settler", state, self.config))
        for field, bad in (("cityPopulation", 3), ("hasSafeSite", False), ("settlers", 1),
                           ("queuedSettlers", 1), ("reservedSettlers", 1), ("gold", 99)):
            old, state[field] = state[field], bad
            self.assertFalse(self.planner.AllowRecruit("settler", state, self.config), field)
            state[field] = old

    def test_protected_sites_reservations_and_deterministic_ties(self):
        sites = self.lua.table_from([self.table(index=i, score=50, legal=True, revealed=True,
                                                safe=True, protected=False) for i in (9, 5)])
        reservations = self.lua.table_from({5: 12})
        self.assertEqual(self.planner.Site(sites, reservations, 11).index, 9)
        self.assertEqual(self.planner.Site(sites, reservations, 12).index, 5)
        sites[2].protected, sites[1].revealed = True, None
        self.assertIsNone(self.planner.Site(sites, reservations, 12))

    def test_paid_journal_unknown_cannot_replay_and_requires_causal_proof(self):
        transition = self.planner.Transition
        self.assertEqual(transition("QUOTED", "SUBMIT", self.table(confirmed=True))[0], "QUOTED")
        stage, _ = transition("QUOTED", "SUBMIT", self.table(confirmed=True, quoteValid=True))
        self.assertEqual(stage, "SUBMITTED")
        stage, _ = transition(stage, "UNKNOWN", self.table())
        self.assertEqual(stage, "UNKNOWN")
        self.assertEqual(transition(stage, "SUBMIT", self.table(confirmed=True, quoteValid=True))[0], "UNKNOWN")
        self.assertEqual(transition(stage, "COMMIT", self.table(engineSuccess=True, settled=True))[0], "UNKNOWN")
        self.assertEqual(transition(stage, "REJECT", self.table(correlated=True))[0], "UNKNOWN")
        stage, _ = transition(stage, "COMMIT", self.table(correlated=True, engineSuccess=True, settled=True))
        self.assertEqual(stage, "COMMITTED")
        self.assertEqual(transition(stage, "COMMIT", self.table()), ("COMMITTED", "duplicate"))

    def test_all_lua_sources_compile_as_lua53(self):
        compile_only = self.lua.eval("function(source,name) local fn,err=load(source,name); return fn~=nil,err end")
        for path in (ROOT / "mod/Baiqi").rglob("*.lua"):
            ok, error = compile_only(path.read_text(encoding="utf-8"), str(path))
            self.assertTrue(ok, error)


if __name__ == "__main__":
    unittest.main()
