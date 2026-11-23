"""Player Raze provenance survives reload and cannot grant a background order."""
import json
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53
import test_baiqi_settler_direct_goal as direct
import test_baiqi_settler_goals_core as goals

ROOT=Path(__file__).resolve().parents[1]
WORLD=r'''
W={turn=131,localID=0,owner=0,cityID=917516,city=true,visible=true,revealed=true,
 active=true,strategic=true,human=true,leader='LEADER_BAIQI',properties={},reads=0,writes=0,native=0,logs=0}
local function Plot(index)
 return {GetIndex=function()return index end,GetX=function()return index%10 end,
 GetY=function()return math.floor(index/10)end,GetOwner=function()return W.owner end,
 IsCity=function()return W.city end,GetProperty=function(_,key)
  assert(key=='RAZE','Other property read');W.reads=W.reads+1
  if W.onGet then W.onGet()end;return W.properties[index]
 end,SetProperty=function(_,key,value)
  assert(key=='RAZE','Other property write');W.writes=W.writes+1
  if W.beforeSet then W.beforeSet()end
  if not W.dropWrite then W.properties[index]=value end
  if W.afterSet then W.afterSet()end
 end}
end
city={GetID=function()assert(W.city);return W.cityID end,
 GetOwner=function()assert(W.city);return W.owner end,GetX=function()assert(W.city);return 1 end,
 GetY=function()assert(W.city);return 2 end,CanRaze=function()return W.legal~=false end}
p={IsTurnActive=function()return W.active end,GetCities=function()return{
 FindID=function(_,id)return W.city and not W.alias and id==W.cityID and city or nil end}end}
C={leader='LEADER_BAIQI',razeChoiceKey='RAZE'}
E={Game={GetLocalPlayer=function()return W.localID end,GetCurrentGameTurn=function()return W.turn end,
 IsAllowStrategicCommands=function()return W.strategic end},
 GameConfiguration={IsAnyMultiplayer=function()return W.multi==true end,IsHotseat=function()return W.hotseat==true end},
 Players={[0]=p},PlayerConfigurations={[0]={GetLeaderTypeName=function()return W.leader end,IsHuman=function()return W.human end}},
 Map={GetGridSize=function()return 10,10 end,GetPlotByIndex=Plot,GetPlot=function(x,y)return Plot(y*10+x)end},
 PlayersVisibility={[0]={IsRevealed=function()return W.revealed end,IsVisible=function()return W.visible end}},
 CityManager={GetCityAt=function(x,y)return W.city and x==1 and y==2 and city or nil end}}
API=assert(BaiqiRazeChoiceCore.Create(C,E))
function Remember()return API.Remember(0,917516,21,1,2)end
function Read(index)return API.Read(0,index or 21,(index or 21)%10,math.floor((index or 21)/10))end
function View()
 local api={version=1,marker='baiqi-raze-choice-v1',Remember=function(...)return API.Remember(...)end}
 V={BaiqiUIGuard={PlayerID=function()if W.otherLeader then return nil end;return 0 end},
 CityCommandTypes={DESTROY=9},CityDestroyDirectives={RAZE=3},UnitOperationTypes={PARAM_FLAGS=7},
 Map=E.Map,ExposedMembers={BaiqiRazeChoiceBridge=api},Print=function()W.logs=W.logs+1 end}
 manager={CanStartCommand=function()return W.commandLegal~=false end}
 local native=function(...)
  W.native=W.native+1;W.args={n=select('#',...),...}
  if W.nativeError then error('NATIVE_FAILURE')end
  if W.destroy then W.city=false end
  return nil,true,nil,'last'
 end
 Forward=BaiqiRazeChoiceView.Wrap(native,manager,V)
end
'''


class RazeChoiceContracts(unittest.TestCase):
    def each(self,body):
        for factory in (Lua51,Lua53):
            with self.subTest(vm=factory.__module__):
                lua=factory(unpack_returned_tuples=True)
                for name in ('BaiqiRazeChoiceCore','BaiqiRazeChoiceView'):
                    lua.execute((ROOT/'mod/Baiqi/Lua'/f'{name}.lua').read_text(encoding='utf-8'))
                lua.execute(WORLD)
                self.assertTrue(lua.execute('return(function()\n'+body+'\nreturn true end)()'))

    def test_absence_never_invents_a_past_raze(self):
        self.each("W.city=false;local s,b=Read();assert(s=='READY'and b==false and W.writes==0)")

    def test_real_choice_survives_fresh_core_and_empty_plot_without_writes(self):
        self.each("local s,v=Remember();assert(s=='READY'and v.cityID==917516 and W.writes==1);v.cityID=1;W.city=false;API=assert(BaiqiRazeChoiceCore.Create(C,E));local a,b,r,v=Read();assert(a=='READY'and b and v.cityID==917516 and W.writes==1);local c,d=Read(22);assert(c=='READY'and d==false)")

    def test_same_choice_is_idempotent_and_different_identity_cannot_overwrite(self):
        self.each("Remember();Remember();assert(W.writes==1);W.cityID=983052;local s,v=API.Remember(0,983052,21,1,2);assert(s=='READY'and v.cityID==917516 and W.writes==1)")

    def test_native_core_missing_config_human_uses_typed_player_fallback(self):
        self.each("E.PlayerConfigurations[0].IsHuman=nil;p.IsHuman=function()return W.human end;local s,b=Read();assert(s=='READY'and b==false);assert(Remember()=='READY'and W.writes==1)")
        for change in ("E.PlayerConfigurations[0].IsHuman=nil;p.IsHuman=function()return false end", "E.PlayerConfigurations[0].IsHuman=nil", "E.PlayerConfigurations[0].IsHuman='invalid';p.IsHuman=function()return true end", "W.human=false;p.IsHuman=function()return true end"):
            self.each(change+";assert(Read()=='UNAVAILABLE');assert(Remember()=='UNAVAILABLE'and W.writes==0)")

    def test_wrong_owner_alias_hidden_and_inactive_do_not_write(self):
        for change in ("W.owner=1","W.alias=true","W.visible=false","W.revealed=false","W.city=false","W.active=false","W.strategic=false","W.multi=true","W.hotseat=true","W.human=false","W.localID=1","W.leader='QIN'"):
            with self.subTest(change=change):self.each(change+";assert(Remember()=='UNAVAILABLE'and W.writes==0)")

    def test_wrong_coordinates_or_full_city_identity_never_write(self):
        self.each("assert(API.Remember(0,917516,22,1,2)=='UNAVAILABLE');assert(API.Remember(0,1,21,1,2)=='UNAVAILABLE');assert(API.Read(0,101,1,10)=='UNAVAILABLE');assert(W.writes==0)")

    def test_malformed_record_is_preserved_and_not_treated_as_clear_land(self):
        for data in ("{version=99}","true","{version=1,kind='PLAYER_RAZE_CHOICE',owner=1,cityID=917516,plot=21,x=1,y=2,turn=131}"):
            self.each("W.properties[21]="+data+";local original=W.properties[21];assert(Read()=='UNAVAILABLE');assert(Remember()=='UNAVAILABLE');assert(W.writes==0 and W.properties[21]==original)")

    def test_write_unknown_freezes_without_retry_and_reload_uses_real_saved_state(self):
        for hook in ("W.dropWrite=true","W.beforeSet=function()error('BEFORE')end","W.afterSet=function()error('AFTER')end"):
            self.each(hook+";assert(Remember()=='UNAVAILABLE');W.beforeSet=nil;W.afterSet=nil;W.dropWrite=false;assert(Read()=='UNAVAILABLE');assert(Remember()=='UNAVAILABLE'and W.writes==1);API=assert(BaiqiRazeChoiceCore.Create(C,E));local s,b=Read();assert(s=='READY'and b==(W.properties[21]~=nil))")

    def test_state_changes_during_reads_or_persist_are_unavailable(self):
        self.each("W.onGet=function()W.turn=132 end;assert(Read()=='UNAVAILABLE'and W.writes==0)")
        self.each("W.afterSet=function()W.owner=1 end;assert(Remember()=='UNAVAILABLE'and W.writes==1);assert(Read()=='UNAVAILABLE')")

    def test_reentrant_record_is_not_a_second_writer(self):
        self.each("W.onGet=function()W.inner=Remember()end;assert(Remember()=='READY');assert(W.inner=='UNAVAILABLE'and W.writes==1)")

    def test_original_raze_tuple_and_arguments_forward_once_no_deleted_city_read(self):
        self.each("View();W.destroy=true;local params={[7]=3};local a,b,c,d=Forward(city,9,params,nil,'tail');assert(a==nil and b==true and c==nil and d=='last');assert(W.native==1 and W.writes==1 and W.args.n==5 and W.args[3]==params and W.args[4]==nil and W.args[5]=='tail');assert(Read()=='READY')")

    def test_keep_liberate_qin_and_unqualified_requests_do_not_record(self):
        for change,flag in (("",2),("",1),("W.otherLeader=true",3),("W.commandLegal=false",3),("W.legal=false",3)):
            self.each("View()\n"+change+"\nForward(city,9,{[7]="+str(flag)+"});assert(W.native==1 and W.writes==0)")

    def test_bridge_failure_does_not_duplicate_or_suppress_original_native(self):
        self.each("View();V.ExposedMembers.BaiqiRazeChoiceBridge.Remember=function()error('BRIDGE')end;Forward(city,9,{[7]=3});assert(W.native==1 and W.writes==0 and W.logs==1)")
        self.each("View();W.nativeError=true;local ok,e=pcall(Forward,city,9,{[7]=3});assert(not ok and string.find(e,'NATIVE_FAILURE')and W.native==1 and W.writes==1)")

    def test_gameplay_bootstrap_replaces_only_matching_old_world_bridge(self):
        source=(ROOT/'mod/Baiqi/Lua/BaiqiRazeChoiceGameplay.lua').read_text(encoding='utf-8')
        for existing,expected in (("nil",True),("{version=1,marker='baiqi-raze-choice-v1',Read=function()error('OLD_WORLD')end}",True),("{version=1,marker='other'}",False)):
            for factory in (Lua51,Lua53):
                with self.subTest(vm=factory.__module__,existing=existing):
                    lua=factory(unpack_returned_tuples=True)
                    lua.execute((ROOT/'mod/Baiqi/Lua/BaiqiRazeChoiceCore.lua').read_text(encoding='utf-8'));lua.execute(WORLD)
                    lua.execute("for k,v in pairs(E)do _G[k]=v end;BaiqiConfig=C;function include()end;ExposedMembers={BaiqiRazeChoiceBridge="+existing+"}")
                    lua.execute(source)
                    self.assertEqual(lua.eval('BaiqiRazeChoiceGameplay.api~=nil'),expected)
                    self.assertEqual(lua.eval('W.writes'),0)
                    if expected:
                        self.assertEqual(lua.eval('ExposedMembers.BaiqiRazeChoiceBridge.Read(0,21,1,2)')[:2],('READY',False))
                        lua.execute('local old=ExposedMembers.BaiqiRazeChoiceBridge;'+source+'\nassert(old==ExposedMembers.BaiqiRazeChoiceBridge)')


class RazeChoiceGoalStorageTests(unittest.TestCase):
    setUp=goals.SettlerGoalsCoreTests.setUp
    def test_recorded_or_unknown_raze_site_cannot_be_remembered(self):
        for code in ('W.blocked=true',"W.choiceStatus='UNAVAILABLE'"):
            with self.subTest(code=code):
                self.setUp();self.lua.execute(code)
                self.assertEqual(self.lua.eval('Remember()')[0],'UNAVAILABLE')
                self.assertEqual(self.w.writes,0)


class RazeChoiceControllerTests(unittest.TestCase):
    candidate_source=None
    setUp=direct.DirectSettlerGoalTests.setUp
    step=direct.DirectSettlerGoalTests.step
    moves=direct.DirectSettlerGoalTests.moves
    def test_old_goal_is_retired_and_valid_elsewhere_expansion_continues(self):
        self.lua.execute('TestWorld.razedPlots={[46]=true}')
        self.step();self.assertEqual(self.moves(),[])
        self.step();self.assertEqual(self.moves(),[(2,2,4)])
        self.assertEqual(self.w.goalProposals['2'].plot,47)
        self.assertTrue(all(r.target!=46 for r in self.w.pathQueries.values()))

    def test_unknown_raze_history_never_grants_movement(self):
        self.lua.execute("TestWorld.razeRead=function()return 'UNAVAILABLE' end")
        for _ in range(3):self.step()
        self.assertEqual(self.moves(),[])

    def test_raze_choice_during_native_move_qualification_cancels_stale_goal_order(self):
        self.lua.execute('''local original=UnitManager.CanStartOperation
UnitManager.CanStartOperation=function(unit,op,...)
 if op==UnitOperationTypes.MOVE_TO then TestWorld.razedPlots={[46]=true}end
 return original(unit,op,...)
end''')
        self.step();self.assertEqual(self.moves(),[])


class RazeChoiceFoundingTests(unittest.TestCase):
    def case(self,body):
        data=json.loads((ROOT/'tests/fixtures/settlement_intent_core_cases.json').read_text(encoding='utf-8'))
        for factory in (Lua51,Lua53):
            with self.subTest(vm=factory.__module__):
                lua=factory(unpack_returned_tuples=True)
                for name in ('BaiqiSettlementJournal','BaiqiSettlementStateCore','BaiqiSettlementIntentCore'):
                    lua.execute((ROOT/'mod/Baiqi/Lua'/f'{name}.lua').read_text(encoding='utf-8'))
                lua.execute(data['fixture_lua']);lua.execute("E.RazeChoice={Read=function()return m.razeStatus or 'READY',m.razeBlocked==true end}")
                self.assertTrue(lua.execute('return(function()'+body+';return true end)()'))

    def test_prepare_rejects_recorded_or_unknown_choice(self):
        for state in ("m.razeBlocked=true","m.razeStatus='UNAVAILABLE'"):
            self.case("local a=Init();"+state+";local s=a.Prepare(0,7929900,906,26,20,'0:148:1');assert(s=='UNAVAILABLE'and m.writes==1 and m.bank.operations['7929900']==nil)")

    def test_choice_between_prepare_and_commit_cannot_grant(self):
        self.case("local a=Init();local op=Prepare(a);m.razeBlocked=true;local granted=a.Commit(0,7929900,op.token,'0:148:1');assert(granted==false and m.bank.operations['7929900'].stage=='PREPARED')")

    def test_choice_during_armed_persist_never_grants_or_replays(self):
        self.case("local a=Init();local op=Prepare(a);m.onSet=function()m.razeBlocked=true end;local granted=a.Commit(0,7929900,op.token,'0:148:1');assert(granted==false and m.bank.operations['7929900'].stage=='ARMED');local n=m.writes;m.razeBlocked=false;m.onSet=nil;assert(a.Commit(0,7929900,op.token,'0:148:1')==false and m.writes==n)")

if __name__=='__main__':unittest.main()
