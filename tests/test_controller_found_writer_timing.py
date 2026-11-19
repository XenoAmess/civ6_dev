"""Private founding pcall timing keeps the stored writer and original call contract."""
from pathlib import Path
import hashlib,itertools,json,tempfile,unittest
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from tools import build_controller_diagnostic as diagnostic
from test_controller_native_path_timing import FINE

RAW=b'''local function RequestCivilian(foundingNative,fresh,action,params)
      local called=pcall(foundingNative.writer,fresh,action,params)
  return called
end
'''
WORLD='''unpack=unpack or table.unpack
T={time=100,turn=90,active=true,callbacks={},calls=0}
Automation={GetTime=function()T.time=T.time+.001;return T.time end}
Game={GetCurrentGameTurn=function()return T.turn end,GetLocalPlayer=function()return 0 end}
Players={[0]={IsTurnActive=function()return T.active end,GetCities=function()return{GetCount=function()return 10 end}end}}
Events={PlayerTurnActivated={Add=function(fn)T.callbacks[#T.callbacks+1]=fn end,
Remove=function(fn)for i=#T.callbacks,1,-1 do if T.callbacks[i]==fn then table.remove(T.callbacks,i)end end end}}
UnitManager=setmetatable({},{__index=function(_,key)assert(key=='RequestOperation');return T.native end,
__newindex=function()error('Native binding replaced')end})
'''


class FoundWriterConsumerTests(unittest.TestCase):
    runtime=L51

    def fixture(self,forward=False):
        lua=self.runtime(unpack_returned_tuples=True);lua.execute(WORLD)
        code=diagnostic.found_writer_source(RAW).decode()
        body='_P6ControllerFoundWriter(fn,...)'if forward else'RequestCivilian(fn,...)'
        code+='BaiqiController={RunNow=function(fn,...)return '+body+' end}\n'
        code+=diagnostic.suffix(('RequestCivilian',),source_version=157,include_pre_observer=True,include_turn90=True,found_native_timing=True)
        code+='''return {get=function()return _P6ControllerFoundWriter end,
set=function(fn)_P6ControllerFoundWriter=fn end,
call=function(...)return _P6ControllerFoundWriter(...)end}'''
        lua.globals().Access=lua.execute(code);return lua

    def test_actual_pcall_site_calls_stored_writer_once_and_keeps_identity(self):
        lua=self.fixture();lua.execute('''local h=P6ControllerNested;assert(h.source=='baiqi157-controller-children-v6'and h.SetEnabled(true))
local actor,params={},{};local native=function(u,op,p)T.calls=T.calls+1;assert(u==actor and op==8 and p==params);T.time=T.time+.02;return false end
T.native=native;local captured={writer=UnitManager.RequestOperation}
assert(BaiqiController.RunNow(captured,actor,8,params)==true)
assert(T.calls==1 and captured.writer==native and UnitManager.RequestOperation==native)
assert(h.serial==1 and #h.profile.samples==3 and h.errors==0)
assert(h.profile.samples[1].name=='Native.FoundRequestOperation'and h.profile.samples[1].seconds>=.02)
assert(h.profile.samples[2].name=='RequestCivilian'and h.profile.samples[3].name=='Controller.RunNow')
for _,row in ipairs(h.profile.samples)do assert(row.rootId==1 and row.rootTurn==90 and not row.failed)end
''')

    def test_current_writer_lookup_and_false_void_throw_keep_pcall_semantics(self):
        lua=self.fixture();lua.execute('''local h=P6ControllerNested;assert(h.SetEnabled(true));local actor,params={},{};local lookups=0
local first=function()T.calls=T.calls+1;return false end
local second=function()T.calls=T.calls+1 end
local captured=setmetatable({},{__index=function(_,key)assert(key=='writer');lookups=lookups+1;local fn=T.native;T.native=second;return fn end})
T.native=first;assert(BaiqiController.RunNow(captured,actor,8,params)==true)
assert(lookups==1 and T.calls==1 and UnitManager.RequestOperation==second)
assert(BaiqiController.RunNow(captured,actor,8,params)==true and lookups==2 and T.calls==2)
local failure={};captured={writer=function()T.calls=T.calls+1;error(failure)end}
assert(BaiqiController.RunNow(captured,actor,8,params)==false and T.calls==3)
assert(h.profile.samples[7].failed and not h.profile.samples[8].failed and not h.profile.samples[9].failed and h.errors==0)
''')

    def test_passthrough_arity_nil_errors_disable_and_retired_cached_root(self):
        lua=self.fixture(forward=True);lua.execute('''local h=P6ControllerNested
local fn=function(...)T.calls=T.calls+1;assert(select('#',...)==3);local a,b,c=...;assert(a==false and b==nil and c==17);return false,nil,7,nil end
local function check(...)assert(select('#',...)==4);local a,b,c,d=...;assert(a==false and b==nil and c==7 and d==nil)end
check(BaiqiController.RunNow(fn,false,nil,17));assert(#h.profile.samples==0 and T.calls==1)
assert(h.SetEnabled(true));check(BaiqiController.RunNow(fn,false,nil,17));assert(T.calls==2 and #h.profile.samples==2)
local failure={};local ok,err=pcall(BaiqiController.RunNow,function()T.calls=T.calls+1;error(failure)end)
assert(not ok and err==failure and T.calls==3 and h.currentEntry==nil and h.profile.samples[3].failed and h.profile.samples[4].failed)
local cached=BaiqiController.RunNow;local count=#h.profile.samples;local ok,same=h.Restore();assert(ok and #same==3)
for _,v in ipairs(same)do assert(v)end
assert(Access.get()==h.bindings[3].original and #T.callbacks==0 and not h.SetEnabled(true))
check(cached(fn,false,nil,17));assert(T.calls==4 and #h.profile.samples==count)
''')

    def test_foreign_proxy_and_observer_survive_restore(self):
        lua=self.fixture(forward=True);lua.execute('''local h=P6ControllerNested;local foreign=function()return 19 end;local observer=function()end
Access.set(foreign);T.callbacks[#T.callbacks+1]=observer
local ok,same=h.Restore();assert(ok and same[1]and same[2]and not same[3]and Access.get()==foreign)
assert(#T.callbacks==1 and T.callbacks[1]==observer and BaiqiController.RunNow(function()end)==19)
local ok2,same2=h.Restore();assert(ok2 and same2==same and #h.profile.samples==0)
''')

    def test_capacity_remains_one4096_profile_and_never_replays(self):
        lua=self.fixture();lua.execute('''local h=P6ControllerNested
for i=1,h.profile.capacity-1 do h.profile.samples[i]={name='prior'}end
assert(h.SetEnabled(true));local captured={writer=function()T.calls=T.calls+1 end}
assert(BaiqiController.RunNow(captured,{},8,{})==true and T.calls==1)
assert(h.profile.capacity==4096 and #h.profile.samples==4096 and h.profile.totalCalls==3 and h.profile.dropped==2)
assert(h.profile.samples[4096].name=='Native.FoundRequestOperation'and h.errors>0)
''')


class FoundWriterLua53Tests(FoundWriterConsumerTests):runtime=L53


class FoundWriterArtifactTests(unittest.TestCase):
    def test_current_eight_defaults_keep_independent_frozen_bytes(self):
        rows=[]
        for path,detour,turn90 in itertools.product((False,True),repeat=3):
            options=dict(source_version=157,include_pre_observer=True,native_path_timing=path,detour_native_timing=detour,include_turn90=turn90)
            raw=diagnostic.suffix(**options);self.assertEqual(raw,diagnostic.suffix(**options,found_native_timing=False))
            rows.append([path,detour,turn90,hashlib.sha256(raw.encode()).hexdigest()])
        self.assertEqual(hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest(),'d7c9385be55ec8cdd829faf2aad249ec35d8622b7a2993059c959c031ed8ab2c')

    def test_recovery_rejects_missing_duplicate_and_reserved_anchors(self):
        private=diagnostic.found_writer_source(RAW);self.assertEqual(diagnostic.recover_found_writer_source(private),RAW)
        for raw in(RAW.replace(b'pcall(foundingNative.writer',b'pcall(other.writer'),RAW+RAW,RAW.replace(b'local function RequestCivilian(',b'local function Other('),RAW+b'-- _P6ControllerFoundWriter'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):diagnostic.found_writer_source(raw)
        with self.assertRaises(ValueError):diagnostic.recover_found_writer_source(private+b'-- _P6ControllerFoundWriter')

    def test_invalid_exact_flags_scope_and_versions_refuse_before_output(self):
        with tempfile.TemporaryDirectory(dir=diagnostic.ROOT/'.local-model')as temp:
            for i,value in enumerate((None,0,1,'true',[],{})):
                with self.assertRaises(ValueError):diagnostic.suffix(source_version=157,include_pre_observer=True,found_native_timing=value)
                out=Path(temp)/str(i)
                with self.assertRaises(ValueError):diagnostic.build(out,include_pre_observer=True,found_native_timing=value)
                self.assertFalse(out.exists())
            for version,pre in((156,True),(999,True),(157,False),(157.0,True),(True,True)):
                with self.assertRaises(ValueError):diagnostic.suffix(source_version=version,include_pre_observer=pre,found_native_timing=True)
            out=Path(temp)/'no-scope'
            with self.assertRaises(ValueError):diagnostic.build(out,found_native_timing=True)
            self.assertFalse(out.exists())

    def test_real_combined_package_has_one_profile_and_exact_release_recovery(self):
        source=diagnostic.ROOT/'mod/Baiqi';raw=(source/'Lua/BaiqiController.lua').read_bytes()
        with tempfile.TemporaryDirectory(dir=diagnostic.ROOT/'.local-model')as temp:
            options=dict(children=FINE,include_pre_observer=True,native_path_timing=True,detour_native_timing=True,include_turn90=True,found_native_timing=True)
            out=Path(temp)/'all';d=diagnostic.build(out,**options)
            self.assertEqual((d['source_version'],d['mode'],d['binding_count']),(171,'baiqi171-controller-children-v6',17))
            self.assertEqual((d['sample_capacity'],d['profile_count']),(4096,1));self.assertEqual(d['changed_files'],['Lua/BaiqiController.lua'])
            self.assertTrue(d['release_text_recovers_exactly']and d['lua51_compiled']and d['lua53_compiled']);self.assertFalse(d['native_global_binding_modified'])
            suffix=diagnostic.suffix(source_version=171,**options).encode();private=(out/'Baiqi/Lua/BaiqiController.lua').read_bytes();self.assertTrue(private.endswith(suffix))
            recovered=diagnostic.recover_found_writer_source(private[:-len(suffix)])
            recovered=diagnostic.recover_native_path_source(diagnostic.recover_detour_paths(recovered))
            self.assertEqual(recovered,raw);self.assertEqual((source/'Lua/BaiqiController.lua').read_bytes(),raw)


if __name__=='__main__':unittest.main()
