from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
ROOT=Path(__file__).resolve().parents[1]
class SelectedNestedDiagnostic(unittest.TestCase):
 def runtime(self,VM,capacity=8,clock='Clock'):
  l=VM(unpack_returned_tuples=True);l.execute('Turn=85;Player=0;Time=0;function Clock()Time=Time+0.001;return Time end;function BadClock()error("clock",0)end;function ZeroClock()return 0 end;function ReadTurn()return Turn end;function ReadPlayer()return Player end')
  make=l.execute((ROOT/'tools/lua/diagnostic_selected_nested.lua').read_text(encoding='utf-8'));profile=l.execute('local unpack=unpack or table.unpack\n'+(ROOT/'tools/lua/diagnostic_profile.lua').read_text(encoding='utf-8'));wrap,api=make(profile,l.globals()[clock],l.globals().ReadTurn,l.globals().ReadPlayer,l.table_from(['Tick','ReadBack','BaiqiController.RunNow']),capacity);l.globals().Wrap=wrap;l.globals().API=api;return l
 def each(self,code,**kw):
  for VM in (L51,L53):
   with self.subTest(VM=VM.__module__):self.runtime(VM,**kw).execute(code)
 def test_disabled_and_unselected_preserve_identity_and_nil_arity(self):
  self.each("local calls=0;local function fn(...)calls=calls+1;return ... end;assert(Wrap('Else.lua:1:Tick',fn)==fn and Wrap('Lua/BaiqiController.lua:1:Other',fn)==fn);local wrapped=Wrap('Lua/BaiqiController.lua:1:Tick',fn);local function Pack(...)return {n=select('#',...),...}end;local r=Pack(wrapped(nil,false,7,nil));assert(calls==1 and r.n==4 and r[1]==nil and r[2]==false and r[3]==7 and r[4]==nil and API.Read().totalCalls==0)")
 def test_nested_children_and_parent_have_separate_actual_rows(self):
  self.each("local inner=Wrap('Lua/BaiqiController.lua:1:ReadBack',function(...)return ... end);local root=Wrap('Lua/BaiqiController.lua:2:BaiqiController.RunNow',function(...)return inner(nil,false,7,nil)end);assert(API.Arm(0,85));Turn=86;local function Pack(...)return{n=select('#',...),...}end;local r=Pack(root(true));assert(r.n==4 and r[1]==nil and r[2]==false and r[3]==7 and r[4]==nil);local s=API.Read();assert(#s.rows==2 and s.totalCalls==2 and s.dropped==0 and s.rows[1].name:match('ReadBack$')and s.rows[2].name:match('RunNow$'));assert(s.rows[1].argumentCount==4 and s.rows[2].argumentCount==1 and s.rows[2].allowOrders=='true'and s.rows[1].turnStart==86 and s.rows[2].turnEnd==86);assert(s.rows[2].started<=s.rows[1].started and s.rows[2].ended>=s.rows[1].ended)")
 def test_original_error_once_and_failure_row_are_preserved(self):
  self.each("local calls=0;local fn=Wrap('Lua/BaiqiController.lua:1:Tick',function()calls=calls+1;error('known_error',0)end);assert(API.Arm(0,85));local ok,why=pcall(fn);assert(not ok and why=='known_error'and calls==1);local s=API.Read();assert(#s.rows==1 and s.rows[1].failed and s.totalCalls==1)")
 def test_capacity_drops_parent_without_overwriting_child_metadata(self):
  self.each("local child=Wrap('Lua/BaiqiController.lua:1:ReadBack',function(a,b)return a+b end);local root=Wrap('Lua/BaiqiController.lua:2:BaiqiController.RunNow',function(x)return child(33,44)end);assert(API.Arm(0,85));assert(root(true)==77);local s=API.Read();assert(#s.rows==1 and s.dropped==1 and s.rows[1].name:match('ReadBack$')and s.rows[1].argumentCount==2 and s.rows[1].allowOrders==nil)",capacity=1)
 def test_arm_is_typed_exact_context_and_one_shot(self):
  self.each("assert(not API.Arm(1,85)and not API.Arm(0,true)and not API.Arm(0,84));Player=1;assert(not API.Arm(0,85));Player=0;assert(API.Arm(0,85));assert(not API.Arm(0,85));assert(API.Stop());assert(not API.Read().enabled and API.Read().used);assert(not API.Arm(0,85));assert(API.Retire()and API.Retire());assert(API.Read().retired and not API.Arm(0,85))")
 def test_stop_and_retire_preserve_function_results_and_read_copy(self):
  self.each("local calls=0;local fn=Wrap('Lua/BaiqiController.lua:1:Tick',function(x)calls=calls+1;return x end);assert(API.Arm(0,85));assert(fn(2)==2);local old=API.Read();old.rows[1].name='foreign';assert(API.Read().rows[1].name~='foreign');assert(API.Stop());assert(fn(3)==3 and API.Read().totalCalls==1);assert(API.Retire());assert(fn(4)==4 and calls==3 and API.Read().totalCalls==1)")
 def test_zero_aggregation_and_broken_clock_do_not_change_function(self):
  self.each("local fn=Wrap('Lua/BaiqiController.lua:1:Tick',function()return nil,false,7 end);assert(API.Arm(0,85));local a,b,c=fn();local s=API.Read();assert(a==nil and b==false and c==7 and s.totalCalls==1 and #s.rows==0 and s.zeroSuccess==1 and s.invalidClock==0)",clock='ZeroClock')
  self.each("local fn=Wrap('Lua/BaiqiController.lua:1:Tick',function()return nil,false,7 end);assert(API.Arm(0,85));local a,b,c=fn();local s=API.Read();assert(a==nil and b==false and c==7 and s.totalCalls==1 and #s.rows==0 and s.invalidClock==1)",clock='BadClock')
 def test_constructor_rejects_bad_bounds_and_sparse_or_duplicate_names(self):
  for VM in (L51,L53):
   with self.subTest(VM=VM.__module__):
    l=VM(unpack_returned_tuples=True);l.globals().NewProfile=l.execute('local unpack=unpack or table.unpack\n'+(ROOT/'tools/lua/diagnostic_profile.lua').read_text());l.globals().NewSelected=l.execute((ROOT/'tools/lua/diagnostic_selected_nested.lua').read_text());l.execute("local function C()return 0 end;for _,cap in ipairs({0,-1,513,1.5,true})do assert(not pcall(NewSelected,NewProfile,C,C,C,{'Tick'},cap))end;for _,names in ipairs({{}, {'Tick','Tick'}, {[1]='Tick',[3]='ReadBack'}, {Tick=true}, {'Bad:method'}})do assert(not pcall(NewSelected,NewProfile,C,C,C,names,4))end")
if __name__=='__main__':unittest.main()
