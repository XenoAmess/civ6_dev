from pathlib import Path
from uuid import uuid4
import hashlib,importlib,json,unittest
from tools.build_static_control import ROOT,build,clock_prelude


class PressurePairedBuildTests(unittest.TestCase):
    def test_real_prefix_all_five_actual_segments_dual_lua(self):
        for version in ('lua51','lua53'):
            for first in (0,1,2147483641):
                lua=importlib.import_module('lupa.'+version).LuaRuntime(unpack_returned_tuples=True)
                lua.execute('''Turn=1;Clock=10;Callbacks={};ExposedMembers={}
Game={GetCurrentGameTurn=function()return Turn end,GetLocalPlayer=function()return 0 end}
Automation={GetTime=function()return Clock end}
Events={PlayerTurnActivated={Add=function(f)Callbacks[#Callbacks+1]=f end,Remove=function()end}}''')
                lua.globals().Turn=first
                lua.execute(clock_prelude(normal_end_bridge=True,source_version=142,pressure_initial_turn=first))
                lua.execute("P6PairStage={phase='RECORDING',token=string.rep('a',32),ends={},normal_end=true,source_version=142,source='baiqi142-pressure-paired-v1'}")
                g=lua.globals();g.P6PairStage.initial_turn=first
                for turn in range(first,first+5):
                    g.Turn=turn;g.Clock=100+20*(turn-first);g.P6PairStage.ends[turn]=True
                    self.assertTrue(g.ExposedMembers.P6BaiqiPairEndBridge.Begin(turn,g.P6PairStage.token))
                    g.Turn=turn+1;g.Clock+=2;lua.execute('for _,f in ipairs(Callbacks)do f(0,false)end')
                self.assertEqual([r.to_turn for r in g.P6PairClock.Snapshot(g.P6PairClock).records.values()],list(range(first+1,first+6)))
                self.assertIsNone(lua.globals().P6PairStage.ends[first+5])

    def test_invalid_pressure_never_creates_output(self):
        for value in (True,1.0,-1,2147483642,'1'):
            out=ROOT/'.local-model/pressure-paired-build-tests'/uuid4().hex
            with self.assertRaises(ValueError):build(out,paired_clock=True,normal_end_bridge=True,pressure_initial_turn=value)
            self.assertFalse(out.exists())
            with self.assertRaises(ValueError):clock_prelude(normal_end_bridge=True,source_version=142,pressure_initial_turn=value)
        for kwargs in ({},{'paired_clock':True},{'normal_end_bridge':True}):
            out=ROOT/'.local-model/pressure-paired-build-tests'/uuid4().hex
            with self.assertRaises(ValueError):build(out,pressure_initial_turn=1,**kwargs)
            self.assertFalse(out.exists())
        for version in (None,140,141,142.0):
            with self.assertRaises(ValueError):clock_prelude(normal_end_bridge=True,source_version=version,pressure_initial_turn=1)

    def test_real_packages_same_prefix_metadata_and_source_immutable(self):
        out=ROOT/'.local-model/pressure-paired-build-tests'/uuid4().hex
        infos=[build(out/v,paired_clock=True,normal_end_bridge=True,variant=v,pressure_initial_turn=1)for v in('enabled','control')]
        self.assertEqual(infos[0]['clock_prefix_sha256'],infos[1]['clock_prefix_sha256'])
        for v,info in zip(('enabled','control'),infos):
            self.assertEqual((info['files'],info['source_version'],info['source'],info['initial_turn']),(119,142,'baiqi142-pressure-paired-v1',1))
            self.assertEqual(info['mode'],f'baiqi142-pressure-paired-{v}-v1')
            self.assertEqual(info['paired_end_turns'],[1,2,3,4,5]);self.assertEqual(info['paired_activation_turns'],[2,3,4,5,6])
            self.assertFalse(info['installed']);self.assertFalse(info['normal_end_driver_ready']);self.assertFalse(info['cross_context_begin_native_verified'])
            self.assertTrue(info['lua51_compiled']);self.assertTrue(info['native_activation_inline_stop'])
            archives=list((out/v).glob('*.zip'));self.assertEqual(len(archives),1);self.assertIn('-pressure-1.zip',archives[0].name)
            self.assertEqual(json.loads((out/v/'static-control-build.json').read_text(encoding='utf-8')),info)
            for name,digest in info['source_hashes'].items():self.assertEqual(hashlib.sha256((ROOT/'mod/Baiqi'/name).read_bytes()).hexdigest(),digest)

    def test_legacy_prefix_hashes_unchanged(self):
        hashes={None:'9989d5ee5bd9519541a05ef87c54797fb67a51797340572601b54046a616a513',
                140:'1336446353a3b83d4605433e723ff317240bd8168da4483cae193fe42111f1a3',
                141:'361c8a12c6a31c1f310cdf4d51a135fa88d16b0ed73047198ad14ad734711bef',
                142:'765bf987369b1e3eccf1a6844db3e10828d6ac9534659b5fa059a03a9032f818'}
        for version,digest in hashes.items():
            prefix=clock_prelude(normal_end_bridge=version is not None,source_version=version)
            self.assertEqual(hashlib.sha256(prefix.encode()).hexdigest(),digest)
