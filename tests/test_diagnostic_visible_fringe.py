from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class VisibleFringeTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.probe=self.lua.execute((ROOT/'tools/lua/diagnostic_visible_fringe.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
edges={};revealed={};visibilityReads={};neighborReads={};badVisibility=false
function Plot(i,x,y)
 return setmetatable({GetIndex=function()return i end,GetX=function()return x or i end,
 GetY=function()return y or 0 end},{__index=function(_,k)error('HIDDEN_CONTENT:'..k)end})
end
M={GetAdjacentPlot=function(x,y,d)
 local k=x..':'..y;neighborReads[k]=(neighborReads[k]or 0)+1
 local e=edges[x]and edges[x][d];if type(e)=='table'then return e end
 if e~=nil then return Plot(e)end
end}
V={IsRevealed=function(_,x,y)
 visibilityReads[x]=(visibilityReads[x]or 0)+1
 if badVisibility then return nil end
 return revealed[x]==true
end}
''')

    def call(self,x=0,y=0):return self.probe(self.lua.globals().M,self.lua.globals().V,x,y)

    def test_bfs_crosses_revealed_ring_stops_at_three_and_sorts(self):
        self.lua.execute('edges={[0]={[0]=5,[1]=2},[5]={[0]=7},[2]={[0]=3},[3]={[0]=4},[4]={[0]=9}};revealed[5]=true;revealed[2]=true')
        r=self.call();self.assertTrue(r.complete)
        self.assertEqual([(v.distance,v.plot_index)for v in r.rows.values()],[(2,3),(2,7),(3,4)])
        self.assertEqual(r.inspected_nodes,6)
        self.assertIsNone(self.lua.globals().neighborReads['4:0'])

    def test_cycle_center_index_and_duplicate_nodes_read_once(self):
        self.lua.execute('edges={[0]={[0]=1,[1]=1},[1]={[0]=0,[1]=2},[2]={[0]=1}}')
        r=self.call();self.assertTrue(r.complete);self.assertEqual(r.inspected_nodes,3)
        self.assertEqual([v.plot_index for v in r.rows.values()],[1,2])
        self.assertEqual(self.lua.globals().visibilityReads[1],1)
        self.assertIsNone(self.lua.globals().visibilityReads[0])

    def test_worldedge_nil_and_invalid_arguments_are_distinct(self):
        r=self.call();self.assertEqual((r.status,r.inspected_nodes,len(r.rows)),('COMPLETE',1,0))
        for x in (-1,1.5,float('nan'),float('inf'),'0',None):
            with self.subTest(x=x):
                r=self.call(x);self.assertEqual((r.status,r.inspected_nodes),('UNKNOWN',0))

    def test_unknown_visibility_errors_and_conflicting_geometry_preserve_partial(self):
        for change in ('badVisibility=true',
                       'M.GetAdjacentPlot=function()error("read")end',
                       'edges[0][1]=Plot(1,2,0)',
                       'edges[0][1]=Plot(2,1,0)',
                       'edges[0][1]=Plot(3,0/0,0)'):
            with self.subTest(change=change):
                self.setUp();self.lua.execute('edges={[0]={[0]=1}};'+change)
                r=self.call();self.assertEqual(r.status,'UNKNOWN');self.assertFalse(r.complete)

    def tree(self,n):
        self.lua.globals().N=n
        self.lua.execute('''
edges={};local level={0};local nextID=1
for depth=1,3 do local fresh={}
 for _,parent in ipairs(level)do edges[parent]={}
  for direction=0,5 do if nextID<N then
   edges[parent][direction]=nextID;fresh[#fresh+1]=nextID;nextID=nextID+1
  end end
 end
 level=fresh
end
''')

    def test_node_cap_exact64_and_extra65_without_visibility_read_for_extra(self):
        self.tree(64);r=self.call();self.assertTrue(r.complete)
        self.assertEqual((r.inspected_nodes,len(r.rows)),(64,63))
        self.setUp();self.tree(65);r=self.call()
        self.assertEqual((r.status,r.inspected_nodes,len(r.rows)),('PARTIAL_LIMIT',64,63))
        self.assertIsNone(self.lua.globals().visibilityReads[64])


if __name__=='__main__':unittest.main()
