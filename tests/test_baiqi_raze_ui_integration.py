"""Actual replacement/loader/view/guard with a declared native API oracle.

This qualifies Lua integration, never a Civ6 Native result.
"""
from pathlib import Path
import sys,unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
import test_baiqi_raze_choice as contracts

PARENT=r'''
g_pSelectedCity=Players[0]:GetCities():GetNextCapturedCity()
function OnButton3()
 local params={[UnitOperationTypes.PARAM_FLAGS]=CityDestroyDirectives.KEEP}
 if CityManager.CanStartCommand(g_pSelectedCity,CityCommandTypes.DESTROY,params)then
  CityManager.RequestCommand(g_pSelectedCity,CityCommandTypes.DESTROY,params)
 end
end
function OnButton4()
 local params={[UnitOperationTypes.PARAM_FLAGS]=CityDestroyDirectives.RAZE}
 if CityManager.CanStartCommand(g_pSelectedCity,CityCommandTypes.DESTROY,params)then
  CityManager.RequestCommand(g_pSelectedCity,CityCommandTypes.DESTROY,params)
 end
end
'''

def world(factory,extra=''):
    lua=factory(unpack_returned_tuples=True)
    lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiRazeChoiceCore.lua').read_text(encoding='utf-8'))
    lua.execute(contracts.WORLD)
    lua.execute(r'''
for k,v in pairs(E)do _G[k]=v end
BaiqiConfig=C
GameConfiguration.GetValue=function()return W.ruleset or 'RULESET_EXPANSION_2'end
UnitManager={}
UI={RequestPlayerOperation=function()error('NO_PLAYER_OPERATION')end}
PlayerOperations={EXECUTE_SCRIPT=1}
CityCommandTypes={DESTROY=9}
CityDestroyDirectives={KEEP=2,RAZE=3}
UnitOperationTypes={PARAM_FLAGS=7}
ContextPtr={SetShutdown=function(_,fn)W.shutdown=fn end}
p.GetCulture=function()return{}end
local originalCities=p.GetCities
p.GetCities=function(self)
 local group=originalCities(self)
 group.GetNextCapturedCity=function()return W.city and city or nil end
 return group
end
local getCityAt=E.CityManager.GetCityAt
CityManager={GetCityAt=getCityAt,
 CanStartCommand=function(ci,command,params)
  assert(ci==city and command==9 and(params[7]==2 or params[7]==3))
  W.qualifiers=(W.qualifiers or 0)+1
  return W.commandLegal~=false
 end,
 RequestCommand=function(ci,command,params,...)
  assert(ci==city and command==9 and(params[7]==2 or params[7]==3))
  W.native=W.native+1;W.forwarded=params
  if params[7]==3 then W.city=false end
  return nil,true,nil,'last'
 end}
E.CityManager=CityManager
API=assert(BaiqiRazeChoiceCore.Create(C,E))
API.version=1;API.marker='baiqi-raze-choice-v1'
ExposedMembers={BaiqiRazeChoiceBridge=API}
NativeBefore={manager=CityManager,qualifier=CityManager.CanStartCommand,
 writer=CityManager.RequestCommand,units=UnitManager,ui=UI,players=Players}
''')
    if extra:lua.execute(extra)
    included=[]
    def include(name):
        included.append(name)
        if name=='BaiqiConfig':lua.execute('BaiqiConfig=C')
        elif name in ('BaiqiUIGuard','BaiqiPolicy','BaiqiUILoader','BaiqiRazeChoiceView'):
            lua.execute((ROOT/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
        elif name=='RazeCity_Expansion2':include('RazeCity')
        elif name=='RazeCity':lua.execute(PARENT)
        else:raise AssertionError('Unexpected include: '+name)
    lua.globals().include=include
    lua.execute((ROOT/'mod/Baiqi/UI/BaiqiRazeCity.lua').read_text(encoding='utf-8'))
    return lua,included


class RazeUIIntegrationTests(unittest.TestCase):
    def test_original_keep_and_raze_qualifiers_and_callbacks_remain_native(self):
        for factory in (Lua51,Lua53):
            for flag,callback in ((2,'OnButton3'),(3,'OnButton4')):
                with self.subTest(vm=factory.__module__,flag=flag):
                    lua,inc=world(factory)
                    self.assertTrue(lua.eval('CityManager.CanStartCommand(g_pSelectedCity,9,{[7]='+str(flag)+'})'))
                    self.assertTrue(lua.eval('CityManager.CanStartCommand==NativeBefore.qualifier'))
                    self.assertTrue(lua.eval('NativeBefore.manager.RequestCommand==NativeBefore.writer'))
                    self.assertTrue(lua.eval('UnitManager==NativeBefore.units and UI==NativeBefore.ui and Players==NativeBefore.players'))
                    self.assertNotIn('BaiqiUIGuard',inc)
                    lua.execute(callback+'()')
                    self.assertEqual(lua.eval('W.native'),1)
                    self.assertEqual(lua.eval('W.forwarded[7]'),flag)
                    self.assertEqual(lua.eval('W.writes'),1 if flag==3 else 0)
                    if flag==3:
                        self.assertEqual(lua.eval('API.Read(0,21,1,2)')[:2],('READY',True))
                        self.assertEqual(lua.eval('W.properties[21].cityID'),917516)

    def test_qin_original_choices_do_not_record_baiqi_metadata(self):
        for factory in (Lua51,Lua53):
            for callback in ('OnButton3','OnButton4'):
                with self.subTest(vm=factory.__module__,callback=callback):
                    lua,_=world(factory,"W.leader='LEADER_QIN_SHI_HUANG'")
                    lua.execute(callback+'()')
                    self.assertEqual((lua.eval('W.native'),lua.eval('W.writes')),(1,0))

    def test_parent_ruleset_loader_retains_base_and_GS_inheritance(self):
        for factory in (Lua51,Lua53):
            for ruleset in ('RULESET_STANDARD','RULESET_EXPANSION_1','RULESET_EXPANSION_2'):
                with self.subTest(vm=factory.__module__,ruleset=ruleset):
                    _,inc=world(factory,'W.ruleset='+repr(ruleset))
                    self.assertEqual(inc.count('RazeCity'),1)
                    self.assertEqual(inc.count('RazeCity_Expansion2'),int(ruleset=='RULESET_EXPANSION_2'))

    def test_engine_rejection_is_not_overridden_or_replayed(self):
        for factory in (Lua51,Lua53):
            lua,_=world(factory,'W.commandLegal=false')
            lua.execute('OnButton4()')
            self.assertEqual((lua.eval('W.native'),lua.eval('W.writes')),(0,0))

    def test_unknown_or_nonhuman_identity_never_fabricates_choice(self):
        for factory in (Lua51,Lua53):
            for code in ("W.human=false","W.multi=true","W.hotseat=true","PlayerConfigurations[0].IsHuman='invalid';p.IsHuman=function()return true end"):
                with self.subTest(vm=factory.__module__,code=code):
                    lua,_=world(factory,code);lua.execute('OnButton4()')
                    self.assertEqual((lua.eval('W.native'),lua.eval('W.writes')),(1,0))

    def test_shutdown_restores_only_owned_context_manager(self):
        for factory in (Lua51,Lua53):
            lua,_=world(factory);lua.execute('W.shutdown()')
            self.assertTrue(lua.eval('CityManager==NativeBefore.manager and UnitManager==NativeBefore.units and UI==NativeBefore.ui and Players==NativeBefore.players'))

if __name__=='__main__':unittest.main()
