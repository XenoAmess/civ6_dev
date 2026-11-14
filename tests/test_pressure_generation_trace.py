"""Fake Native ports only; diagnostic trace does not qualify a real world."""
import importlib
from pathlib import Path
import unittest
from tests.test_pressure_fixture_geometry import PORTS,LAYOUT,SOURCE as GEOMETRY

SOURCE=(Path(__file__).resolve().parents[1]/'tools/lua/pressure_generation_trace.lua').read_text(encoding='utf-8')


class PressureGenerationTraceTests(unittest.TestCase):
    def ports(self,version='lua51'):
        lua=importlib.import_module('lupa.'+version).LuaRuntime(unpack_returned_tuples=True)
        env=lua.eval(PORTS)();emit,events=lua.execute('local rows={};return function(s,n) rows[#rows+1]={s,n} end,rows')
        return lua,lua.execute(SOURCE),env,emit,events

    def test_actual_consumer_dual_versions_and_exact_phases(self):
        expected=[['TERRAIN_BEGIN',0]]+[['TERRAIN_PROGRESS',n] for n in range(128,1025,128)]+[['TERRAIN_END',1144]]
        expected += [[stage+'_'+suffix,0] for stage in ('AREA','CHOKE','CONTINENTS','START0','START1') for suffix in ('BEGIN','END')]
        for version in ('lua51','lua53'):
            for variant in ('NO_SITE','MANY'):
                lua,make,env,emit,events=self.ports(version);wrapped,snapshot=make(env,emit)
                self.assertEqual((env.reads,len(env.log),len(events)),(0,0,0))
                self.assertTrue(lua.eval('function(a,b)return a==b end')(env.Map,wrapped.Map))
                result=lua.execute(GEOMETRY)(wrapped,lua.table_from(LAYOUT,recursive=True),variant)
                self.assertEqual(result.land_tiles,11 if variant=='NO_SITE' else 1144)
                self.assertEqual(len(env.log),1149)
                self.assertEqual([list(row.values()) for row in events.values()],expected)
                self.assertEqual(dict(snapshot()),dict(terrain_attempts=1144,terrain_completed=1144,logging_errors=0))
                with self.assertRaisesRegex(Exception,'Extra terrain'):wrapped.TerrainBuilder.SetTerrainType(None,0)
                self.assertEqual(len(env.log),1149)

    def test_all_real_ports_and_enums_checked_before_constructor_side_effects(self):
        for mutation in ['e.grass=0/0','e.hills=math.huge','e.grass=0.5','e.grass=e.ocean',
                         'e.Map.GetPlotByIndex=nil','e.AreaBuilder.Recalculate=nil',
                         'e.TerrainBuilder.StampContinents=nil','e.Players[1].SetStartingPlot=nil']:
            lua,make,env,emit,events=self.ports();lua.eval('function(e)'+mutation+' end')(env)
            with self.assertRaises(Exception):make(env,emit)
            self.assertEqual((env.reads,len(env.log),len(events)),(0,0,0))

    def test_native_error_identity_and_no_success_phase(self):
        for version in ('lua51','lua53'):
            lua,make,env,emit,events=self.ports(version)
            native,sentinel,count=lua.execute('local err={};local n=0;return function(...)n=n+1;error(err,0)end,err,function()return n end')
            env.TerrainBuilder.StampContinents=native;wrapped,snapshot=make(env,emit)
            ok,error=lua.eval('function(w)return pcall(w.TerrainBuilder.StampContinents)end')(wrapped)
            self.assertFalse(ok);self.assertTrue(lua.eval('function(a,b)return a==b end')(error,sentinel))
            self.assertEqual(count(),1)
            self.assertEqual([row[1] for row in events.values()],['CONTINENTS_BEGIN','CONTINENTS_ERROR'])

    def test_nil_arguments_return_arity_and_original_player_self(self):
        for version in ('lua51','lua53'):
            lua,make,env,emit,events=self.ports(version)
            native=lua.eval('''function(...) assert(select('#',...)==4 and select(1,...)==nil
              and select(2,...)=='tail' and select(3,...)==nil and select(4,...)==99);return nil,'RETURN',nil,7 end''')
            env.TerrainBuilder.SetTerrainType=native;env.AreaBuilder.Recalculate=native
            env.Players[1].SetStartingPlot=lua.eval('function(original,fn)return function(self,...)assert(self==original);return fn(...)end end')(env.Players[1],native)
            wrapped,snapshot=make(env,emit)
            pack=lua.eval("function(fn,...)local function p(...)return{n=select('#',...),...}end;return p(fn(...))end")
            colon=lua.eval('function(p,...)return p:SetStartingPlot(...)end')
            for fn,args in [(wrapped.TerrainBuilder.SetTerrainType,()),(wrapped.AreaBuilder.Recalculate,()),
                            (colon,(wrapped.Players[1],))]:
                result=pack(fn,*args,None,'tail',None,99)
                self.assertEqual((result.n,result[1],result[2],result[3],result[4]),(4,None,'RETURN',None,7))

    def test_logger_error_never_prevents_native_or_masks_its_error(self):
        lua,make,env,emit,events=self.ports();bad=lua.eval('function()error("logger",0)end')
        wrapped,snapshot=make(env,bad)
        lua.execute(GEOMETRY)(wrapped,lua.table_from(LAYOUT,recursive=True),'NO_SITE')
        self.assertEqual((len(env.log),snapshot().terrain_completed,snapshot().logging_errors),(1149,1144,20))
        lua,make,env,emit,events=self.ports();native,sentinel=lua.execute('local err={};return function()error(err,0)end,err')
        env.AreaBuilder.Recalculate=native;wrapped,snapshot=make(env,lua.eval('function()error("logger",0)end'))
        ok,error=lua.eval('function(w)return pcall(w.AreaBuilder.Recalculate)end')(wrapped)
        self.assertFalse(ok);self.assertTrue(lua.eval('function(a,b)return a==b end')(error,sentinel))
        self.assertEqual(snapshot().logging_errors,2)

    def test_terrain_failure_stops_consumer_and_snapshot_is_copy(self):
        lua,make,env,emit,events=self.ports();env.failAt=17;wrapped,snapshot=make(env,emit)
        with self.assertRaisesRegex(Exception,'fixture setter failure'):
            lua.execute(GEOMETRY)(wrapped,lua.table_from(LAYOUT,recursive=True),'MANY')
        self.assertEqual((len(env.log),snapshot().terrain_attempts,snapshot().terrain_completed),(18,18,17))
        self.assertEqual([row[1] for row in events.values()],['TERRAIN_BEGIN','TERRAIN_ERROR'])
        snap=snapshot();snap.terrain_attempts=999
        self.assertEqual(snapshot().terrain_attempts,18)
