"""Protect real native query behavior and the diagnostic report contract."""
from pathlib import Path
import unittest

from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class QualificationTimingTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
            unpack=table.unpack;table.pack=nil;table.unpack=nil;debug=nil
            function Pack(...) return {n=select('#',...),...} end
            function Clock() ticks=ticks+1;return ticks/1000 end
            ticks=0;calls=0
            function Native(...) calls=calls+1;return ... end
        ''')
        self.lua.globals().NewProfile = self.lua.execute(
            (ROOT / 'tools/lua/diagnostic_profile.lua').read_text(encoding='utf-8'))
        self.install = self.lua.execute(
            (ROOT / 'tools/lua/diagnostic_qualification.lua').read_text(encoding='utf-8'))
        self.configure()

    def configure(self, native='Native', clock='Clock'):
        self.lua.execute('s={managerProxy={CanStartOperation=' + native
                         + ',CanStartCommand=' + native + '},currentEntry={}}')
        self.install(self.lua.globals().s, self.lua.globals().NewProfile, self.lua.eval(clock))

    def check(self, code):
        self.lua.execute(code)

    def test_all_arguments_and_results_include_nil_holes(self):
        self.check('''
            local r=Pack(s.managerProxy.CanStartOperation(false,2,nil,4,nil))
            assert(r.n==5 and r[1]==false and r[2]==2 and r[3]==nil and r[5]==nil)
            assert(calls==1 and s.currentEntry.qual.CanStartOperation.samples==1)
        ''')

    def test_boolean_and_actual_result_table_keep_identity(self):
        self.check('''
            local object={};local a,b=s.managerProxy.CanStartCommand(true,object)
            assert(a==true and b==object and calls==1)
        ''')

    def test_no_returns_remain_zero_returns(self):
        self.configure('function() calls=calls+1 end')
        self.check('assert(Pack(s.managerProxy.CanStartOperation()).n==0 and calls==1)')

    def test_error_identity_is_preserved_and_native_is_not_replayed(self):
        self.check('NativeError={}')
        self.configure('function() calls=calls+1;error(NativeError,0) end')
        self.check('''
            local ok,err=pcall(s.managerProxy.CanStartOperation)
            assert(not ok and err==NativeError and calls==1)
            assert(s.currentEntry.qual.CanStartOperation.samples==1 and s.qualProfile.samples[1].failed)
        ''')

    def test_outside_formal_entry_has_no_clock_or_profile_calls(self):
        self.check('''
            s.currentEntry=nil;local a,b=s.managerProxy.CanStartOperation(false,7)
            assert(a==false and b==7 and calls==1 and ticks==0 and s.qualProfile.totalCalls==0)
        ''')

    def test_invalid_clock_is_unknown_and_does_not_suppress_query(self):
        self.configure(clock="function() error('clock unavailable') end")
        self.check('''
            assert(s.managerProxy.CanStartCommand(9)==9 and calls==1)
            local q=s.currentEntry.qual.CanStartCommand
            assert(q.unknown==1 and q.samples==0 and q.seconds==0 and s.qualProfile.invalidClock==1)
        ''')

    def test_capacity_preserves_all_calls_and_marks_unmeasured_intervals(self):
        self.check('''
            for i=1,4097 do assert(s.managerProxy.CanStartOperation(i)==i) end
            local q=s.currentEntry.qual.CanStartOperation
            assert(calls==4097 and s.qualProfile.dropped==1 and q.samples==4096 and q.unknown==1)
        ''')

    def test_report_can_read_the_same_profile_metadata(self):
        self.check('''
            s.managerProxy.CanStartOperation(true,{})
            assert(s.qualProfile.totalCalls==1 and s.qualProfile.invalidClock==0 and s.qualProfile.dropped==0)
            assert(s.currentEntry.qual.CanStartOperation.seconds>0)
        ''')

    def test_each_root_gets_its_own_qualification_bucket(self):
        self.check('''
            s.managerProxy.CanStartOperation(1);local first=s.currentEntry
            s.currentEntry={};s.managerProxy.CanStartCommand(2)
            assert(first.qual.CanStartOperation.samples==1 and first.qual.CanStartCommand==nil)
            assert(s.currentEntry.qual.CanStartOperation==nil and s.currentEntry.qual.CanStartCommand.samples==1)
        ''')

    def test_module_does_not_require_a_caller_pack_function(self):
        self.check('''
            pack=nil;local a,b,c=s.managerProxy.CanStartOperation(true,nil,3)
            assert(a==true and b==nil and c==3 and calls==1)
        ''')


if __name__ == '__main__':
    unittest.main()
