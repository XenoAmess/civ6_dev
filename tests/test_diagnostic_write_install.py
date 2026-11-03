from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class WriteInstallTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.counter=self.lua.execute((ROOT/'tools/lua/diagnostic_queries.lua').read_text(encoding='utf-8'))
        self.install=self.lua.execute((ROOT/'tools/lua/diagnostic_write_install.lua').read_text(encoding='utf-8'))
        self.lua.globals().TestCanonicalCounter=self.counter
        self.lua.globals().InstallForTest=self.install
        self.lua.execute('''
TestErrorObject={tag='native-error-object'}
TestCalls={unitOperation=0,unitCommand=0,cityOperation=0,cityCommand=0,playerOperation=0}
TestBucket={};TestBucketCalls=0;TestFactoryCalls=0
TestFailBucket=false;TestNativeError=false
local function native(name)
 return function(...)
  TestCalls[name]=TestCalls[name]+1
  TestLastArgs={n=select('#',...),...}
  if name=='unitOperation' and TestNativeError then error(TestErrorObject,0) end
  return false,nil,'tail',nil
 end
end
Env={UnitManager={RequestOperation=native('unitOperation'),RequestCommand=native('unitCommand')},
 CityManager={RequestOperation=native('cityOperation'),RequestCommand=native('cityCommand')},
 UI={RequestPlayerOperation=native('playerOperation')},extra='keep'}
Originals={UnitManager=Env.UnitManager,CityManager=Env.CityManager,UI=Env.UI}
GetBucket=function()
 TestBucketCalls=TestBucketCalls+1
 if TestFailBucket then error(TestErrorObject,0) end
 return TestBucket
end
''')
        self.env=self.lua.globals().Env
        self.bucket=self.lua.globals().GetBucket

    def installed(self):
        state=self.install(self.env,self.counter,self.bucket)
        self.lua.globals().State=state
        return state


    def test_install_all_groups_without_dispatch_or_bucket_read(self):
        self.installed()
        self.lua.execute("""
for _,name in ipairs({'UnitManager','CityManager','UI'}) do
 assert(Env[name]==State.proxies[name] and Env[name]~=Originals[name])
 assert(State.originals[name]==Originals[name])
 assert(State.stats[name].totalCalls==0 and State.stats[name].callbackErrors==0)
end
assert(Env.extra=='keep' and TestBucketCalls==0)
for _,n in pairs(TestCalls) do assert(n==0) end
""")

    def test_all_five_dispatches_preserve_arguments_nil_returns_and_exact_counts(self):
        self.installed()
        self.lua.execute("""
local function pack(...) return {n=select('#',...),...} end
local r=pack(Env.UnitManager.RequestOperation('unit',99,nil))
assert(r.n==4 and r[1]==false and r[2]==nil and r[3]=='tail' and r[4]==nil)
assert(TestLastArgs.n==3 and TestLastArgs[1]=='unit' and TestLastArgs[2]==99 and TestLastArgs[3]==nil)
Env.UnitManager.RequestCommand('command')
Env.CityManager.RequestOperation('city')
Env.CityManager.RequestCommand('city-command')
Env.UI.RequestPlayerOperation('player')
for _,n in pairs(TestCalls) do assert(n==1) end
assert(State.stats.UnitManager.totalCalls==2 and State.stats.CityManager.totalCalls==2 and State.stats.UI.totalCalls==1)
assert(TestBucket['UnitManager.RequestOperation']==1 and TestBucket['UnitManager.RequestCommand']==1)
assert(TestBucket['CityManager.RequestOperation']==1 and TestBucket['UI.RequestPlayerOperation']==1)
assert(TestBucket['CityManager.RequestCommand']==1)
local count=0;for _ in pairs(TestBucket) do count=count+1 end;assert(count==5)
""")

    def test_bucket_error_still_dispatches_once_and_reports_callback_failure(self):
        state=self.installed()
        self.lua.globals().TestFailBucket=True
        self.assertEqual(self.env.UnitManager.RequestOperation('unit',1,None),(False,None,'tail',None))
        self.assertEqual(self.lua.globals().TestCalls.unitOperation,1)
        self.assertEqual(state.stats.UnitManager.totalCalls,1)
        self.assertEqual(state.stats.UnitManager.callbackErrors,1)

    def test_native_error_object_is_preserved_after_one_actual_target_call(self):
        self.installed()
        self.lua.execute("""
TestNativeError=true
local ok,err=pcall(Env.UnitManager.RequestOperation,'unit',1,nil)
assert(not ok and err==TestErrorObject)
assert(TestCalls.unitOperation==1 and State.stats.UnitManager.totalCalls==1)
assert(State.stats.UnitManager.callbackErrors==0)
""")

    def test_restore_retains_foreign_replacement_and_repeated_restore_is_safe(self):
        self.installed()
        self.lua.execute("""
local foreign={RequestPlayerOperation=function() return 'foreign' end}
Env.UI=foreign
local r=State:Restore()
assert(r.UnitManager and r.CityManager and not r.UI)
assert(Env.UnitManager==Originals.UnitManager and Env.CityManager==Originals.CityManager and Env.UI==foreign)
local again=State:Restore()
assert(not again.UnitManager and not again.CityManager and not again.UI)
assert(Env.UI==foreign and Env.extra=='keep' and TestBucketCalls==0)
""")

    def test_constructor_failure_at_each_stage_never_installs_partial_proxies(self):
        for stage in (1,2,3):
            with self.subTest(stage=stage):
                self.setUp();self.lua.globals().FailStage=stage
                self.lua.execute("""
local function factory(...)
 TestFactoryCalls=TestFactoryCalls+1
 if TestFactoryCalls==FailStage then error(TestErrorObject,0) end
 return TestCanonicalCounter(...)
end
local ok,err=pcall(InstallForTest,Env,factory,GetBucket)
assert(not ok and err==TestErrorObject and TestFactoryCalls==FailStage)
for _,name in ipairs({'UnitManager','CityManager','UI'}) do assert(Env[name]==Originals[name]) end
assert(TestBucketCalls==0 and Env.extra=='keep')
""")
        for malformed in (1,2):
            with self.subTest(malformed=malformed):
                self.setUp();self.lua.globals().Malformed=malformed
                self.lua.execute("""
local function factory(...)
 TestFactoryCalls=TestFactoryCalls+1
 if TestFactoryCalls==3 then
  if Malformed==1 then return nil,{} end
  return {},nil
 end
 return TestCanonicalCounter(...)
end
local ok=pcall(InstallForTest,Env,factory,GetBucket);assert(not ok)
for _,name in ipairs({'UnitManager','CityManager','UI'}) do assert(Env[name]==Originals[name]) end
assert(TestBucketCalls==0)
""")

    def test_invalid_install_arguments_fail_without_mutating_existing_environment(self):
        self.lua.execute("""
assert(not pcall(InstallForTest,nil,TestCanonicalCounter,GetBucket))
for _,bad in ipairs({false,1,'x'}) do
 assert(not pcall(InstallForTest,bad,TestCanonicalCounter,GetBucket))
 assert(not pcall(InstallForTest,Env,bad,GetBucket))
 assert(not pcall(InstallForTest,Env,TestCanonicalCounter,bad))
end
assert(not pcall(InstallForTest,Env,nil,GetBucket))
assert(not pcall(InstallForTest,Env,TestCanonicalCounter,nil))
for _,name in ipairs({'UnitManager','CityManager','UI'}) do assert(Env[name]==Originals[name]) end
assert(TestBucketCalls==0 and Env.extra=='keep')
""")

    def test_missing_native_api_members_fail_before_any_environment_assignment(self):
        for group,method in (('UnitManager','RequestCommand'),('CityManager','RequestOperation'),('CityManager','RequestCommand'),('UI','RequestPlayerOperation')):
            with self.subTest(group=group):
                self.setUp();self.lua.globals().BadGroup=group;self.lua.globals().BadMethod=method
                self.lua.execute("""
Env[BadGroup][BadMethod]=nil
local ok=pcall(InstallForTest,Env,TestCanonicalCounter,GetBucket);assert(not ok)
for _,name in ipairs({'UnitManager','CityManager','UI'}) do assert(Env[name]==Originals[name]) end
assert(TestBucketCalls==0 and Env.extra=='keep')
""")

    def test_city_command_counted_forwarded_and_restored(self):
        self.installed()
        self.lua.execute("""
local function pack(...) return {n=select('#',...),...} end
local r=pack(Env.CityManager.RequestCommand('cmd',10,nil))
assert(r.n==4 and r[1]==false and r[2]==nil and r[3]=='tail' and r[4]==nil)
assert(TestLastArgs.n==3 and TestLastArgs[1]=='cmd' and TestLastArgs[2]==10 and TestLastArgs[3]==nil)
assert(TestCalls.cityCommand==1 and TestCalls.cityOperation==0)
assert(State.stats.CityManager.totalCalls==1)
assert(TestBucket['CityManager.RequestCommand']==1)
local original=Originals.CityManager.RequestCommand
local restored=State:Restore()
assert(restored.CityManager and Env.CityManager==Originals.CityManager)
assert(Env.CityManager.RequestCommand==original)
State=InstallForTest(Env,TestCanonicalCounter,GetBucket)
local foreign={RequestOperation=function() return 'op' end,RequestCommand=function() return 'cmd' end}
Env.CityManager=foreign
local res=State:Restore()
assert(not res.CityManager)
assert(Env.CityManager==foreign)
""")

    def test_unselected_members_forward_without_being_counted_as_writes(self):
        self.lua.execute("Originals.UnitManager.Query=function() return 'query-result' end")
        self.installed()
        self.lua.execute("""
assert(Env.UnitManager.Query==Originals.UnitManager.Query)
assert(Env.UnitManager.Query()=='query-result')
assert(State.stats.UnitManager.totalCalls==0 and TestBucketCalls==0)
""")


    def test_virtual_environment_bindings_restore_current_context_references(self):
        self.lua.execute("""
local slots={UnitManager=Originals.UnitManager,CityManager=Originals.CityManager,UI=Originals.UI}
local writes={}
local env=setmetatable({}, {
 __index=function(_,key) assert(slots[key]~=nil);return slots[key] end,
 __newindex=function(_,key,value)
  assert(key=='UnitManager' or key=='CityManager' or key=='UI')
  writes[#writes+1]=key;slots[key]=value
 end})
local state=InstallForTest(env,TestCanonicalCounter,GetBucket)
assert(#writes==3 and slots.UnitManager==state.proxies.UnitManager and slots.UI==state.proxies.UI)
local foreign={};slots.UI=foreign
local result=state:Restore()
assert(result.UnitManager and result.CityManager and not result.UI and #writes==5)
assert(slots.UnitManager==Originals.UnitManager and slots.CityManager==Originals.CityManager and slots.UI==foreign)
for _ in pairs(env) do error('Facade stored a raw field instead of binding the context') end
assert(TestBucketCalls==0)
""")

    def test_virtual_environment_constructor_failure_performs_no_bound_assignment(self):
        self.lua.execute("""
local slots={UnitManager=Originals.UnitManager,CityManager=Originals.CityManager,UI=Originals.UI}
local writes=0
local env=setmetatable({}, {
 __index=function(_,key) return slots[key] end,
 __newindex=function(_,key,value) writes=writes+1;slots[key]=value end})
local function factory(...)
 TestFactoryCalls=TestFactoryCalls+1
 if TestFactoryCalls==3 then error(TestErrorObject,0) end
 return TestCanonicalCounter(...)
end
local ok,err=pcall(InstallForTest,env,factory,GetBucket)
assert(not ok and err==TestErrorObject and TestFactoryCalls==3 and writes==0)
for _,name in ipairs({'UnitManager','CityManager','UI'}) do assert(slots[name]==Originals[name]) end
assert(TestBucketCalls==0)
""")


if __name__=='__main__':
    unittest.main()
