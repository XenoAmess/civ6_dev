from pathlib import Path
import unittest,uuid,json
from lupa.lua53 import LuaRuntime
from tools.build_static_control import build,clock_prelude,ROOT
from tools.static_control_source import transform
from tools.build_mod import manifest_files


class PairedBuildTests(unittest.TestCase):
    def test_identical_stopwatch_before_original_executor_and_all_source_hashes(self):
        out=ROOT/'.local-model/paired-build-tests'/uuid.uuid4().hex
        enabled=build(out/'enabled',paired_clock=True,variant='enabled')
        control=build(out/'control',paired_clock=True,variant='control')
        self.assertEqual(enabled['clock_prefix_sha256'],control['clock_prefix_sha256'])
        self.assertEqual(enabled['source_hashes'],control['source_hashes'])
        self.assertEqual(enabled['changed_files'],['UI/BaiqiExecutor.lua'])
        raw=(ROOT/'mod/Baiqi/UI/BaiqiExecutor.lua').read_text(encoding='utf-8')
        prefix=clock_prelude()
        self.assertEqual((out/'enabled/Baiqi/UI/BaiqiExecutor.lua').read_text(encoding='utf-8'),prefix+raw)
        self.assertEqual((out/'control/Baiqi/UI/BaiqiExecutor.lua').read_text(encoding='utf-8'),prefix+transform(raw,'UI/BaiqiExecutor.lua')[0])
        expected=len(manifest_files(ROOT/'mod/Baiqi'))
        self.assertEqual(enabled['files'],expected);self.assertEqual(control['files'],expected)
        self.assertEqual((enabled['source_version'],control['source_version']),(77,77))
        receipt=ROOT/'.local-model/acceptance-p6-20261101'/f"paired-c2-v{enabled['source_version']}-{out.name}-tested-builds.json"
        receipt.write_text(json.dumps({'root':str(out.relative_to(ROOT)),'enabled':enabled,'control':control},indent=2)+'\n',encoding='utf-8',newline='\n')

    def test_prefix_subscribes_before_original_callback_and_reload_retires_own_only(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''T={time=1,turn=85,pid=0,remove=0,callbacks={}}
Events={PlayerTurnActivated={Add=function(fn) T.callbacks[#T.callbacks+1]=fn end,Remove=function(fn) T.remove=T.remove+1;for i=#T.callbacks,1,-1 do if T.callbacks[i]==fn then table.remove(T.callbacks,i) end end end}}
Automation={GetTime=function() return T.time end};Game={GetCurrentGameTurn=function() return T.turn end,GetLocalPlayer=function() return T.pid end}
''')
        prefix=clock_prelude();lua.execute(prefix)
        lua.execute("Events.PlayerTurnActivated.Add(function() T.time=T.time+10 end);assert(P6PairClock:Begin(85));T.turn=86;T.time=2;for _,fn in ipairs(T.callbacks) do fn(0) end")
        self.assertEqual(lua.globals().P6PairClock.Snapshot(lua.globals().P6PairClock).records[1].seconds,1)
        lua.execute(prefix)
        self.assertEqual((lua.globals().T.remove,len(lua.globals().T.callbacks)),(1,2))
        self.assertTrue(lua.globals().P6PairClock.Snapshot(lua.globals().P6PairClock).subscribed)

    def test_invalid_variant_rejected_before_output_creation(self):
        out=ROOT/'.local-model/paired-build-tests'/uuid.uuid4().hex
        for kwargs in ({'variant':'enabled'},{'variant':'unknown'},{'paired_clock':1}):
            with self.assertRaises(ValueError):build(out,**kwargs)
        self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
