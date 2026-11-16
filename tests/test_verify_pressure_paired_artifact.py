from pathlib import Path
import hashlib
import json
import shutil
import tempfile
import unittest

from tools.build_mod import digest,package
from tools.build_static_control import ROOT,build,clock_prelude
from tools.verify_paired_artifact import verify_pair


class VerifyPressurePairedArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'.local-model');cls.base=Path(cls.temp.name)
        for turn in(1,6):
            for variant in('enabled','control'):
                build(cls.base/f'{turn}-{variant}',paired_clock=True,normal_end_bridge=True,variant=variant,pressure_initial_turn=turn)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def copy(self,turn=6,variant='enabled'):
        temp=tempfile.TemporaryDirectory(dir=self.base);self.addCleanup(temp.cleanup)
        out=Path(temp.name)/'artifact';shutil.copytree(self.base/f'{turn}-{variant}',out)
        return out

    def metadata(self,out):return json.loads((out/'static-control-build.json').read_text(encoding='utf-8'))
    def write(self,out,meta):
        (out/'static-control-build.json').write_text(json.dumps(meta),encoding='utf-8')

    def test_both_actual_pressure_calendars_variants_need_explicit_frozen_turn(self):
        for turn in(1,6):
            for variant in('enabled','control'):
                with self.subTest(turn=turn,variant=variant):
                    out=self.base/f'{turn}-{variant}';before={p.relative_to(out):digest(p)for p in out.rglob('*')if p.is_file()}
                    meta=verify_pair(out,ROOT/'mod/Baiqi',variant,pressure_initial_turn=turn)
                    self.assertEqual(meta,self.metadata(out))
                    self.assertEqual(before,{p.relative_to(out):digest(p)for p in out.rglob('*')if p.is_file()})
                    with self.assertRaises(ValueError):verify_pair(out,ROOT/'mod/Baiqi',variant)

    def test_wrong_caller_calendar_and_nonexact_or_out_of_range_turns_reject(self):
        out=self.base/'6-enabled'
        for turn in(1,True,-1,2147483642,6.0,'6'):
            with self.subTest(turn=turn),self.assertRaises(ValueError):
                verify_pair(out,ROOT/'mod/Baiqi','enabled',pressure_initial_turn=turn)

    def test_source_mode_and_each_calendar_field_cannot_be_forged(self):
        bad=[('source','wrong'),('mode','baiqi155-paired-enabled-c3-normal-end'),('initial_turn',1),
             ('initial_turn',True),('paired_end_turns',[6,7,8,9,True]),
             ('paired_end_turns',[7,8,9,10,11]),('paired_activation_turns',[6,7,8,9,10]),
             ('paired_activation_turns',[7,8,9,10,11.0]),('paired_activation_turns',None)]
        for key,value in bad:
            with self.subTest(key=key,value=value):
                out=self.copy();m=self.metadata(out)
                if value is None:m.pop(key)
                else:m[key]=value
                self.write(out,m)
                with self.assertRaises(ValueError):verify_pair(out,ROOT/'mod/Baiqi','enabled',pressure_initial_turn=6)

    def test_stale_ordinary_prefix_rehashed_into_pressure_package_is_rejected(self):
        out=self.copy();m=self.metadata(out);version=m['source_version'];f=out/'Baiqi/UI/BaiqiExecutor.lua'
        prefix=clock_prelude(normal_end_bridge=True,source_version=version,pressure_initial_turn=6)
        raw=f.read_text(encoding='utf-8');self.assertTrue(raw.startswith(prefix))
        old=clock_prelude(normal_end_bridge=True,source_version=version)
        f.write_text(old+raw[len(prefix):],encoding='utf-8');m['control_hashes']['UI/BaiqiExecutor.lua']=digest(f)
        archive=out/f'Baiqi-paired{version}-enabled-normal-end-pressure-6.zip';package(out/'Baiqi',archive);m['archive_sha256']=digest(archive)
        # Metadata still claims the correct pressure prefix, so only canonical-body validation catches this forgery.
        self.assertEqual(m['clock_prefix_sha256'],hashlib.sha256(prefix.encode()).hexdigest());self.write(out,m)
        with self.assertRaisesRegex(ValueError,'canonical'):
            verify_pair(out,ROOT/'mod/Baiqi','enabled',pressure_initial_turn=6)

    def test_pressure_archive_tamper_and_wrong_archive_name_reject(self):
        out=self.copy();m=self.metadata(out);version=m['source_version']
        archive=out/f'Baiqi-paired{version}-enabled-normal-end-pressure-6.zip'
        with archive.open('ab')as f:f.write(b'tampered')
        with self.assertRaisesRegex(ValueError,'Archive hash'):
            verify_pair(out,ROOT/'mod/Baiqi','enabled',pressure_initial_turn=6)
        out=self.copy();archive=out/f'Baiqi-paired{version}-enabled-normal-end-pressure-6.zip'
        archive.rename(out/f'Baiqi-paired{version}-enabled-normal-end.zip')
        with self.assertRaises((ValueError,FileNotFoundError)):
            verify_pair(out,ROOT/'mod/Baiqi','enabled',pressure_initial_turn=6)


if __name__=='__main__':unittest.main()
