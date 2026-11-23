"""Actual bootstrap consumer: Core-created handles versus UI-time Map getters."""
from pathlib import Path
import sys
import unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
import test_baiqi_raze_choice as contracts

ROOT=contracts.ROOT
BOOT=(ROOT/'mod/Baiqi/Lua/BaiqiRazeChoiceGameplay.lua').read_text(encoding='utf-8')
CONTEXT=r'''
W.inUI=false;W.coreHandles=0;W.uiHandles=0
local original=E.Map.GetPlotByIndex
E.Map.GetPlotByIndex=function(index)
 local t=original(index)
 if W.inUI then W.uiHandles=W.uiHandles+1;t.SetProperty=nil
 else W.coreHandles=W.coreHandles+1 end
 return t
end
for k,v in pairs(E)do _G[k]=v end
BaiqiConfig=C;function include()end;ExposedMembers={}
'''

class BoundCorePlotConsumers(unittest.TestCase):
    def each(self,body):
        for factory in (Lua51,Lua53):
            with self.subTest(vm=factory.__module__):
                lua=factory(unpack_returned_tuples=True)
                for name in ('BaiqiRazeChoiceCore','BaiqiRazeChoiceView'):
                    lua.execute((ROOT/'mod/Baiqi/Lua'/f'{name}.lua').read_text(encoding='utf-8'))
                lua.execute(contracts.WORLD);lua.execute(CONTEXT);lua.execute(BOOT)
                self.assertTrue(lua.execute('return(function()\n'+body+'\nreturn true end)()'))

    def test_real_bootstrap_then_ui_original_raze_uses_bound_core_handle(self):
        self.each(r'''
local nativeMap=Map
assert(W.writes==0 and W.reads==0)
API=assert(BaiqiRazeChoiceGameplay.api);W.inUI=true
View();W.destroy=true;local a,b,c,d=Forward(city,9,{[7]=3},nil,'tail')
assert(a==nil and b==true and c==nil and d=='last'and W.native==1)
assert(W.writes==1 and W.properties[21].cityID==917516)
local s,blocked,why,v=Read()
assert(s=='READY'and blocked==true and why=='player_raze_choice'and v.cityID==917516)
assert(W.uiHandles==0 and W.coreHandles>0 and Map==nativeMap)
''')

    def test_bound_handles_do_not_read_hidden_properties_or_grant_hidden_choice(self):
        self.each(r'''
API=assert(BaiqiRazeChoiceGameplay.api);W.inUI=true;W.visible=false
assert(W.reads==0 and W.writes==0)
assert(Remember()=='UNAVAILABLE'and W.reads==0 and W.writes==0)
W.visible=true;W.active=false
assert(Remember()=='UNAVAILABLE'and W.writes==0)
''')

    def test_current_map_dimensions_must_match_bound_world_before_read_or_write(self):
        self.each(r'''
API=assert(BaiqiRazeChoiceGameplay.api);W.inUI=true
E.Map.GetGridSize=function()return 11,10 end
assert(Read()=='UNAVAILABLE'and Remember()=='UNAVAILABLE'and W.writes==0)
''')

if __name__=='__main__':unittest.main()
