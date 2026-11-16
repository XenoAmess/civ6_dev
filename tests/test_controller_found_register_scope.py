"""Keep private diagnostic locals off the real product's main register frame."""
import unittest
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from tools import build_controller_diagnostic as d
from test_controller_found_writer_timing import WORLD

CHILDREN=('ProcessSettler','SettlementHeld','ExpansionStable','SettlerGoalBridge','KnownExpansionSupport','SettlementSites','PathStep','Safe','SettlerOccupiedDetour','RequestCivilian','SettlementBridge','FoundingSite')
OPTIONS=dict(children=CHILDREN,source_version=157,include_pre_observer=True,native_path_timing=True,detour_native_timing=True,include_turn90=True,found_native_timing=True)


def main_stack(raw):
    lua=L51(encoding=None);dump=lua.eval(b'function(s)return string.dump(assert(loadstring(s)))end');data=dump(raw)
    assert data[:6]==b'\x1bLua\x51\x00'
    order='little'if data[6]else'big';size_t=data[8];length=int.from_bytes(data[12:12+size_t],order)
    offset=12+size_t+length+2*data[7]
    return data[offset+3]


class FoundRegisterScopeTests(unittest.TestCase):
    def test_full_actual_private_main_frame_stays_near_original(self):
        raw=(d.ROOT/'mod/Baiqi/Lua/BaiqiController.lua').read_bytes()
        private=d.found_writer_source(d.instrument_detour_paths(d.native_path_source(raw)))+d.suffix(**OPTIONS).encode()
        # Four private lexical passthrough cells plus closure invocation, without
        # allocating the diagnostic owner's declarations on the product frame.
        self.assertLessEqual(main_stack(private),main_stack(raw)+6)

    def test_all16_outer_cells_are_wrapped_and_restored_after_a_tail_call(self):
        for engine in(L51,L53):
            with self.subTest(engine=engine.__module__):
                lua=engine(unpack_returned_tuples=True);lua.execute(WORLD)
                code=''
                for name in CHILDREN:code+=f'local function {name}(...)T.calls=T.calls+1;return false,nil,9,nil end\n'
                helpers=[d.NATIVE_PATH_HELPER,*[x[0]for x in d.DETOUR_HELPERS],d.FOUND_WRITER_HELPER]
                for name in helpers:code+=f'local function {name}(fn,...)return fn(...)end\n'
                code+='local function Native(...)T.calls=T.calls+1;return false,nil,9,nil end\nBaiqiController={RunNow=function(...)\n'
                for name in CHILDREN:code+=name+'(...)\n'
                for name in helpers[:-1]:code+=name+'(Native,...)\n'
                code+='return '+helpers[-1]+'(Native,...)end}\n'
                code+='local function Tail()T.tail=(T.tail or 0)+1 end;Tail()\n'
                code+=d.suffix(**OPTIONS)
                code+='''local h=P6ControllerNested;assert(T.tail==1 and #h.bindings==17 and h.SetEnabled(true))
local cached=BaiqiController.RunNow
local function check(...)assert(select('#',...)==4);local a,b,c,e=...;assert(a==false and b==nil and c==9 and e==nil)end
check(cached(false,nil,7));assert(T.calls==16 and h.serial==1 and #h.profile.samples==17 and h.errors==0)
local seen={};for _,r in ipairs(h.profile.samples)do assert(r.rootId==1);seen[r.name]=true end
assert(seen['ProcessSettler']and seen['SettlementBridge']and seen['Native.FoundRequestOperation']and seen['Native.DetourChoicePath'])
local ok,same=h.Restore();assert(ok and #same==17);for _,v in ipairs(same)do assert(v)end
check(cached(false,nil,7));assert(T.calls==32 and #h.profile.samples==17 and #T.callbacks==0)
'''
                lua.execute(code)


if __name__=='__main__':unittest.main()
