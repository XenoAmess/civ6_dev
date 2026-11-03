from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime
from tools.lua_write_instrument import instrument_writes
from tools.lua_function_instrument import instrument

ROOT=Path(__file__).resolve().parents[1]


class WriteInstrumentationTests(unittest.TestCase):
    def test_colon_lookup_before_arguments_and_exact_receiver(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''Order={};Obj=setmetatable({},{__index=function(self,key)
 Order[#Order+1]='lookup';return function(actual,...) assert(actual==Obj);return select('#',...),... end end})
function Arg() Order[#Order+1]='arg';return 4 end
function P6WriteMethod(label,obj,key) local f=obj[key];return function(...) return f(obj,...) end end''')
        out,m=instrument_writes('R={Obj:SetProperty(Arg(),nil,false,nil)}','test.lua')
        lua.execute(out);self.assertEqual(lua.eval("table.concat(Order,',')"),'lookup,arg')
        self.assertEqual((lua.globals().R[1],lua.globals().R[2],lua.globals().R[4]),(4,4,False))
        self.assertEqual(m[0]['kind'],'object_call')

    def test_static_pcall_alias_nonfunction_checks_and_precise_method_pairs(self):
        source='''local f=UnitManager.RequestCommand
pcall(CityManager.TransferCity,city,0)
local available=type(UI.RequestPlayerOperation)=='function'
local native=NativeUnit.RequestOperation
local query=CityManager.FinishMoves
'''
        out,m=instrument_writes(source,'test.lua')
        self.assertEqual(len(m),4);self.assertIn('local query=CityManager.FinishMoves',out)
        self.assertEqual([x['skip_guard'] for x in m],[True,False,True,False])
        LuaRuntime().execute('assert(load(...))',out)

    def test_comments_strings_and_unrelated_calls_unchanged(self):
        source='-- player:SetProperty(1)\nlocal s="UI.RequestPlayerOperation"\nCanStartOperation(unit)\n'
        out,m=instrument_writes(source,'test.lua');self.assertEqual(out,source);self.assertEqual(m,[])

    def test_unsupported_receiver_declaration_assignment_and_collision_fail(self):
        for source in ['p.units:SetProperty(1)','p[0]:SetProperty(1)','Get():SetProperty(1)',
                       'function p:SetProperty(x) end','env.UI.RequestPlayerOperation(1)',
                       'UI.RequestPlayerOperation=f','function UI.RequestPlayerOperation() end',
                       'local P6WriteMethod=1','local P6WriteRef=1']:
            with self.subTest(source=source),self.assertRaises(ValueError):instrument_writes(source,'bad.lua')

    def test_every_actual_source_write_then_function_rewrite_compiles(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        compile_lua=lua.eval('function(s,n) local f,e=load(s,n);assert(f,e);return true end')
        by_file={}
        for p in sorted((ROOT/'mod/Baiqi').rglob('*.lua')):
            name=p.relative_to(ROOT).as_posix()
            text,manifest=instrument_writes(p.read_text(encoding='utf-8-sig'),name)
            text,_=instrument(text,name)
            compile_lua(text,name);by_file[name]=manifest
        gameplay=by_file['mod/Baiqi/Lua/BaiqiGameplay.lua']
        self.assertEqual(sum(x['receiver']=='plot' and x['method']=='SetProperty' for x in gameplay),2)
        self.assertTrue(any(x['receiver']=='unit' and x['method']=='SetProperty' for x in by_file['mod/Baiqi/Lua/BaiqiCapture.lua']))
        self.assertTrue(any(x['receiver']=='CityManager' and x['method']=='TransferCity' for x in by_file['mod/Baiqi/Lua/BaiqiCapture.lua']))
        self.assertTrue(any(x['receiver']=='UI' and x['method']=='RequestPlayerOperation' for x in by_file['mod/Baiqi/UI/BaiqiExecutor.lua']))


if __name__=='__main__':unittest.main()
