from pathlib import Path
import hashlib
import unittest
from unittest.mock import patch
from uuid import uuid4
import zipfile
from lupa.lua51 import LuaRuntime
from tools import build_plan_profile_mod as builder
from tools.build_mod import manifest_files

ROOT=Path(__file__).resolve().parents[1]


class BuildPlanProfileModTests(unittest.TestCase):
    def fresh(self):
        return ROOT/'.local-model/plan-profile-tests'/uuid4().hex

    def test_actual_current_inventory_bytes_compilers_and_archive(self):
        source=ROOT/'mod/Baiqi'
        before={n:hashlib.sha256((source/n).read_bytes()).hexdigest() for n in manifest_files(source)}
        out=self.fresh();result=builder.build(out)
        self.assertEqual(result['changed_files'],['UI/BaiqiExecutor.lua'])
        self.assertEqual((result['files'],result['lua_sources_compiled_51_and_53']),(119,97))
        self.assertEqual(result['sample_capacity'],4096)
        self.assertFalse(result['aggregate_zero']);self.assertFalse(result['installed'])
        self.assertTrue(result['release_text_recovers_exactly'])
        self.assertTrue(result['gameplay_planning_bodies_unchanged'])
        self.assertFalse(result['release_bodies_unchanged'])
        target=out/'Baiqi';raw=(source/builder.EXECUTOR).read_text(encoding='utf-8')
        transformed,prefix,binding=builder.transform(raw)
        self.assertEqual((target/builder.EXECUTOR).read_text(encoding='utf-8'),transformed)
        self.assertEqual(builder.restore_release(transformed,prefix,binding),raw)
        for n in before:
            if n!=builder.EXECUTOR:self.assertEqual((source/n).read_bytes(),(target/n).read_bytes())
        self.assertEqual(before,{n:hashlib.sha256((source/n).read_bytes()).hexdigest() for n in manifest_files(source)})
        with zipfile.ZipFile(out/'Baiqi-plan140-stageA-v1.zip') as z:
            self.assertEqual(len(z.namelist()),119)
            for n in before:self.assertEqual(z.read('Baiqi/'+n),(target/n).read_bytes())

    def test_actual_executor_registers_anchor_before_includes_and_wraps_after(self):
        raw=(ROOT/'mod/Baiqi'/builder.EXECUTOR).read_text(encoding='utf-8')
        code,_,_=builder.transform(raw);lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''rawget=nil;rawset=nil;Turn=86;Clock=10;Includes=0;Activations={}
Game={GetLocalPlayer=function() return 0 end,GetCurrentGameTurn=function() return Turn end}
Automation={GetTime=function() return Clock end}
Players={[0]={IsTurnActive=function() return true end,
 GetCities=function() return {GetCount=function() return 10 end} end}}
local function Event() return {Add=function() end,Remove=function() end} end
Events={PlayerTurnActivated={Add=function(fn) Activations[#Activations+1]=fn end,
 Remove=function(fn) for i,f in ipairs(Activations) do if f==fn then table.remove(Activations,i);return end end end},
 LoadGameViewStateDone=Event(),GameCoreEventPlaybackComplete=Event()}
ContextPtr={SetUpdate=function() end,SetInitHandler=function() end,SetShutdown=function() end}
function Original(...) Clock=Clock+.01;return ... end
function include(name)
 assert(#Activations==1 and not P6PerfPlanA.bound and P6PerfPlanA.profile.totalCalls==0)
 Includes=Includes+1
 if name=='BaiqiController' then BaiqiController={RunNow=Original,SetTurnGuard=function() end}
 elseif name=='BaiqiAdmin' then BaiqiAdmin={Run=Original}
 else assert(name=='BaiqiMissionaryPurchase') end
end''')
        lua.execute(code)
        lua.execute('''assert(Includes==3 and #Activations==2 and P6PerfPlanA.bound)
assert(P6PerfPlanA.SetEnabled(true));for _,fn in ipairs(Activations) do fn(0) end
assert(P6PerfPlanA.anchors[86]==10)
local function Save(...) return select('#',...),... end
local n,a,b,c,d=Save(BaiqiController.RunNow(8,nil,true,nil))
assert(n==4 and a==8 and b==nil and c==true and d==nil)
assert(P6PerfPlanA.profile.samples[1].name=='Controller.RunNow')
local ok,same=P6PerfPlanA.Restore();assert(ok and same[1] and same[2])
assert(#Activations==1 and BaiqiAdmin.Run==Original and BaiqiController.RunNow==Original)''')

    def test_unknown_source_version_and_output_overlap_reject_before_writes(self):
        out=self.fresh()
        files=manifest_files(ROOT/'mod/Baiqi')
        with patch.object(builder,'manifest_files',return_value=files):
            with patch.object(builder.ET,'fromstring') as parse:
                parse.return_value.get.return_value='141'
                with self.assertRaisesRegex(ValueError,'actual source140'):builder.build(out)
        self.assertFalse(out.exists())
        with self.assertRaisesRegex(ValueError,'separate'):builder.build(ROOT/'mod/Baiqi/private-diagnostic')

    def test_actual_executor_inline_anchor_precedes_plan_even_with_reverse_dispatch(self):
        code,_,_=builder.transform((ROOT/'mod/Baiqi'/builder.EXECUTOR).read_text(encoding='utf-8'))
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''rawget=nil;rawset=nil;Turn=85;Clock=10;Available=false;Activations={}
Game={GetLocalPlayer=function()return 0 end,GetCurrentGameTurn=function()return Turn end}
GameConfiguration={IsSavedGame=function()return true end}
Automation={GetTime=function()return Clock end}
Players={[0]={IsTurnActive=function()return true end,GetCities=function()return {GetCount=function()return 10 end}end}}
GameInfo={Projects={}};PlayerOperations={EXECUTE_SCRIPT=1};UI={RequestPlayerOperation=function()end}
local function Event()return {Add=function()end,Remove=function()end}end
Events={LoadGameViewStateDone=Event(),GameCoreEventPlaybackComplete=Event(),
 PlayerTurnActivated={Add=function(f)Activations[#Activations+1]=f end,
 Remove=function(f)for i,v in ipairs(Activations)do if f==v then table.remove(Activations,i);return end end end}}
ContextPtr={SetHide=function()end,LookUpControl=function()return {IsHidden=function()return false end}end,
 SetUpdate=function()end,SetInitHandler=function(self,f)Initialize=f end,SetShutdown=function(self,f)Shutdown=f end}
function Original(...)
 assert(P6PerfPlanA.anchors[Turn]==Clock,'Actual plan entered before native anchor')
 Clock=Clock+.01;return ...
end
function include(name)
 if name=='BaiqiController' then BaiqiController={RunNow=Original,SetTurnGuard=function()end,
  SetSettlementLoadKind=function()end,IsAvailable=function()return Available end,Shutdown=function()end}
 elseif name=='BaiqiAdmin' then BaiqiAdmin={Run=function()end} end
end''')
        lua.execute(code)
        lua.execute('''Initialize(true);assert(#Activations==2 and P6PerfPlanA.SetEnabled(true))
Turn=86;Clock=20;Available=true
for i=#Activations,1,-1 do Activations[i](0,false) end
assert(P6PerfPlanA.qualificationErrors==0 and P6PerfPlanA.anchors[86]==20)
assert(#P6PerfPlanA.profile.samples==1 and P6PerfPlanA.profile.samples[1].started==20)
local ok,same=P6PerfPlanA.Restore();assert(ok and same[1]and same[2]and #Activations==1)
Shutdown();assert(#Activations==0)''')

    def test_moved_or_duplicate_binding_sites_are_rejected(self):
        raw=(ROOT/'mod/Baiqi'/builder.EXECUTOR).read_text(encoding='utf-8')
        for text in (raw.replace('local ready=false','local ready=true'),
                     raw.replace('local ready=false','-- moved\nlocal ready=false'),
                     raw+'\nlocal ready=false\n',
                     raw.replace('Events.PlayerTurnActivated.Remove(Activate)','Events.PlayerTurnActivated.Remove(Other)')):
            with self.subTest(text=text[-50:]):
                with self.assertRaises(ValueError):builder.transform(text)


if __name__=='__main__':
    unittest.main()
