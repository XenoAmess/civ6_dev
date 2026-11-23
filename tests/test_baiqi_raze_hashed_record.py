"""Engine 1.0.12.74 saved kind-key shape; no save mutation or Native grant."""
from pathlib import Path
import sys,unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
import test_baiqi_raze_choice as contracts
ROOT=contracts.ROOT
HASH=r"DB={MakeHash=function(s)assert(s=='kind');return -1002749146 end};E.HashString=DB.MakeHash;API=assert(BaiqiRazeChoiceCore.Create(C,E))"
NATIVE=r'''
W.city=false
W.nativeSaved={version=1,owner=0,cityID=917516,plot=862,x=26,y=19,turn=131,
 [-1002749146]='PLAYER_RAZE_CHOICE'}
E.Map.GetGridSize=function()return 44,26 end
E.Map.GetPlotByIndex=function(n)return{
 GetIndex=function()return n end,GetX=function()return n%44 end,
 GetY=function()return math.floor(n/44)end,
 IsCity=function()return false end,GetOwner=function()return -1 end,
 GetProperty=function()W.reads=W.reads+1;if n==862 then return W.nativeSaved end end,
 SetProperty=function()W.writes=W.writes+1;error('READ_MUST_NOT_REWRITE_SAVED_RECORD')end}
end
API=assert(BaiqiRazeChoiceCore.Create(C,E))
'''

class HashedSavedRazeRecord(unittest.TestCase):
    def each(self,body):
        for factory in (Lua51,Lua53):
            with self.subTest(vm=factory.__module__):
                lua=factory(unpack_returned_tuples=True)
                lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiRazeChoiceCore.lua').read_text(encoding='utf-8'))
                lua.execute(contracts.WORLD);lua.execute(HASH)
                self.assertTrue(lua.execute('return(function()\n'+body+'\nreturn true end)()'))

    def test_actual_native_saved_eight_fields_read_canonically_without_rewrite(self):
        self.each(NATIVE+r'''
local original=W.nativeSaved;local s,b,r,v=API.Read(0,862,26,19)
assert(s=='READY'and b==true and r=='player_raze_choice','ACTUAL_HASHED_NATIVE_RECORD_REJECTED')
assert(v.kind=='PLAYER_RAZE_CHOICE'and v.owner==0 and v.cityID==917516 and v.turn==131)
v.cityID=1;assert(W.nativeSaved==original and original.cityID==917516 and original.kind==nil)
assert(original[-1002749146]=='PLAYER_RAZE_CHOICE'and W.writes==0)
''')

    def test_repeated_choice_accepts_existing_hashed_record_without_second_write(self):
        self.each(r'''
assert(Remember()=='READY'and W.writes==1)
local raw=W.properties[21];raw[DB.MakeHash('kind')]=raw.kind;raw.kind=nil
API=assert(BaiqiRazeChoiceCore.Create(C,E))
local s,v,r=Remember()
assert(s=='READY'and v.kind=='PLAYER_RAZE_CHOICE'and v.cityID==917516 and r=='already_recorded')
assert(W.writes==1 and W.properties[21]==raw and raw.kind==nil)
''')

    def test_alias_duplicates_wrong_hash_or_wrong_identity_remain_unavailable(self):
        changes=["W.nativeSaved.kind='PLAYER_RAZE_CHOICE'", "W.nativeSaved[-1002749145]=W.nativeSaved[-1002749146];W.nativeSaved[-1002749146]=nil", "W.nativeSaved[-1002749146]='OTHER'", "W.nativeSaved.owner=1", "W.nativeSaved.turn=132", "W.nativeSaved.version=2", "W.nativeSaved.extra=true"]
        for change in changes:
            with self.subTest(change=change):
                self.each(NATIVE+change+";local raw=W.nativeSaved;assert(API.Read(0,862,26,19)=='UNAVAILABLE');assert(W.nativeSaved==raw and W.writes==0)")

    def test_missing_throwing_or_malformed_hash_function_cannot_create_api(self):
        for change in ["E.HashString=nil", "E.HashString=1", "E.HashString=function()error('HASH_UNAVAILABLE')end", "E.HashString=function()return nil end", "E.HashString=function()return 'hash'end", "E.HashString=function()return 1.5 end", "E.HashString=function()return 0/0 end"]:
            with self.subTest(change=change):
                self.each(change+";assert(BaiqiRazeChoiceCore.Create(C,E)==nil and W.writes==0)")

if __name__=='__main__':unittest.main()
