from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]


class CultureWriteInstallTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().Counter=self.lua.execute((ROOT/'tools/lua/diagnostic_queries.lua').read_text(encoding='utf-8'))
        self.lua.globals().Install=self.lua.execute((ROOT/'tools/lua/diagnostic_culture_write_install.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
Calls={getter=0,writes=0,reads=0,bucket=0};Bucket={};NativeError={sentinel=true}
function Pack(...) return {n=select('#',...),...} end
function MakeCulture(tag)
 local c={tag=tag}
 local function write(self,...)
  assert(self==c,'native culture receiver');Calls.writes=Calls.writes+1;Calls.writeArgs=Pack(...)
  if ThrowNative then error(NativeError,0) end
  return false,nil,'tail',nil
 end
 c.RequestChangeGovernment=write;c.SetGovernmentChangeConsidered=write;c.RequestPolicyChanges=write
 c.GetCurrentGovernment=function(self,...) assert(self==c);Calls.reads=Calls.reads+1;return tag,nil,'read-tail',nil end
 return c
end
Culture=MakeCulture('first');Player={tag='player'}
Player.GetCulture=function(self,...)
 assert(self==Player);Calls.getter=Calls.getter+1;Calls.getterArgs=Pack(...)
 if GetterError then error(NativeError,0) end
 return Culture,nil,99,nil
end
Player.IsHuman=function(self) assert(self==Player);return true end
Other={tag='foreign'};NativePlayers={[0]=Player,[1]=Other};Env={Players=NativePlayers}
function GetBucket() Calls.bucket=Calls.bucket+1;if BucketError then error(NativeError,0) end;return Bucket end
function Start(counter) State=Install(Env,counter or Counter,GetBucket,0) end
function Total() local n=0;for _,s in ipairs(State.stats.counters) do n=n+s.totalCalls end;return n end
''')

    def test_lazy_selected_player_and_real_native_read_receivers(self):
        self.lua.execute('''
Start();assert(Calls.getter==0 and Calls.writes==0 and Calls.bucket==0)
assert(Env.Players[1]==Other and Env.Players[2]==nil and NativePlayers[0]==Player)
local p=Env.Players[0];assert(p~=Player and p==Env.Players[0] and p:IsHuman() and p.tag=='player')
local c=p:GetCulture();local r=Pack(c:GetCurrentGovernment())
assert(c~=Culture and c.tag=='first' and r.n==4 and r[1]=='first' and r[4]==nil)
assert(Calls.reads==1 and Total()==0 and Calls.bucket==0)
''')

    def test_getter_and_all_three_writers_preserve_nil_arity_and_returns(self):
        self.lua.execute('''
Start();local result=Pack(Env.Players[0]:GetCulture('a',nil,'b',nil))
assert(Calls.getter==1 and Calls.getterArgs.n==4 and result.n==4 and result[3]==99 and result[4]==nil)
local c=result[1]
for _,method in ipairs({'RequestChangeGovernment','SetGovernmentChangeConsidered','RequestPolicyChanges'}) do
 local out=Pack(c[method](c,8,nil,'tail',nil))
 assert(out.n==4 and out[1]==false and out[2]==nil and out[3]=='tail' and out[4]==nil)
 assert(Calls.writeArgs.n==4 and Calls.writeArgs[1]==8 and Calls.writeArgs[4]==nil)
 assert(Bucket['Culture.'..method]==1)
end
assert(Calls.writes==3 and Total()==3 and State.stats.counters[1].callbackErrors==0)
''')

    def test_new_native_culture_identity_is_not_replaced_with_stale_cache(self):
        self.lua.execute('''
Start();local p=Env.Players[0];local old=p:GetCulture()
Culture=MakeCulture('second');local current=p:GetCulture()
assert(current~=old and current.tag=='second' and current==p:GetCulture())
assert(State.stats.players==1 and State.stats.cultures==2)
current:SetGovernmentChangeConsidered(true);assert(Total()==1)
''')

    def test_metadata_failure_does_not_block_native_and_native_error_identity_survives(self):
        self.lua.execute('''
Start();local c=Env.Players[0]:GetCulture();BucketError=true
c:RequestPolicyChanges({},{});assert(Calls.writes==1 and Total()==1 and State.stats.counters[1].callbackErrors==1)
BucketError=false;ThrowNative=true
local ok,err=pcall(function() c:RequestChangeGovernment(7) end)
assert(not ok and err==NativeError and Calls.writes==2 and Total()==2)
GetterError=true;local ok2,err2=pcall(function() Env.Players[0]:GetCulture() end)
assert(not ok2 and err2==NativeError)
''')

    def test_missing_method_and_factory_failure_forward_original_getter_tuple(self):
        self.lua.execute('''
Culture.RequestPolicyChanges=nil;Start();local v=Pack(Env.Players[0]:GetCulture())
assert(v.n==4 and v[1]==Culture and v[3]==99 and v[4]==nil and State.stats.missing==1)
assert(State:Restore())
Culture=MakeCulture('ok')
Start(function() error('diagnostic factory failure') end)
local out=Pack(Env.Players[0]:GetCulture())
assert(out.n==4 and out[1]==Culture and out[3]==99 and State.stats.wrapErrors==1 and Calls.writes==0)
''')

    def test_culture_cache_limit_forwards_uninstrumented_original_without_eviction(self):
        self.lua.execute('''
Start();local p=Env.Players[0];local first
for i=1,128 do Culture=MakeCulture(i);local c=p:GetCulture();assert(c~=Culture);if i==1 then first=c end end
Culture=MakeCulture(129);assert(p:GetCulture()==Culture)
assert(State.stats.cultures==128 and State.stats.droppedCultures==1 and #State.stats.counters==128)
first:RequestChangeGovernment(1);assert(Total()==1)
''')

    def test_player_cache_limit_preserves_foreign_and_missing_players(self):
        self.lua.execute('''
Start()
for i=1,16 do NativePlayers[0]={GetCulture=function() return Culture end};assert(Env.Players[0]~=NativePlayers[0]) end
NativePlayers[0]={GetCulture=function() return Culture end};assert(Env.Players[0]==NativePlayers[0])
assert(State.stats.players==16 and State.stats.droppedPlayers==1 and Env.Players[1]==Other)
NativePlayers[0]=nil;assert(Env.Players[0]==nil and State.stats.missing==1)
''')

    def test_restore_stops_even_retained_counter_facades_and_keeps_foreign_binding(self):
        self.lua.execute('''
Start();local players=Env.Players;local p=players[0];local c=p:GetCulture()
c:RequestChangeGovernment(1);assert(Total()==1)
local foreign={};Env.Players=foreign;assert(State:Restore()==false and Env.Players==foreign)
c:RequestChangeGovernment(2);assert(Calls.writes==2 and Total()==1 and Calls.bucket==1)
assert(p:GetCulture()==Culture and players[0]==Player)
''')

    def test_normal_restore_and_invalid_inputs_do_not_dispatch(self):
        self.lua.execute('''
for _,pid in ipairs({-1,1.5,2147483648,math.huge}) do
 local ok=pcall(Install,Env,Counter,GetBucket,pid);assert(not ok and Env.Players==NativePlayers)
end
assert(not pcall(Install,Env,Counter,GetBucket,0/0))
Start();assert(State:Restore() and Env.Players==NativePlayers and not State:Restore())
assert(Calls.getter==0 and Calls.writes==0)
''')


if __name__=='__main__':
    unittest.main()
