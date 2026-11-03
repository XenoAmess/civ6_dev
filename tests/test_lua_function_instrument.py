from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime
from tools.lua_function_instrument import instrument

ROOT=Path(__file__).resolve().parents[1]


class FunctionInstrumentationTests(unittest.TestCase):
    def runtime(self,source):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''Labels={};Identities={}
function P6OwnWrap(label,fn)
 Labels[#Labels+1]=label
 local wrapped=function(...) return fn(...) end
 Identities[fn]=wrapped;return wrapped
end''')
        result,manifest=instrument(source,'test/fixture.lua')
        lua.execute(result)
        return lua,manifest

    def test_local_recursion_nested_loop_headers_and_repeat_condition(self):
        lua,manifest=self.runtime('''local function factorial(n)
 if n<=1 then return 1 elseif n==2 then return 2 else return n*factorial(n-1) end
end
local n=0
for i=1,(function() return 2 end)() do while n<i do n=n+1 end end
repeat n=n-1 until (function() return n==0 end)()
R=factorial(6);N=n''')
        self.assertEqual((lua.globals().R,lua.globals().N),(720,0))
        self.assertEqual(len(manifest),3)

    def test_named_and_colon_methods_keep_receiver_and_empty_parameters(self):
        lua,_=self.runtime('''A={B={value=9}}
function A.B:Get(...) return self.value,... end
function A.B:Empty() return self.value end
function A.B.Static(x) return x end
R={n=select('#',A.B:Get(false,nil,'tail',nil)),A.B:Get(false,nil,'tail',nil)}
assert(A.B:Empty()==9 and A.B.Static(4)==4)''')
        r=lua.globals().R;self.assertEqual((r.n,r[1],r[2],r[4]),(5,9,False,'tail'))

    def test_strings_comments_and_long_literals_remain_byte_exact(self):
        source='''-- function fake() end
--[==[ function hidden() end ]==]
local s=[=[function ghost() if then end]=]
local q="function \\\" end"; local r='end \\\' function'
F=function(...) return s,q,r,... end -- last function() end
'''
        output,manifest=instrument(source,'literal.lua')
        self.assertEqual(len(manifest),1)
        for line in source.splitlines()[:4]:self.assertIn(line,output)
        lua,_=self.runtime(source);self.assertEqual(lua.globals().F()[0],'function ghost() if then end')

    def test_callback_identity_available_before_native_add_and_remove(self):
        self.runtime('''local registered
Events={E={Add=function(fn) assert(not registered);registered=fn end,
 Remove=function(fn) assert(registered==fn);registered=nil end}}
function OnOpen(...) return ... end
Events.E.Add(OnOpen); Events.E.Remove(OnOpen)
F=OnOpen;assert(F==OnOpen)''')

    def test_error_objects_tail_nil_and_immediate_invocation(self):
        self.runtime('''Error={};F=function(...) return ... end
local function Pack(...) return {n=select('#',...),...} end
local x=Pack(F(1,nil,false,nil));assert(x.n==4 and x[3]==false)
local function Boom() error(Error,0) end
local ok,e=pcall(Boom);assert(not ok and e==Error)
assert((function(x) return x end)(7)==7)''')

    def test_fail_closed_unterminated_blocks_strings_delimiters_and_collision(self):
        for source in ['function F()','function F( end','function A..B() end',
                       'local function A.B() end','repeat end','until true','end',
                       'for i=1,2 end','local x="unfinished','--[==[no close',
                       'local x=[=[no close','function() return ] end','local P6OwnWrap=1']:
            with self.subTest(source=source),self.assertRaises(ValueError):instrument(source,'bad.lua')

    def test_safe_utf8_and_control_label_quoted_for_real_lua(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('function P6OwnWrap(label,fn) Label=label;return fn end')
        output,_=instrument('F=function() end','白绮\x00"\\')
        lua.execute(output);self.assertTrue(lua.globals().Label.startswith('白绮\x00"\\'))

    def test_lua_whitespace_escape_and_escaped_crlf_inside_short_string(self):
        source='local x="a\\z \n  b";local y="x\\\r\ny";F=function() return x,y end'
        lua,manifest=self.runtime(source)
        self.assertEqual(lua.globals().F(),('ab','x\ny'));self.assertEqual(len(manifest),1)

    def test_every_actual_own_source_and_instrumented_copy_compile(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        compile_lua=lua.eval('function(s,n) local f,e=load(s,n);assert(f,e);return true end')
        total=0;files=0
        for path in sorted((ROOT/'mod/Baiqi').rglob('*.lua')):
            source=path.read_text(encoding='utf-8-sig');name=path.relative_to(ROOT).as_posix()
            compile_lua(source,name)
            result,manifest=instrument(source,name)
            compile_lua('local P6OwnWrap=function(_,fn) return fn end\n'+result,name+'-diagnostic')
            total+=len(manifest);files+=1
        self.assertGreater(files,60);self.assertGreater(total,500)


if __name__=='__main__':unittest.main()
