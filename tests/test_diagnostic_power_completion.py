"""Exercise real callback records and exact cleanup against independent ports."""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=r'''
W={turn=312,player=0,mp=false,human=true,leader='LEADER_BAIQI',owner=0,
 free=2,temp=0,required=5,powered=false,project=false,coal=0,oil=1,uranium=0,
 hash=-1205325871,size=1,busy=true,messages=true,reads=0,orders=0,
 added={},removed={},callbacks={},removeCalls=0,addCalls=0}
local function forbidden()W.orders=W.orders+1;error('forbidden game action')end
local power={GetFreePower=function()W.reads=W.reads+1;if W.throw then error('native unavailable')end
 if W.drift then W.free=W.free+1 end;return W.free end,
 GetTemporaryPower=function()return W.temp end,GetRequiredPower=function()return W.required end,
 IsFullyPowered=function()return W.powered end,IsFullyPoweredByActiveProject=function()return W.project end}
local queue={GetCurrentProductionTypeHash=function()return W.hash end,GetSize=function()return W.size end}
local city={GetID=function()return 524295 end,GetOwner=function()return W.owner end,
 GetPower=function()return power end,GetBuildQueue=function()return queue end}
local resources={GetResourceAmount=function(_,key)
 if key=='RESOURCE_COAL'then return W.coal elseif key=='RESOURCE_OIL'then return W.oil
 elseif key=='RESOURCE_URANIUM'then if W.ownerDrift then W.owner=1 end;return W.uranium end
 error('unexpected resource')end}
local cities={FindID=function(_,id)if id==524295 and not W.noCity then
 if W.freshWrapper then local c={};for k,v in pairs(city)do c[k]=v end;return c end
 return city end end}
local p={GetCities=function()return cities end,GetResources=function()return resources end,SetProperty=forbidden,
 IsTurnActive=function()error('must support interturn callbacks')end}
local function Event(kind)
 local event={}
 event.Add=function(...)
  assert(select('#',...)==1,'static Add');local fn=...;W.addCalls=W.addCalls+1
  W.added[kind]=fn;W.callbacks[kind]=fn
  if W.addThrow==kind then error('Add threw after attachment')end
  if W.addFalse==kind then return false end
 end
 event.Remove=function(...)
  assert(select('#',...)==1,'static Remove');local fn=...;W.removeCalls=W.removeCalls+1;W.removed[kind]=fn
  if W.removeThrow==kind then error('Remove unavailable')end
  if W.removeFalse==kind then return false end
  if W.callbacks[kind]==fn then W.callbacks[kind]=nil end
 end
 return event
end
E={Game={GetLocalPlayer=function(...)assert(select('#',...)==0);return W.player end,
 GetCurrentGameTurn=function(...)assert(select('#',...)==0);return W.turn end},
 GameConfiguration={IsAnyMultiplayer=function()return W.mp end},UI={IsGameCoreBusy=function()return W.busy end,
 IsProcessingMessages=function()return W.messages end},Players={[0]=p},PlayerConfigurations={[0]={
 IsHuman=function()return W.human end,GetLeaderTypeName=function()return W.leader end}},
 Events={CityProductionCompleted=Event('prod'),CityProjectCompleted=Event('project')},
 cityIDs={524295},maxRecords=4,minTurn=312,maxTurn=320,
 CityManager={RequestOperation=forbidden},UnitManager={RequestOperation=forbidden}}
function Emit(kind,pid,id)local fn=W.callbacks[kind];if fn then fn(pid,id,123456,'unused')end end
'''


class PowerCompletionTests(unittest.TestCase):
    def setUp(self):
        self.lua=LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FIXTURE)
        path=Path(os.environ.get('POWER_COMPLETION_SOURCE') or ROOT/'tools/lua/diagnostic_power_completion.lua')
        self.module=self.lua.execute(path.read_text(encoding='utf-8'))
        self.w=self.lua.globals().W
        self.e=self.lua.globals().E

    def install(self):
        self.h=self.module.Install(self.e)
        return self.h

    def emit(self,kind='prod',pid=0,city=524295):
        self.lua.globals().Emit(kind,pid,city)
        self.assertEqual(self.w.orders,0)

    def test_two_actual_callbacks_capture_positive_fuel_unpowered_signed_hash_interturn(self):
        h=self.install();self.emit();self.emit('project')
        self.assertEqual(len(h.samples),2)
        for index,kind in [(1,'CityProductionCompleted'),(2,'CityProjectCompleted')]:
            row=h.samples[index]
            self.assertEqual((row.eventKind,row.turn,row.cityID,row.status),(kind,312,524295,'KNOWN'))
            self.assertEqual((row.fullyPowered,row.requiredPower,row.coal,row.oil,row.queueHash),(False,5,0,1,-1205325871))
            self.assertTrue(row.busy);self.assertTrue(row.messages)
        self.assertEqual(h.errors,0)

    def test_bad_scope_and_dense_city_list_rejected_before_subscriptions(self):
        for code in ['E.cityIDs={}','E.cityIDs={[1]=524295,hidden=999}',
                     'E.cityIDs={[2]=524295}','E.cityIDs={524295,524295}',
                     'E.maxRecords=0','E.maxRecords=129','E.minTurn=321',
                     'W.player=1','W.mp=true','W.human=false',"W.leader='OTHER'",'W.owner=1']:
            with self.subTest(code=code):
                self.setUp();self.lua.execute(code)
                with self.assertRaises(Exception):self.install()
                self.assertEqual(self.w.addCalls,0)

    def test_other_actor_city_and_malformed_ids_ignored_before_getters(self):
        h=self.install()
        for args in [('prod',1,524295),('project',0,99),('prod',0,-1),('prod',0,float('nan'))]:self.emit(*args)
        self.assertEqual((len(h.samples),h.matches,self.w.reads),(0,0,0))

    def test_scope_changes_after_install_are_explicit_unknown_without_native_snapshot(self):
        for key,value in [('player',1),('mp',True),('human',False),('leader','OTHER'),('turn',321),('owner',1),('noCity',True)]:
            with self.subTest(key=key):
                self.setUp();h=self.install();self.w[key]=value;self.emit()
                self.assertEqual((h.samples[1].status,h.errors,h.matches),('UNKNOWN',1,1))
                self.assertIsNone(h.samples[1].coal);self.assertEqual(self.w.reads,0)

    def test_throw_bad_number_boolean_and_drift_are_unknown_never_zero_fallback(self):
        for key,value in [('throw',True),('drift',True),('required',float('nan')),('oil',-1),('powered',1),('hash',1.5),('size',129)]:
            with self.subTest(key=key):
                self.setUp();h=self.install();self.w[key]=value;self.emit()
                self.assertEqual((h.samples[1].status,h.errors),('UNKNOWN',1));self.assertIsNone(h.samples[1].coal)

    def test_final_owner_drift_unknown_and_fresh_city_wrapper_can_be_known(self):
        h=self.install();self.w.ownerDrift=True;self.emit();self.assertEqual(h.samples[1].status,'UNKNOWN')
        self.setUp();h=self.install();self.w.freshWrapper=True;self.emit();self.assertEqual(h.samples[1].status,'KNOWN')

    def test_cap_counts_drops_without_more_native_reads(self):
        self.e.maxRecords=1;h=self.install();self.emit();reads=self.w.reads;self.emit('project')
        self.assertEqual((len(h.samples),h.matches,h.drops,self.w.reads),(1,2,1,reads))

    def test_restore_uses_both_exact_refs_once_and_disables_retained_callbacks(self):
        h=self.install();self.lua.execute('W.savedProd=W.added.prod;W.savedProject=W.added.project')
        self.assertTrue(h.Restore());self.assertTrue(h.Restore())
        self.assertTrue(self.lua.eval('W.added.prod==W.removed.prod and W.added.project==W.removed.project'))
        self.assertEqual(self.w.removeCalls,2);self.assertFalse(h.active);self.assertTrue(h.restored)
        self.lua.execute('W.savedProd(0,524295);W.savedProject(0,524295)')
        self.assertEqual((len(h.samples),self.w.reads),(0,0))

    def test_failed_remove_never_claims_success_or_retries_unknown_remove(self):
        for key in ['removeThrow','removeFalse']:
            with self.subTest(key=key):
                self.setUp();h=self.install();self.w[key]='prod'
                self.assertFalse(h.Restore());self.assertFalse(h.Restore())
                self.assertFalse(h.active);self.assertFalse(h.restored);self.assertEqual((h.removeErrors,self.w.removeCalls),(1,2))
                self.emit();self.assertEqual((len(h.samples),self.w.reads),(0,0))

    def test_partial_add_throw_or_false_after_attachment_exactly_cleans_attempted_refs(self):
        for key in ['addThrow','addFalse']:
            for kind,count in [('prod',1),('project',2)]:
                with self.subTest(key=key,kind=kind):
                    self.setUp();self.w[key]=kind
                    with self.assertRaises(Exception):self.install()
                    self.assertEqual((self.w.addCalls,self.w.removeCalls,len(self.w.callbacks)),(count,count,0))
                    self.assertTrue(self.lua.eval('W.added.prod==W.removed.prod'))
                    if count==2:self.assertTrue(self.lua.eval('W.added.project==W.removed.project'))

    def test_input_list_is_copied_and_primitive_records_do_not_alias_live_ports(self):
        h=self.install();self.e.cityIDs[1]=99;self.emit();self.assertEqual(h.samples[1].status,'KNOWN')
        self.w.oil=9;self.emit('project');self.assertEqual(h.samples[1].oil,1);self.assertEqual(h.samples[2].oil,9)
        self.assertEqual(self.lua.globals().E.maxRecords,4)
        self.assertIsNone(self.lua.globals().DiagnosticPowerCompletion)


if __name__=='__main__':unittest.main()
