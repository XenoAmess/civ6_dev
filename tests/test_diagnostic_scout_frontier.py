from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class ScoutFrontierTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.probe=self.lua.execute((ROOT/'tools/lua/diagnostic_scout_frontier.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
units={};revealed=false;pending=false;extraQueue=false;zeroQueue=false
function Unit(id)
 return{GetID=function()return id end,GetOwner=function()return 0 end,GetUnitType=function()return 1 end,
 GetX=function()return id end,GetY=function()return 2 end,GetMovesRemaining=function()return 2.5 end,
 GetFormationUnitCount=function()return 1 end,IsReadyToMove=function()return true end,
 IsReadyToSelect=function()return true end,IsDead=function()return false end,
 IsDelayedDeath=function()return false end,HasPendingOperations=function()return pending end}
end
function Plot(index)
 return setmetatable({GetIndex=function()return index end,GetX=function()return index+10 end,
 GetY=function()return 3 end},{__index=function(_,k)error('HIDDEN_CONTENT_OR_UNDECLARED_API:'..k)end})
end
E={Game={GetLocalPlayer=function()return 0 end},GameConfiguration={IsAnyMultiplayer=function()return false end,
 IsHotseat=function()return false end},PlayerConfigurations={[0]={GetLeaderTypeName=function()return'LEADER_BAIQI'end,
 IsHuman=function()return true end}},Players={[0]={IsTurnActive=function()return true end,
 GetUnits=function()return{Members=function()return ipairs(units)end}end}},
 GameInfo={Units={[1]={UnitType='UNIT_SCOUT'},[2]={UnitType='UNIT_BUILDER'}}},
 UnitManager={GetQueuedDestination=function()if extraQueue then return nil,nil end;if zeroQueue then return 0 end;return nil end},
 PlayersVisibility={[0]={IsRevealed=function()return revealed end}},
 Map={GetAdjacentPlot=function(x,_,d)if d>0 then return nil end;return Plot(x)end}}
units={Unit(2),Unit(1)}
''')

    def probe_current(self):return self.probe(self.lua.globals().E)

    def test_geometry_only_unknown_neighbors_sorted_and_no_game_commands(self):
        r=self.probe_current();self.assertTrue(r.complete)
        self.assertEqual([v.unit_id for v in r.rows.values()],[1,2])
        row=r.rows[1];self.assertEqual((row.unit_x,row.unit_y,row.x,row.y,row.plot_index),(1,2,11,3,1))
        self.lua.execute('revealed=true');self.assertEqual(len(self.probe_current().rows),0)

    def test_queue_zero_and_pending_true_exclude_extra_nil_is_unknown(self):
        self.lua.execute('zeroQueue=true');r=self.probe_current();self.assertTrue(r.complete);self.assertEqual(len(r.rows),0)
        self.lua.execute('zeroQueue=false;extraQueue=true');self.assertEqual(self.probe_current().status,'UNKNOWN')
        self.lua.execute('extraQueue=false;pending=true');r=self.probe_current();self.assertTrue(r.complete);self.assertEqual(len(r.rows),0)
        self.lua.execute('pending=nil');self.assertEqual(self.probe_current().status,'UNKNOWN')

    def test_known_civilian_escort_foreign_and_unready_units_are_excluded(self):
        for change in ('units[1].GetUnitType=function()return 2 end',
                       'units[1].GetFormationUnitCount=function()return 2 end',
                       'units[1].GetOwner=function()return 1 end',
                       'units[1].IsReadyToMove=function()return false end'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute('units={Unit(1)};'+change)
                r=self.probe_current();self.assertTrue(r.complete);self.assertEqual(len(r.rows),0)

    def test_unknown_reads_and_context_cannot_become_empty_complete(self):
        for change in ('pending=nil','revealed=nil',
                       'E.UnitManager.GetQueuedDestination=function()error("read")end',
                       'E.Map.GetAdjacentPlot=function()return false end',
                       'E.Game.GetLocalPlayer=function()return 1 end',
                       'E.GameConfiguration.IsAnyMultiplayer=function()return nil end',
                       'units[1].GetMovesRemaining=function()return 0/0 end'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute(change);r=self.probe_current()
                self.assertEqual(r.status,'UNKNOWN');self.assertFalse(r.complete)

    def test_row_limit_exact_extra_and_duplicates(self):
        self.lua.execute('units={};for i=1,64 do units[i]=Unit(i)end')
        r=self.probe_current();self.assertTrue(r.complete);self.assertEqual(len(r.rows),64)
        self.lua.execute('units[65]=Unit(65)');r=self.probe_current()
        self.assertEqual((r.status,len(r.rows)),('PARTIAL_LIMIT',64))
        self.lua.execute('units[65]=Unit(1)');r=self.probe_current()
        self.assertTrue(r.complete);self.assertEqual(len(r.rows),64)

    def test_unit_limit_exact_and_extra(self):
        self.lua.execute('units={};for i=1,256 do units[i]=Unit(i);units[i].GetUnitType=function()return 2 end end')
        r=self.probe_current();self.assertTrue(r.complete);self.assertEqual(r.inspected_units,256)
        self.lua.execute('units[257]=Unit(257)');r=self.probe_current()
        self.assertEqual((r.status,r.inspected_units),('PARTIAL_LIMIT',256))


if __name__=='__main__':unittest.main()
