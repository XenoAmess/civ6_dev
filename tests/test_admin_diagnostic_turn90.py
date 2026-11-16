"""Explicit private Admin90 diagnosis; preserve default output and real calls."""
from pathlib import Path
import hashlib
import tempfile
import unittest
import subprocess
import sys
from unittest.mock import patch
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from tools import build_admin_diagnostic as builder


class AdminTurn90Tests(unittest.TestCase):
    def fixture(self,engine,enabled):
        lua=engine(unpack_returned_tuples=True)
        code='''unpack=unpack or table.unpack
T={time=100,turn=90,active=true,calls=0,callbacks={}}
Automation={GetTime=function()T.time=T.time+.001;return T.time end}
Game={GetCurrentGameTurn=function()return T.turn end,GetLocalPlayer=function()return 0 end}
Players={[0]={IsTurnActive=function()return T.active end,GetCities=function()return{GetCount=function()return 10 end}end}}
Events={PlayerTurnActivated={Add=function(f)T.callbacks[1]=f end,Remove=function(f)assert(T.callbacks[1]==f);T.callbacks={}end}}
'''
        for name in builder.CHILDREN:code+=f'local function {name}(...)T.calls=T.calls+1;return false,nil,... end\n'
        for name in builder.RUNNERS:code+=f'{name}={{Run=function(...)T.calls=T.calls+1;return false,nil,... end}}\n'
        code+='''BaiqiAdmin={Run=function(...)
Research(...);if T.fail then error('original failure')end
return BaiqiFoodFocusRunner.Run(...)
end}
'''
        lua.execute(code+builder.suffix(source_version=157,include_turn90=enabled))
        return lua

    def test_default_bytes_remain_exact_for_old_and_current_versions(self):
        pins={141:'fc37bbb67d6be95bceafca55df9b719a4882ca09fb260dc3efdd7a672a0850a3',157:'bde61aa6e70cc1a887be2b2492888462022210fc52697a96083fcf761fa25d77'}
        for version,sha in pins.items():
            raw=builder.suffix(source_version=version)
            self.assertEqual(hashlib.sha256(raw.encode()).hexdigest(),sha)
            self.assertEqual(builder.suffix(source_version=version,include_turn90=False),raw)

    def test_explicit90_preserves_preobserver_returns_and_cutoff(self):
        for engine in(L51,L53):
            with self.subTest(engine=engine.__module__):
                lua=self.fixture(engine,True);lua.execute('''
local h=P6AdminNested;assert(h.source=='baiqi157-admin-children-v2'and h.profile.capacity==4096 and #h.bindings==13)
assert(h.SetEnabled(true));local cached=BaiqiAdmin.Run
local function check(...)assert(select('#',...)==4);local a,b,c,d=...;assert(a==false and b==nil and c==9 and d==nil)end
check(cached(9,nil));assert(T.calls==2 and #h.profile.samples==3 and h.serial==1 and next(h.anchors)==nil)
T.callbacks[1](0);local anchor=h.anchors[90];assert(anchor)
check(cached(9,nil));assert(T.calls==4 and #h.profile.samples==6 and h.serial==2)
T.time=anchor+11;check(cached(9,nil));assert(T.calls==6 and #h.profile.samples==6)
assert(h.errors==0 and h.profile.dropped==0 and h.profile.invalidClock==0)
''')

    def test_false_outside_turns_and_inactive_forward_without_samples(self):
        for engine in(L51,L53):
            lua=self.fixture(engine,False);lua.execute('assert(P6AdminNested.SetEnabled(true));BaiqiAdmin.Run();assert(T.calls==2 and #P6AdminNested.profile.samples==0)')
            lua=self.fixture(engine,True);lua.execute('''local h=P6AdminNested;assert(h.SetEnabled(true))
T.turn=86;BaiqiAdmin.Run();T.turn=91;BaiqiAdmin.Run();T.turn=90;T.active=false;BaiqiAdmin.Run()
assert(T.calls==6 and #h.profile.samples==0 and h.serial==0)
''')

    def test_original_errors_are_forwarded_once_and_entry_cleared(self):
        for engine in(L51,L53):
            lua=self.fixture(engine,True);lua.execute('''local h=P6AdminNested;assert(h.SetEnabled(true));T.fail=true
local ok,err=pcall(BaiqiAdmin.Run,9,nil);assert(not ok and tostring(err):find('original failure',1,true))
assert(T.calls==1 and h.currentEntry==nil and h.serial==1 and #h.profile.samples==2)
assert(h.profile.samples[2].failed==true)
''')

    def test_restore_keeps_foreign_bindings_and_captured_calls_passthrough(self):
        for engine in(L51,L53):
            lua=self.fixture(engine,True);lua.execute('''local h=P6AdminNested;assert(h.SetEnabled(true));local cached=BaiqiAdmin.Run
local foreign=function()return 19 end;BaiqiAdmin.Run=foreign;BaiqiFloodPurchase.Run=foreign;BaiqiFoodFocusRunner={Run=foreign}
local ok,same=h.Restore();assert(ok and #same==13 and not same[1]and not same[11]and not same[12]and same[13])
assert(BaiqiAdmin.Run==foreign and BaiqiFloodPurchase.Run==foreign and BaiqiFoodFocusRunner.Run==foreign)
assert(cached()==19 and #h.profile.samples==0 and #T.callbacks==0 and not h.SetEnabled(true))
local ok2,same2=h.Restore();assert(ok2 and same2==same)
''')

    def test_nonexact_flags_and_unsupported_versions_refuse_before_output(self):
        class IntSubclass(int):pass
        with tempfile.TemporaryDirectory(dir=builder.ROOT/'.local-model')as temp:
            for i,value in enumerate((None,0,1,'true',[],{},IntSubclass(1))):
                out=Path(temp)/str(i)
                with self.assertRaises(ValueError):builder.suffix(source_version=157,include_turn90=value)
                with self.assertRaises(ValueError):builder.build(out,include_turn90=value)
                self.assertFalse(out.exists())
            for version in(141,156,160,True,157.0,'157'):
                with self.assertRaises(ValueError):builder.suffix(source_version=version,include_turn90=True)
            with patch.object(builder.ET,'fromstring')as parse:
                parse.return_value.get.return_value='156';out=Path(temp)/'legacy'
                with self.assertRaises(ValueError):builder.build(out,include_turn90=True)
                self.assertFalse(out.exists())

    def test_actual_package_changes_only_admin_and_metadata_is_explicit(self):
        with tempfile.TemporaryDirectory(dir=builder.ROOT/'.local-model')as temp:
            out=Path(temp)/'prepared';d=builder.build(out,include_turn90=True)
            self.assertEqual((d['source_version'],d['mode'],d['files']),(159,'baiqi159-admin-children-v2',119))
            self.assertEqual(d['focus_turns'],[87,88,89,90]);self.assertIs(d['include_turn90'],True)
            self.assertEqual((d['profile_count'],d['sample_capacity']),(1,4096))
            self.assertEqual(d['changed_files'],['Lua/BaiqiAdmin.lua'])
            self.assertTrue(d['lua51_compiled']and d['lua53_compiled']and d['original_admin_exact_prefix'])
            raw=(builder.ROOT/'mod/Baiqi/Lua/BaiqiAdmin.lua').read_bytes()
            self.assertEqual((out/'Baiqi/Lua/BaiqiAdmin.lua').read_bytes(),raw+builder.suffix(source_version=159,include_turn90=True).encode())

    def test_cli_exposes_explicit_turn90_option(self):
        p=subprocess.run([sys.executable,str(builder.ROOT/'tools/build_admin_diagnostic.py'),'--help'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0);self.assertIn('--include-turn90',p.stdout)


if __name__=='__main__':unittest.main()
