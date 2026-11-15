"""Real-controller regression from the native 178 mountain/civilian blockade."""
from pathlib import Path
import json
import unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT/'tests/fixtures/settler_blocked_route178.json').read_text(encoding='utf-8'))


class SettlerBoundedDetourTests(unittest.TestCase):
    candidate_source = None

    def world(self, runtime, change='', single_corridor=False):
        lua = runtime(unpack_returned_tuples=True)
        for name in ('tests/lua/mock_world.lua', 'tests/lua/mock_movement.lua',
                     'tests/lua/mock_path_ranking.lua', 'mod/Baiqi/Lua/BaiqiConfig.lua',
                     'mod/Baiqi/Lua/BaiqiPolicy.lua', 'mod/Baiqi/Lua/BaiqiPlanner.lua'):
            lua.execute((ROOT/name).read_text(encoding='utf-8'))
        nodes = ','.join('{index=%d,x=%d,y=%d,water=%s,impassable=%s,blocked=%s}' %
                         (n['index'], n['x'], n['y'], str(n['water']).lower(),
                          str(n['impassable']).lower(), str(n['why']=='CIVILIAN').lower())
                         for n in FIXTURE['nodes'])
        path = ','.join(map(str, FIXTURE['native_path']))
        lua.execute('FixtureNodes={'+nodes+'};FixturePath={'+path+'}')
        lua.execute('''
local w,o=TestWorld,TestWorld.objects
w.withBuilder=false;w.withSettler=true;w.queueSize=1;w.settlerPlot=230
w.settlementRecommendations={845};w.nativePath=FixturePath;w.nodeReads=0;w.moveChecks=0
w.hidden={};w.fogged={};w.siteOwners={};w.blocked={};w.impassable={};w.plots={};w.byXY={}
GameInfo.Units[3]={UnitType='UNIT_GREAT_PROPHET',Index=3,FormationClass='FORMATION_CLASS_CIVILIAN',Maintenance=0}
for _,n in ipairs(FixtureNodes)do
 local i,x,y=n.index,n.x,n.y
 w.blocked[i]=n.blocked;w.impassable[i]=n.impassable
 local p={GetIndex=function()return i end,GetX=function()return x end,GetY=function()return y end,
  GetOwner=function()return w.siteOwners[i]or(i==845 and -1 or 7)end,
  IsWater=function()return n.water end,IsImpassable=function()return w.impassable[i]end,
  IsCity=function()return false end,GetFeatureType=function()return -1 end}
 w.plots[i]=p;w.byXY[x..':'..y]=p
end
Map.GetPlotByIndex=function(i)return w.plots[i]end
Map.GetPlot=function(x,y)return w.byXY[math.floor(x)..':'..math.floor(y)]end
Map.GetPlotDistance=function(x,y,x2,y2)
 local dq=x2-math.floor(y2/2)-x+math.floor(y/2);local dr=y2-y
 return(math.abs(dq)+math.abs(dr)+math.abs(dq+dr))/2
end
Map.GetPlotXYWithRangeCheck=function(x,y,dq,dr,r)
 if(math.abs(dq)+math.abs(dr)+math.abs(dq+dr))/2>r then return nil end
 return Map.GetPlot(x-math.floor(y/2)+dq+math.floor((y+dr)/2),y+dr)
end
Map.GetAdjacentPlot=function(x,y,d)
 local a={{1,0},{0,1},{-1,1},{-1,0},{0,-1},{1,-1}};local q=a[d+1]
 return Map.GetPlotXYWithRangeCheck(x,y,q[1],q[2],1)
end
PlayersVisibility[7].IsRevealed=function(_,x,y)local p=Map.GetPlot(x,y);return p~=nil and not w.hidden[p:GetIndex()]end
PlayersVisibility[7].IsVisible=function(_,x,y)local p=Map.GetPlot(x,y);return p~=nil and not w.hidden[p:GetIndex()]and not w.fogged[p:GetIndex()]end
local enemy={GetID=function()return 900 end,GetOwner=function()return 8 end,GetUnitType=function()return 0 end}
local civilian={GetID=function()return 5 end,GetOwner=function()return 7 end,GetUnitType=function()return w.unknownType and 999 or 3 end}
Units.GetUnitsInPlot=function(p)
 local i=p:GetIndex();assert(not w.hidden[i]and not w.fogged[i],'hidden occupancy queried')
 w.nodeReads=w.nodeReads+1
 if i==w.enemyPlot then return{enemy}end
 if w.blocked[i]then return{civilian}end
 return{}
end
local oldLayer=Units.GetUnitsInPlotLayerID
Units.GetUnitsInPlotLayerID=function(p,l)
 if p:GetIndex()==w.unknownLayer then return nil end
 return oldLayer(p,l)
end
o.settler.GetPlotId=function()return w.settlerPlot end
o.settler.GetX=function()return w.plots[w.settlerPlot]:GetX()end
o.settler.GetY=function()return w.plots[w.settlerPlot]:GetY()end
UnitManager.GetMoveToPathEx=function(u,i)
 w.pathQueries[#w.pathQueries+1]={unit=u:GetID(),target=i}
 if i==845 then return{plots=w.nativePath}end
 if w.badNative then return{plots={w.settlerPlot,230,i}}end
 if w.settlerPlot==230 and i==229 then return{plots={230,186,229}}end
 return{plots={w.settlerPlot,i}}
end
local can=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(u,op,mode,params)
 if op==10 then w.moveChecks=w.moveChecks+1;if w.onMoveCheck then w.onMoveCheck(w.moveChecks,params)end end
 return can(u,op,mode,params)
end
w.goalProposals={['2']={unitID=2,unitType='UNIT_SETTLER',plot=845,x=9,y=19}}
''')
        if single_corridor:
            lua.execute('''
local w=TestWorld;local keep={[230]=true,[186]=true,[229]=true,[273]=true,[317]=true,[362]=true,[363]=true}
for _,i in ipairs(FixturePath)do keep[i]=true end
for i in pairs(w.plots)do if not keep[i]then w.impassable[i]=true end end
''')
        if change:
            lua.execute(change)
        source = self.candidate_source or (ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8')
        lua.execute(source)
        return lua

    def run_case(self, lua, count=3):
        w=lua.globals().TestWorld
        for _ in range(count):
            lua.globals().BaiqiController.RunNow()
        self.assertNotIn('脚本错误', lua.globals().BaiqiController.GetStatus())
        self.assertTrue(all(r.unit==2 for r in w.unitRequests.values()), 'Never order a blocker or military')
        return [(r.params[14],r.params[15])for r in w.unitRequests.values()if r.op==10]

    def test_native_blockade_uses_qualified_step_away_from_goal(self):
        for runtime in (Lua51,Lua53):
            with self.subTest(runtime=runtime.__module__):
                self.assertEqual(self.run_case(self.world(runtime)),[(10,4)])

    def test_after_observed_step_does_not_follow_native_path_back_to_blockade(self):
        for runtime in (Lua51,Lua53):
            with self.subTest(runtime=runtime.__module__):
                lua=self.world(runtime,"TestWorld.settlerPlot=186;table.insert(TestWorld.nativePath,1,186)")
                self.assertEqual(self.run_case(lua),[(9,5)])

    def test_blocked_or_unknown_corridors_wait(self):
        cases={
            'first_blocked':'TestWorld.blocked[186]=true',
            'first_foreign':'TestWorld.siteOwners[186]=8',
            'first_hidden':'TestWorld.hidden[186]=true',
            'first_fogged':'TestWorld.fogged[186]=true',
            'middle_mountain':'TestWorld.impassable[229]=true',
            'middle_civilian':'TestWorld.blocked[229]=true',
            'middle_foreign':'TestWorld.siteOwners[229]=8',
            'middle_hidden':'TestWorld.hidden[229]=true',
            'middle_fogged':'TestWorld.fogged[229]=true',
            'unknown_layer':'TestWorld.unknownLayer=229',
            'unknown_occupant':'TestWorld.unknownType=true',
            'bad_first_native_edge':'TestWorld.badNative=true',
            'native_permission_false':'TestWorld.rejectMoveX=10',
            'escort':'TestWorld.formation=2',
            'visible_threat':'TestWorld.enemyPlot=229',
        }
        for runtime in (Lua51,Lua53):
            for name,change in cases.items():
                with self.subTest(runtime=runtime.__module__,case=name):
                    self.assertEqual(self.run_case(self.world(runtime,change,single_corridor=True)),[])

    def test_fresh_native_qualification_invalidates_changed_corridor(self):
        cases={
            'first_occupant':'w.blocked[186]=true',
            'middle_occupant':'w.blocked[229]=true',
            'middle_hidden':'w.hidden[229]=true',
            'middle_foreign':'w.siteOwners[229]=8',
            'middle_mountain':'w.impassable[229]=true',
            'goal_occupied':'w.blocked[845]=true',
            'goal_foreign':'w.siteOwners[845]=8',
            'escort':'w.formation=2',
            'new_threat':'w.enemyPlot=229',
        }
        for runtime in (Lua51,Lua53):
            for name,change in cases.items():
                for qualification in (1,2,3):
                    with self.subTest(runtime=runtime.__module__,case=name,qualification=qualification):
                        lua=self.world(runtime,'local w=TestWorld;w.onMoveCheck=function(n)if n=='+str(qualification)+' then '+change+' end end',single_corridor=True)
                        self.assertEqual(self.run_case(lua),[])


if __name__=='__main__':unittest.main()
