"""The diagnostic reader must never replace the UI guard or expose its writer."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/lua/diagnostic_native_unit_reader.lua"
FIXTURE = r'''
local F={calls=0,writes=0}
F.native={RequestOperation=function()F.writes=F.writes+1;error('WRITER_FORBIDDEN')end}
F.native.CanStartOperation=function(...)
 F.calls=F.calls+1;F.args={n=select('#',...),...};if F.onNative then return F.onNative(...)end;return true,nil,false,nil
end
F.proxy=setmetatable({CanStartOperation=function()return false end},{__index=F.native})
F.E={GetGuardManager=function()if F.onManager then F.onManager()end;return F.proxy end,GetMetatable=getmetatable}
return F
'''


class NativeUnitReaderTests(unittest.TestCase):
    def vms(self):
        from lupa.lua51 import LuaRuntime as Lua51
        from lupa.lua53 import LuaRuntime as Lua53
        return (("Lua51", Lua51), ("Lua53", Lua53))

    def make(self, vm):
        v = vm()
        v.globals().M = v.execute(SOURCE.read_text(encoding="utf-8"))
        v.globals().F = v.execute(FIXTURE)
        return v

    def test_only_readonly_native_qualifier_preserves_exact_arity(self):
        for version, vm in self.vms():
            with self.subTest(VM=version):
                v = self.make(vm)
                v.execute(r'''
F.api=M.New(F.E);local before=F.proxy.RequestOperation
assert(F.calls==0 and F.proxy.CanStartOperation({})==false)
local p={x=9,y=9};local actor={};local function packed(...)return{n=select('#',...),...}end
local r=packed(F.api.CanStartOperation(actor,492889976,nil,p,true))
assert(F.calls==1 and F.args.n==5 and F.args[1]==actor and F.args[2]==492889976 and F.args[3]==nil and F.args[4]==p and F.args[5]==true)
assert(r.n==4 and r[1]==true and r[2]==nil and r[3]==false and r[4]==nil)
assert(F.proxy.RequestOperation==before and F.writes==0 and F.api.RequestOperation==nil and F.api.native==nil)
F.onNative=function()end;r=packed(F.api.CanStartOperation());assert(r.n==0 and F.args.n==0)
F.onNative=function()return nil,false,nil end;r=packed(F.api.CanStartOperation(nil));assert(F.args.n==1 and r.n==3 and r[1]==nil and r[2]==false and r[3]==nil)
assert(F.api.Check()and not F.api.State().invalid and F.writes==0)
''')

    def test_changed_ports_reentry_and_unknown_never_rebind(self):
        cases = {
            "manager": "F.proxy=setmetatable({},{__index=F.native})",
            "meta": "setmetatable(F.proxy,{__index=F.native})",
            "index": "getmetatable(F.proxy).__index={CanStartOperation=function()return true end}",
            "qualifier": "F.native.CanStartOperation=function()return true end",
            "getter": "F.E.GetGuardManager=function()return F.proxy end",
            "meta_getter": "F.E.GetMetatable=function(a)return getmetatable(a)end",
            "getter_throws": "F.onManager=function()error('UNKNOWN')end",
            "getter_reentry": "F.onManager=function()pcall(F.api.CanStartOperation)end",
            "native_throws": "F.onNative=function()error('UNKNOWN')end",
            "native_reentry": "F.onNative=function()pcall(F.api.CanStartOperation);return true end",
            "changed_during_read": "F.onNative=function()getmetatable(F.proxy).__index={};return true end",
        }
        for version, vm in self.vms():
            for name, change in cases.items():
                with self.subTest(VM=version, case=name):
                    v = self.make(vm)
                    v.execute("F.api=M.New(F.E)")
                    v.execute(change)
                    v.execute(r'''
assert(not pcall(F.api.CanStartOperation,{},492889976,nil,{},true))
local calls=F.calls;assert(F.api.State().invalid and not F.api.State().busy)
assert(not pcall(F.api.CanStartOperation)and F.calls==calls and F.writes==0)
''')

    def test_unknown_proxy_shape_rejected_before_native_call(self):
        changes = (
            "setmetatable(F.proxy,nil)",
            "setmetatable(F.proxy,{__metatable='locked',__index=F.native})",
            "getmetatable(F.proxy).__index=function()return F.native end",
            "getmetatable(F.proxy).__index=F.proxy",
            "F.native.CanStartOperation=nil",
            "F.native.CanStartOperation=true",
            "F.E.GetMetatable=nil",
        )
        for version, vm in self.vms():
            for change in changes:
                with self.subTest(VM=version, change=change):
                    v = self.make(vm)
                    v.execute(change)
                    v.execute("assert(not pcall(M.New,F.E)and F.calls==0 and F.writes==0)")


if __name__ == "__main__":
    unittest.main()
