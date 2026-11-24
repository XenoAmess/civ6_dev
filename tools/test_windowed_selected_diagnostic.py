from pathlib import Path
import subprocess,tempfile,unittest
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from tools import build_windowed_selected_profile_mod as build

ROOT=Path(__file__).resolve().parents[1]
RAW='''
local function Choice(unit,choice)
 local ok,edge=pcall(UnitManager.GetMoveToPathEx,unit,choice.index)
 return ok,edge
end
local function Edge(unit,index)
 local pathQuery=UnitManager.GetMoveToPathEx
 local ok,edge=pcall(pathQuery,unit,index)
 return ok,edge
end
local function Step(unit,target)
 local path = UnitManager.GetMoveToPathEx(unit, target:GetIndex())
 return path
end
local function Packet(unit,targetIndex)
 local ok, path = pcall(UnitManager.GetMoveToPathEx, unit, targetIndex)
 return ok,path
end
local function District(unit,job)
 local query=UnitManager.GetMoveToPathEx
 local ok,path=pcall(query,unit,job.endpoint or job.index)
 return ok,path
end
return {Choice=Choice,Edge=Edge,Step=Step,Packet=Packet,District=District}
'''

class WindowedSelectedDiagnostic(unittest.TestCase):
    def runtime(self,VM,capacity=32):
        lua=VM(unpack_returned_tuples=True)
        lua.execute('''Turn=85;Player=0;Time=100;ClockBad=false
function Clock()if ClockBad then return 0/0 end;return Time end
function ReadTurn()return Turn end
function ReadPlayer()return Player end
function Pack(...)return{n=select('#',...),...}end
''')
        factory=lua.execute((ROOT/'tools/lua/diagnostic_windowed_selected.lua').read_text())
        profile=lua.execute('local unpack=unpack or table.unpack\n'+(ROOT/'tools/lua/diagnostic_profile.lua').read_text())
        wrap,api=factory(profile,lua.globals().Clock,lua.globals().ReadTurn,lua.globals().ReadPlayer,
                         lua.table_from(['Tick','ReadBack','BaiqiController.RunNow']),capacity,86,87)
        lua.globals().Wrap=wrap;lua.globals().API=api;lua.globals().P6PerfWindow184=api
        return lua

    def each(self,code,capacity=32):
        for VM in(L51,L53):
            with self.subTest(VM=VM.__module__):self.runtime(VM,capacity).execute(code)

    def test_disabled_and_unselected_keep_identity_arity_and_original_once(self):
        self.each("local n=0;local f=function(...)n=n+1;return ... end;assert(Wrap('Other.lua:1:Tick',f)==f and Wrap('Lua/BaiqiController.lua:1:Other',f)==f);local w=Wrap('Lua/BaiqiController.lua:1:Tick',f);local r=Pack(w(nil,false,7,nil));assert(n==1 and r.n==4 and r[1]==nil and r[2]==false and r[3]==7 and r[4]==nil and API.Read().totalCalls==0)")

    def test_only_two_actual_anchored_ten_second_windows_are_recorded(self):
        self.each("local f=Wrap('Lua/BaiqiController.lua:1:Tick',function()Time=Time+.01;return 7 end);assert(API.Arm(0,85));Turn=86;assert(f()==7 and API.Read().totalCalls==0);assert(API.Anchor(0,86));assert(f()==7);local a=API.Read().anchors[86];Time=a+10;assert(f()==7 and API.Read().totalCalls==1);Turn=87;assert(f()==7 and API.Read().totalCalls==1);assert(API.Anchor(0,87));assert(f()==7 and API.Read().totalCalls==2);Turn=88;assert(f()==7 and API.Read().totalCalls==2);assert(API.Read().skippedOutsideWindows==4)")

    def test_nested_children_and_parent_keep_separate_inclusive_rows(self):
        self.each("local child=Wrap('Lua/BaiqiController.lua:1:ReadBack',function(...)Time=Time+.002;return ... end);local root=Wrap('Lua/BaiqiController.lua:2:BaiqiController.RunNow',function()return child(nil,false,7,nil)end);assert(API.Arm(0,85));Turn=86;assert(API.Anchor(0,86));local r=Pack(root(true));local s=API.Read();assert(r.n==4 and r[1]==nil and r[2]==false and r[3]==7 and r[4]==nil and #s.rows==2 and s.totalCalls==2 and s.rows[1].argumentCount==4 and s.rows[2].allowOrders=='true'and s.rows[2].turnStart==86 and s.rows[2].turnEnd==86 and s.rows[2].windowEligible and s.rows[2].started<=s.rows[1].started and s.rows[2].ended>=s.rows[1].ended)")

    def test_crossing_window_end_is_retained_and_explicitly_ineligible(self):
        self.each("local f=Wrap('Lua/BaiqiController.lua:1:Tick',function()Time=Time+11;return 2 end);assert(API.Arm(0,85));Turn=86;assert(API.Anchor(0,86));assert(f()==2);local s=API.Read();assert(#s.rows==1 and not s.rows[1].windowEligible and s.rows[1].seconds==11 and s.rows[1].anchor==100)")

    def test_original_error_object_and_native_false_nil_arity_are_preserved(self):
        self.each("assert(API.Arm(0,85));Turn=86;assert(API.Anchor(0,86));local n=0;local function f(...)n=n+1;assert(select('#',...)==2);Time=Time+.01;return false,nil,7,nil end;local r=Pack(API.Path('builder-packet',f,false,nil));assert(n==1 and r.n==4 and r[1]==false and r[2]==nil and r[3]==7 and r[4]==nil);local failure={};local function bad()n=n+1;Time=Time+.01;error(failure,0)end;local ok,why=pcall(API.Path,'path-step',bad);local s=API.Read();assert(not ok and why==failure and n==2 and #s.rows==2 and s.rows[1].name=='Native.GetMoveToPathEx'and s.rows[1].site=='builder-packet'and s.rows[1].argumentCount==2 and s.rows[2].failed)")

    def test_capacity_dropped_parent_does_not_overwrite_child_metadata(self):
        self.each("local f=Wrap('Lua/BaiqiController.lua:1:ReadBack',function(a,b)Time=Time+.001;return a+b end);local root=Wrap('Lua/BaiqiController.lua:2:BaiqiController.RunNow',function()return f(3,4)end);assert(API.Arm(0,85));Turn=86;assert(API.Anchor(0,86));assert(root(true)==7);local s=API.Read();assert(#s.rows==1 and s.dropped==1 and s.rows[1].name:match('ReadBack$')and s.rows[1].argumentCount==2 and s.rows[1].allowOrders==nil)",capacity=1)

    def test_arm_anchors_stop_retire_and_read_snapshots_are_strict(self):
        self.each("assert(not API.Arm(1,85)and not API.Arm(0,true)and not API.Arm(0,84));Player=1;assert(not API.Arm(0,85));Player=0;assert(API.Arm(0,85)and not API.Arm(0,85));assert(not API.Anchor(0,86));Turn=86;assert(API.Anchor(0,86));assert(not API.Anchor(0,86)and API.Read().anchorErrors==1);local old=API.Read();old.anchors[86]=-99;assert(API.Read().anchors[86]==100);assert(API.Stop()and not API.Anchor(0,86)and not API.Arm(0,85));assert(API.Retire()and API.Retire()and API.Read().retired)")

    def test_bad_clock_does_not_change_function_or_fake_a_valid_sample(self):
        self.each("ClockBad=true;assert(not API.Arm(0,85)and not API.Read().used);ClockBad=false;assert(API.Arm(0,85));Turn=86;assert(API.Anchor(0,86));local n=0;local f=Wrap('Lua/BaiqiController.lua:1:Tick',function()n=n+1;return nil,false end);ClockBad=true;local a,b=f();local s=API.Read();assert(a==nil and b==false and n==1 and s.gateErrors==1 and s.totalCalls==0 and #s.rows==0)")

    def test_zero_success_and_after_stop_native_passthrough_are_not_retried(self):
        self.each("assert(API.Arm(0,85));Turn=86;assert(API.Anchor(0,86));local n=0;local function f(...)n=n+1;return ... end;local r=Pack(API.Path('builder-packet',f,nil,false,7,nil));assert(r.n==4 and n==1 and API.Read().zeroSuccess==1 and API.Read().totalCalls==1 and #API.Read().rows==0);assert(API.Stop());API.Path('builder-packet',f,2);assert(n==2 and API.Read().totalCalls==1)")

    def test_all_five_real_callsite_forwarders_keep_current_binding_and_getter_order(self):
        for VM in(L51,L53):
            with self.subTest(VM=VM.__module__):
                lua=self.runtime(VM)
                lua.globals().Parts=lua.execute(build.native_path_source(RAW))
                lua.execute("assert(API.Arm(0,85));Turn=86;assert(API.Anchor(0,86));Calls=0;local unit={};local function second(u,index)assert(u==unit and index==43);Calls=Calls+1;Time=Time+.01;return 'second'end;local function first(u,index)assert(u==unit and index==43);Calls=Calls+1;Time=Time+.01;return 'first'end;UnitManager={GetMoveToPathEx=first};local target={GetIndex=function()UnitManager.GetMoveToPathEx=second;return 43 end};assert(Parts.Step(unit,target)=='first'and Calls==1 and UnitManager.GetMoveToPathEx==second);local ok,result=Parts.Packet(unit,43);assert(ok and result=='second');ok,result=Parts.Choice(unit,{index=43});assert(ok and result=='second');ok,result=Parts.Edge(unit,43);assert(ok and result=='second');ok,result=Parts.District(unit,{endpoint=43});assert(ok and result=='second'and Calls==5 and UnitManager.GetMoveToPathEx==second);local s=API.Read();assert(#s.rows==5 and s.rows[1].site=='path-step'and s.rows[2].site=='builder-packet'and s.rows[3].site=='overlap-choice'and s.rows[4].site=='overlap-edge'and s.rows[5].site=='district-route')")

    def test_missing_duplicate_or_reserved_callsite_is_rejected(self):
        for _,before,_ in build.NATIVE_SITES:
            for raw in(RAW.replace(before,'changed',1),RAW+'\n'+before):
                with self.subTest(before=before),self.assertRaises(ValueError):build.native_path_source(raw)
        with self.assertRaises(ValueError):build.native_path_source(RAW+'\n-- P6PerfWindow184')

    def test_selected_original_error_object_is_raised_once_and_retained(self):
        self.each("local n=0;local failure={};local f=Wrap('Lua/BaiqiController.lua:1:Tick',function()n=n+1;Time=Time+.01;error(failure,0)end);assert(API.Arm(0,85));Turn=86;assert(API.Anchor(0,86));local ok,why=pcall(f);local s=API.Read();assert(not ok and why==failure and n==1 and #s.rows==1 and s.rows[1].failed and s.totalCalls==1)")

    def test_unknown_context_still_calls_original_without_invented_timing(self):
        self.each("local n=0;local f=Wrap('Lua/BaiqiController.lua:1:Tick',function()n=n+1;return 7 end);assert(API.Arm(0,85));Turn=86;assert(API.Anchor(0,86));Player='0';assert(f()==7);local s=API.Read();assert(n==1 and s.metadataErrors==1 and s.totalCalls==0 and #s.rows==0)")

    def test_constructor_rejects_sparse_names_bad_caps_and_other_calendars(self):
        for VM in(L51,L53):
            with self.subTest(VM=VM.__module__):
                lua=VM(unpack_returned_tuples=True)
                lua.globals().Factory=lua.execute((ROOT/'tools/lua/diagnostic_windowed_selected.lua').read_text())
                lua.globals().Profile=lua.execute('local unpack=unpack or table.unpack\n'+(ROOT/'tools/lua/diagnostic_profile.lua').read_text())
                lua.execute("local function C()return 0 end;for _,cap in ipairs({0,-1,2049,1.5,true})do assert(not pcall(Factory,Profile,C,C,C,{'Tick'},cap,86,87))end;for _,names in ipairs({{}, {'Tick','Tick'}, {[1]='Tick',[3]='ReadBack'}, {Tick=true}, {'Bad:method'},'Tick'})do assert(not pcall(Factory,Profile,C,C,C,names,4,86,87))end;for _,pair in ipairs({{85,87},{86,88},{true,87},{86,87.5},{0,1}})do assert(not pcall(Factory,Profile,C,C,C,{'Tick'},4,pair[1],pair[2]))end")

    def test_real184_package_and_frozen183_helpers(self):
        for name in('tools/lua/diagnostic_profile.lua','tools/lua/diagnostic_owned_roots.lua',
                     'tools/lua/diagnostic_selected_nested.lua','tools/build_selected_nested_profile_mod.py'):
            original=subprocess.check_output(['git','show','f0340690442232039db7327f646cadc270b43792:'+name],cwd=ROOT)
            self.assertEqual((ROOT/name).read_bytes(),original)
        with tempfile.TemporaryDirectory(dir=ROOT/'.local-model')as temp:
            result=build.build(Path(temp)/'windowed')
            self.assertEqual((result['source_version'],result['files'],result['Lua_sources_compiled_each_VM']),(184,123,101))
            self.assertEqual(len(result['selected_functions']),27)
            self.assertEqual(len(result['Native_path_sites']),5)
            self.assertEqual(result['changed_files'],['Lua/BaiqiController.lua'])
            self.assertTrue(result['actual_transform_and_ZIP_verified'])
            self.assertFalse(result['installed']or result['acceptance_budget_credit'])

if __name__=='__main__':unittest.main()
