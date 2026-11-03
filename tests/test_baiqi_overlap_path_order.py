from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime
from gp_intent_harness import install_gp_bridge

ROOT=Path(__file__).resolve().parents[1]


class OverlapPathOrderTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT/'tests/lua/mock_world.lua').read_text(encoding='utf-8'))
        install_gp_bridge(self.lua)
        for name in ('tests/lua/mock_scientist.lua','tests/lua/mock_civilian_overlap.lua',
                     'mod/Baiqi/Lua/BaiqiConfig.lua','mod/Baiqi/Lua/BaiqiPolicy.lua',
                     'mod/Baiqi/Lua/BaiqiPlanner.lua'):
            self.lua.execute((ROOT/name).read_text(encoding='utf-8'))
        self.lua.execute('''
local w=TestWorld
local original=Map.GetPlotByIndex
local prototype=original(43)
local plots={[42]=original(42),[43]=prototype}
local function neighbor(index,x,y)
 return setmetatable({GetIndex=function() return index end,GetX=function() return x end,
 GetY=function() return y end},{__index=prototype})
end
plots[44]=neighbor(44,2,4);plots[45]=neighbor(45,1,3)
Map.GetPlotByIndex=function(index) return plots[index] end
Map.GetPlot=function(x,y)
 for _,p in pairs(plots) do if p:GetX()==x and p:GetY()==y then return p end end
end
Map.GetPlotDistance=function(x,y,x2,y2) return math.abs(x-x2)+math.abs(y-y2) end
local order={45,43,44}
Map.GetAdjacentPlot=function(x,y,direction)
 if x==2 and y==3 then return plots[order[direction+1]] end
end
w.overlapPathQueries={}
UnitManager.GetMoveToPathEx=function(unit,index)
 w.overlapPathQueries[#w.overlapPathQueries+1]=index
 if w.pathMissing43 and index==43 then return {plots={}} end
 return {plots={42,index}}
end
UnitManager.CanStartOperation=function(unit,operation,_,params)
 if operation~=UnitOperationTypes.MOVE_TO then return false end
 if w.rejectAllMoves then return false end
 if w.rejectMove43 and params[14]==3 and params[15]==3 then return false end
 return true
end
''')
        self.private=self.lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')+'''
return {RunOverlap=function()
 local ctx,player,state=PlayerContext()
 return ClearCivilianOverlap(ctx,player,state,player:GetUnits():FindID(4))
end}
''')
        self.w=self.lua.globals().TestWorld
        self.c=self.lua.globals().BaiqiController
        self.c.RunNow(False)

    def run_overlap(self):
        return self.private.RunOverlap()


    def test_first_accepted_destination_skips_unused_native_paths(self):
        self.assertIs(self.run_overlap(),True)
        self.assertEqual(list(self.w.overlapPathQueries.values()),[43])
        self.assertEqual(len(self.w.unitRequests),1)
        request=self.w.unitRequests[1]
        self.assertEqual((request.unit,request.op,request.params[14],request.params[15]),(4,10,3,3))

    def test_failed_first_destination_tries_next_and_all_rejected_remain_bounded(self):
        for flag in ('pathMissing43','rejectMove43','rejectAllMoves'):
            with self.subTest(flag=flag):
                self.setUp();self.w[flag]=True
                rejected=flag=='rejectAllMoves'
                self.assertIs(self.run_overlap(),not rejected)
                self.assertEqual(list(self.w.overlapPathQueries.values()),[43,44,45] if rejected else [43,44])
                self.assertEqual(len(self.w.unitRequests),0 if rejected else 1)
                if not rejected:
                    request=self.w.unitRequests[1]
                    self.assertEqual((request.unit,request.op,request.params[14],request.params[15]),(4,10,2,4))
                self.assertTrue(all(r.unit==4 for r in self.w.unitRequests.values()))


if __name__=='__main__':
    unittest.main()
