from pathlib import Path
import unittest,uuid,hashlib,json
from lupa.lua53 import LuaRuntime
from tools.static_control_source import transform,edits
from tools.build_static_control import build
from tools.build_mod import manifest_files

ROOT=Path(__file__).resolve().parents[1]


def load(lua,key,control=True):
    source=(ROOT/'mod/Baiqi'/key).read_text(encoding='utf-8')
    return lua.execute(transform(source,key)[0] if control else source)


def world(control=True):
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.execute((ROOT/'tests/lua/mock_world.lua').read_text(encoding='utf-8'))
    for name in ('BaiqiConfig','BaiqiPolicy','BaiqiPlanner','BaiqiController'):load(lua,f'Lua/{name}.lua',control)
    return lua


class StaticControlUITests(unittest.TestCase):
    def test_actual_controller_closed_with_original_positive_consumer(self):
        normal=world(False);normal.globals().BaiqiController.RunNow()
        self.assertEqual(len(normal.globals().TestWorld.cityRequests),1)
        lua=world();g=lua.globals();g.TestWorld.withSettler=True
        for _ in range(3):g.BaiqiController.RunNow(True);g.BaiqiController.Update(10,True);g.TestWorld.turn+=1
        self.assertEqual((len(g.TestWorld.cityRequests),len(g.TestWorld.unitRequests)),(0,0))
        self.assertIsInstance(g.BaiqiController.GetStatus(),str)

    def test_actual_admin_no_requests_with_original_positive_consumer(self):
        for control in (False,True):
            lua=LuaRuntime(unpack_returned_tuples=True);lua.execute((ROOT/'tests/lua/mock_admin.lua').read_text(encoding='utf-8'))
            load(lua,'Lua/BaiqiConfig.lua',control);load(lua,'Lua/BaiqiAdmin.lua',control)
            lua.globals().BaiqiAdmin.Run();w=lua.globals().TestAdmin
            self.assertEqual(len(w.requests),0 if control else 2)
            self.assertEqual(w.policyCalls,0 if control else 1)

    def test_actual_executor_closes_recovery_before_registered_callbacks(self):
        for control,expected in ((False,1),(True,0)):
            lua=world();load(lua,'Lua/BaiqiAdmin.lua');g=lua.globals()
            lua.execute('''
T={recovery=0}
local function event() local fs={};return {Add=function(f) fs[#fs+1]=f end,Remove=function() end,Fire=function(...) for _,f in ipairs(fs) do f(...) end end} end
Events.LoadGameViewStateDone=event();Events.PlayerTurnActivated=event();Events.GameCoreEventPlaybackComplete=event()
ContextPtr={LookUpControl=function() return {IsHidden=function() return false end} end,SetHide=function() end,
 SetUpdate=function(_,f) T.update=f end,SetInitHandler=function(_,f) T.init=f end,SetShutdown=function(_,f) T.shutdown=f end}
GameConfiguration.IsSavedGame=function() return true end
PlayerOperations={EXECUTE_SCRIPT=99};GameInfo.Projects={PROJECT_BAIQI_STANDBY={Hash=90}}
TestWorld.objects.city:GetBuildQueue().CanProduce=function() return false end
UI.RequestPlayerOperation=function() T.recovery=T.recovery+1 end
''')
            load(lua,'UI/BaiqiExecutor.lua',control)
            g.Events.LoadGameViewStateDone.Fire();g.T.update(1);g.Events.GameCoreEventPlaybackComplete.Fire()
            self.assertEqual(g.T.recovery,expected)
            self.assertEqual((len(g.TestWorld.cityRequests),len(g.TestWorld.unitRequests)),(0,0))

    def test_builder_preserves_manifest_assets_and_other_readonly_ui(self):
        out=ROOT/'.local-model/static-control-tests'/uuid.uuid4().hex
        result=build(out);self.assertEqual(result['files'],len(manifest_files(ROOT/'mod/Baiqi')));self.assertEqual(set(result['changed_files']),set(edits()))
        self.assertEqual(result['source_version'],85)
        target=out/'Baiqi';source=ROOT/'mod/Baiqi'
        self.assertEqual(manifest_files(source),manifest_files(target))
        for name in manifest_files(source):
            raw=(source/name).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),result['source_hashes'][name])
            if name not in edits():self.assertEqual((target/name).read_bytes(),raw,name)
        self.assertEqual((target/'Baiqi.modinfo').read_bytes(),(source/'Baiqi.modinfo').read_bytes())
        receipt=ROOT/'.local-model/acceptance-p6-20261101'/f"static-control-v{result['source_version']}-{out.name}-tested-build.json"
        receipt.write_text(json.dumps({'output_dir':str(out.relative_to(ROOT)),'result':result},indent=2)+'\n',encoding='utf-8',newline='\n')

    def test_exact_anchor_rejects_drift_and_unknown_source_is_unchanged(self):
        source=(ROOT/'mod/Baiqi/UI/BaiqiExecutor.lua').read_text(encoding='utf-8')
        with self.assertRaises(ValueError):transform(source.replace('local function Update(delta)','local function Update(changed)'),'UI/BaiqiExecutor.lua')
        with self.assertRaises(ValueError):transform(source+source,'UI/BaiqiExecutor.lua')
        self.assertEqual(transform(source,'UI/NotOwned.lua'),(source,[]))


if __name__=='__main__':unittest.main()
