from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from tools.build_initial_world_observed_mod import transform,restore,HELPER

HARNESS=r'''
return function(Create,which)
 local f={owned=false,production=false,badRead=false,hidden=false};local calls={run=0,update=0,requests=0,hiddenReads=0};local args
 local function Iter(items)local i=0;return function()i=i+1;if items[i]then return i,items[i]end end end
 local function Info(items)local t={};for _,r in ipairs(items)do t[r.Index]=r end;return setmetatable(t,{__call=function()local i=0;return function()i=i+1;return items[i]end end})end
 local settler={GetID=function()return65536 end,GetOwner=function()return0 end,GetUnitType=function()return0 end,GetX=function()return16 end,GetY=function()return14 end,GetMovesRemaining=function()return2 end,GetFormationUnitCount=function()return1 end}
 local army={GetID=function()return131073 end,GetOwner=function()return0 end,GetUnitType=function()return1 end,GetX=function()return17 end,GetY=function()return14 end,GetMovesRemaining=function()return2 end,GetFormationUnitCount=function()return1 end}
 local q={GetSize=function()return f.production and 1 or 0 end,GetCurrentProductionTypeHash=function()return f.production and 101 or 0 end,GetBuildingProgress=function()return0 end,GetBuildingCost=function()return20 end}
 local city={GetID=function()return65536 end,GetOwner=function()return0 end,GetX=function()return16 end,GetY=function()return14 end,GetPopulation=function()return1 end,GetBuildQueue=function()return q end}
 local cities={Members=function()return Iter(f.owned and{city}or{})end,GetCapitalCity=function()if f.owned then return city end end}
 local units={Members=function()return Iter(f.owned and{army}or{settler,army})end};local player={GetCities=function()return cities end,GetUnits=function()return units end}
 local function Secret(value)if f.hidden then calls.hiddenReads=calls.hiddenReads+1;error('hidden plot read')end;return value end
 local plot={GetIndex=function()return632 end,GetX=function()return16 end,GetY=function()return14 end,GetOwner=function()return Secret(-1)end,IsCity=function()return Secret(false)end,IsWater=function()return Secret(false)end,GetTerrainType=function()return Secret(1)end,GetFeatureType=function()return Secret(-1)end,GetResourceType=function()return Secret(-1)end,GetImprovementType=function()return Secret(-1)end}
 local e={Game={GetLocalPlayer=function()if f.badRead then error('capture read failed')end;return0 end,GetCurrentGameTurn=function()return1 end},PlayerConfigurations={[0]={GetLeaderTypeName=function()return'LEADER_BAIQI'end,IsHuman=function()return true end}},Players={[0]=player},GameInfo={Units=Info({{Index=0,Hash=201,UnitType='UNIT_SETTLER'},{Index=1,Hash=202,UnitType='UNIT_WARRIOR'}}),Buildings=Info({{Index=1,Hash=101,BuildingType='BUILDING_MONUMENT'}})},Map={GetPlot=function(x,y)if x==16 and y==14 then return plot end end},PlayersVisibility={[0]={IsVisible=function()return not f.hidden end,IsRevealed=function()return not f.hidden end}},UnitManager={CanStartOperation=function(...)assert(select('#',...)==5);return true end,RequestOperation=function()calls.requests=calls.requests+1;error('observer requested game action')end},UnitOperationTypes={FOUND_CITY=9},OperationResultsTypes={ALL=2},print=function()end}
 local function Pack(...)return{n=select('#',...),...}end
 local nativeRun=function(...)calls.run=calls.run+1;args=Pack(...);if which=='original-error'then error('original failure')end;f.owned=true;if which~='delayed-production'then f.production=true end;return17,nil,'last'end
 local nativeUpdate=function(...)calls.update=calls.update+1;if which=='delayed-production'then f.production=true end end
 local c={RunNow=nativeRun,Update=nativeUpdate};local api=Create(e,c);assert(calls.run==0 and calls.update==0)
 if which=='capture-error'then f.badRead=true;local r=Pack(c.RunNow(5,nil,8));assert(r.n==3 and r[1]==17 and r[2]==nil and r[3]=='last'and calls.run==1 and #api.Read().errors==2)
 elseif which=='original-error'then local ok,err=pcall(c.RunNow);assert(not ok and string.find(err,'original failure',1,true)and calls.run==1)
 elseif which=='foreign-binding'then local foreign=function()return99 end;c.Update=foreign;assert(api.Retire()==false and c.Update==foreign and c.RunNow==nativeRun and api.Read().foreign.Update);return true
 elseif which=='retire-before-call'then assert(api.Retire());local r=Pack(c.RunNow());assert(r.n==3 and api.Read().calls.RunNow==0 and api.Read().initial==nil)
 else
  if which=='hidden'then f.hidden=true end
  local r=Pack(c.RunNow(5,nil,8));assert(r.n==3 and r[1]==17 and r[2]==nil and r[3]=='last'and args.n==3 and args[1]==5 and args[2]==nil and args[3]==8)
  local s=api.Read();assert(#s.errors==0 and #s.initial.cities==0 and #s.initial.units==2 and s.initial.units[1].formation==1 and s.initial.units[1].nativeCanFound==true and s.firstCity.capitalID==65536 and #s.firstCity.cities==1)
  assert(#s.initial.visiblePlots==(f.hidden and 0 or 1)and calls.hiddenReads==0)
  if which=='delayed-production'then assert(s.production==nil);assert(select('#',c.Update(4,nil))==0)end
  assert(s.production.cities[1].kind=='BUILDING'and s.production.cities[1].type=='BUILDING_MONUMENT'and s.production.cities[1].progress==0 and s.production.cities[1].cost==20 and s.complete)
 end
 assert(api.Retire()and c.RunNow==nativeRun and c.Update==nativeUpdate and api.Read().retired and calls.requests==0)
 return true
end
'''
import re
HARNESS=re.sub(r'\breturn(?=\d)','return ',HARNESS)

class InitialWorldObserverTests(unittest.TestCase):
    def test_real_observer_boundaries_both_lua_versions(self):
        source=HELPER.read_text(encoding='utf-8')
        for version,Runtime in [('Lua51',L51),('Lua53',L53)]:
            lua=Runtime();run=lua.execute(HARNESS);create=lua.execute(source)
            for case in ['ordinary','delayed-production','hidden','capture-error','original-error','foreign-binding','retire-before-call']:
                with self.subTest(version=version,case=case):self.assertTrue(run(create,case))
    def test_exact_inverse_and_global_export_boundary(self):
        raw='BaiqiController={}\nfunction BaiqiController.RunNow(...)return ... end\nfunction BaiqiController.Update()end\nfunction BaiqiController.Shutdown()end\n'
        changed,insertion=transform(raw);self.assertEqual(restore(changed,insertion),raw)
        for Runtime in (L51,L53):Runtime().compile(changed)
        with self.assertRaises(ValueError):transform(changed)
        with self.assertRaises(ValueError):transform(raw+'\nreturn BaiqiController\n')
        with self.assertRaises(ValueError):transform(raw.replace('function BaiqiController.Update()', 'function BaiqiController.Tick()'))
        with self.assertRaises(ValueError):restore(changed,'unknown insertion')

if __name__=='__main__':unittest.main()
