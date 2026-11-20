from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53

ROOT = Path(__file__).resolve().parents[1]
RECORDER = (ROOT / 'tools/lua/diagnostic_city_commands.lua').read_text(encoding='utf-8')
FACTORY = (ROOT / 'tools/lua/diagnostic_training_startup.lua').read_text(encoding='utf-8')
FIXTURE = r'''
cmCalls=0;umCalls=0;originalError=nil;owner=0;unitType=0;production=nil;failAdd=false
Game={GetCurrentGameTurn=function()return 119 end}
Info={Units={UNIT_SETTLER={Index=0,Hash=-798712536,PopulationCost=1},[0]={UnitType='UNIT_SETTLER'},[6]={UnitType='UNIT_SCOUT'}},GovernorPromotions={GOVERNOR_PROMOTION_RESOURCE_MANAGER_EXPEDITION={Hash=99}}}
local q={GetCurrentProductionTypeHash=function()return 0 end,GetSize=function()return 0 end,GetUnitProgress=function()return 0 end,GetUnitCost=function()return 175 end}
local governor={GetType=function()return 4 end,IsEstablished=function()return true end,HasPromotion=function(_,hash)assert(hash==99);return false end}
Players={[0]={GetGovernors=function()return{GetAssignedGovernor=function()return governor end}end}}
city={GetOwner=function()return owner end,GetID=function()return 196610 end,GetX=function()return 10 end,GetY=function()return 13 end,GetPopulation=function()return 10 end,GetBuildQueue=function()return q end,GetGrowth=function()return{GetFood=function()return 10 end,GetFoodSurplus=function()return 14 end,GetGrowthThreshold=function()return 57 end}end}
unit={GetOwner=function()return owner end,GetID=function()return 7274546 end,GetUnitType=function()return unitType end,GetX=function()return 12 end,GetY=function()return 16 end,GetMovesRemaining=function()return 2.5 end,GetFormationUnitCount=function()return 1 end}
function Pack(...)return{n=select('#',...),...}end
City={RequestOperation=function(...)cmCalls=cmCalls+1;lastCity=Pack(...);if originalError then error(originalError,0)end;return nil,false,nil,9 end}
Units={RequestOperation=function(...)umCalls=umCalls+1;lastUnit=Pack(...);if originalError then error(originalError,0)end;return nil,false,nil,9 end}
originalCity=City.RequestOperation;originalUnit=Units.RequestOperation
Events={};local names={'CityProductionCompleted','UnitAddedToMap','CityPopulationChanged'}
for _,name in ipairs(names)do
 local handlers={};Events[name]={handlers=handlers,Add=function(fn)handlers[#handlers+1]=fn;if failAdd and name=='UnitAddedToMap'then error('synthetic afterAdd')end end,Remove=function(fn)for i=#handlers,1,-1 do if handlers[i]==fn then table.remove(handlers,i)end end end}
end
function InstallProduction()
 local record={rows={},handlers={},errors=0,dropped=0,active=false};production=record
 for _,name in ipairs(names)do production.handlers[name]=function(...)if record.active then record.rows[#record.rows+1]={kind=name,args={...}}end end end
 for _,name in ipairs(names)do Events[name].Add(production.handlers[name])end
 production.active=true
end
env={GetCities=function()return City end,GetUnits=function()return Units end,GetEvents=function()return Events end,GetGame=function()return Game end,GetInfo=function()return Info end,GetPlayers=function()return Players end,GetProduction=function()return production end}
'''


class TrainingStartupDiagnosticTests(unittest.TestCase):
    def run_case(self, body, before=''):
        for name, cls in [('Lua51', Lua51), ('Lua53', Lua53)]:
            with self.subTest(VM=name):
                vm = cls()
                vm.execute(FIXTURE)
                vm.globals().Recorder = vm.execute(RECORDER)
                vm.globals().New = vm.execute(FACTORY)
                vm.execute(before)
                vm.execute('h=New(env,Recorder,InstallProduction)')
                vm.execute(body)

    def test_passive_install_and_exact_nil_return_arity(self):
        self.run_case(r'''
assert(cmCalls==0 and umCalls==0 and not h.Read().failed)
local params={X=11,Y=16};local r=Pack(City.RequestOperation(city,77,params,nil,false))
assert(r.n==4 and r[1]==nil and r[2]==false and r[3]==nil and r[4]==9)
assert(cmCalls==1 and lastCity.n==5 and lastCity[3]==params and lastCity[4]==nil and lastCity[5]==false)
local s=h.Read();assert(s.city.count==1 and s.city.samples[1].returnCount==4 and s.city.before[1].argumentCount==5)
assert(s.city.before[1].facts.population==10 and s.city.before[1].facts.provision==false)
local u=Pack(Units.RequestOperation(unit,1477390184,params));assert(u.n==4 and umCalls==1 and lastUnit.n==3)
assert(h.Read().unit.before[1].facts.moves==2.5)
assert(h.Retire()and City.RequestOperation==originalCity and Units.RequestOperation==originalUnit)
''')

    def test_only_own_city_and_settlers_are_recorded(self):
        self.run_case(r'''
owner=1;City.RequestOperation(city,77,{});Units.RequestOperation(unit,88,{})
owner=0;unitType=6;Units.RequestOperation(unit,88,{})
local s=h.Read();assert(cmCalls==1 and umCalls==2 and s.city.count==0 and s.unit.count==0 and s.unit.ignored==2)
assert(h.Retire())
''')

    def test_metadata_errors_do_not_replace_native_results(self):
        self.run_case(r'''
city.GetPopulation=function()error('metadata unavailable')end
local r=Pack(City.RequestOperation(city,77,{}));assert(cmCalls==1 and r.n==4)
local s=h.Read();assert(s.city.metadataErrors==1 and not s.city.before[1].metadataKnown and s.city.samples[1].returned)
assert(h.Retire())
''')

    def test_filter_error_still_forwards_once(self):
        self.run_case(r'''
unit.GetOwner=function()error('owner unavailable')end
local r=Pack(Units.RequestOperation(unit,88,{}));assert(umCalls==1 and r.n==4)
local s=h.Read();assert(s.unit.filterErrors==1 and s.unit.count==0)
assert(h.Retire())
''')

    def test_original_error_object_and_unreturned_sample(self):
        self.run_case(r'''
originalError={sentinel=true};local ok,e=pcall(City.RequestOperation,city,77,{})
assert(not ok and e==originalError and cmCalls==1)
assert(h.Read().city.samples[1].returned==false)
assert(h.Retire())
''')

    def test_retained_wrapper_and_repeated_retirement(self):
        self.run_case(r'''
local retained=Units.RequestOperation;assert(h.Retire()and h.Retire())
local r=Pack(retained(unit,88,{}));assert(r.n==4 and umCalls==1 and h.Read().unit.count==0)
for _,event in pairs(Events)do assert(#event.handlers==0)end
''')

    def test_foreign_leaf_preserved_and_cleanup_unknown(self):
        self.run_case(r'''
local foreign=function()return'foreign'end;City.RequestOperation=foreign
assert(h.Retire()==false and City.RequestOperation==foreign and Units.RequestOperation==originalUnit)
local s=h.Read();assert(not s.cleanupKnown and not s.city.binding and not s.city.originalBinding)
''')

    def test_foreign_manager_preserved(self):
        self.run_case(r'''
local old=City;City={RequestOperation=function()return'foreign'end}
assert(h.Retire()==false and City.RequestOperation()=='foreign'and old.RequestOperation~=originalCity)
''')

    def test_bounded_rows_preserve_all_forwarding(self):
        self.run_case(r'''
for i=1,258 do City.RequestOperation(city,77,{X=i})end
local s=h.Read();assert(cmCalls==258 and s.city.count==258 and #s.city.samples==256 and s.city.drops==2 and #s.city.before==256)
assert(h.Retire())
''')

    def test_snapshot_copy_does_not_mutate_observation_or_arguments(self):
        self.run_case(r'''
local params={X=11};City.RequestOperation(city,77,params)
local s=h.Read();s.city.samples[1].params.X=999;s.city.before[1].facts.population=999
local z=h.Read();assert(params.X==11 and z.city.samples[1].params.X==11 and z.city.before[1].facts.population==10)
assert(h.Retire())
''')

    def test_partial_event_install_rolls_back_owned_bindings(self):
        self.run_case(r'''
local s=h.Read();assert(s.failed and s.cleanupKnown and s.retired and production.active==false)
assert(City.RequestOperation==originalCity and Units.RequestOperation==originalUnit)
for _,event in pairs(Events)do assert(#event.handlers==1)end
''', 'for _,event in pairs(Events)do event.Add(function()end)end;failAdd=true')

    def test_foreign_remove_not_called_and_callback_disabled(self):
        self.run_case(r'''
local event=Events.UnitAddedToMap;local callback=production.handlers.UnitAddedToMap
event.Remove=function()error('foreign remove must not run')end
assert(h.Retire()==false and not production.active)
callback(0,7274546);assert(#production.rows==0 and #event.handlers==1)
assert(City.RequestOperation==originalCity and Units.RequestOperation==originalUnit)
''')

    def test_foreign_production_namespace_preserved(self):
        self.run_case(r'''
local owned=production;local foreign={active=true,rows={},handlers={}};production=foreign
assert(h.Retire()==false and foreign.active==true and owned.active==false)
local s=h.Read();assert(not s.productionBinding and not s.cleanupKnown)
for _,event in pairs(Events)do assert(#event.handlers==0)end
''')

    def test_existing_namespace_rejected_before_sdk_changes(self):
        for name, cls in [('Lua51', Lua51), ('Lua53', Lua53)]:
            with self.subTest(VM=name):
                vm = cls()
                vm.execute(FIXTURE)
                vm.globals().Recorder = vm.execute(RECORDER)
                vm.globals().New = vm.execute(FACTORY)
                vm.execute(r'''
production={active=true};local prior=production
local ok=pcall(New,env,Recorder,InstallProduction)
assert(not ok and production==prior and production.active and cmCalls==0 and umCalls==0)
assert(City.RequestOperation==originalCity and Units.RequestOperation==originalUnit)
for _,event in pairs(Events)do assert(#event.handlers==0)end
''')


if __name__ == '__main__':
    unittest.main()
