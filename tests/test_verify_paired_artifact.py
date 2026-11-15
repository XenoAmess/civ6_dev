from pathlib import Path
import json
import shutil
import tempfile
import unittest
import zipfile

from tools.build_mod import digest, package
from tools.build_static_control import ROOT, build
from tools.verify_paired_artifact import verify_pair


class VerifyPairedArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=ROOT / '.local-model')
        cls.base = Path(cls.temp.name)
        for variant in ('enabled', 'control'):
            build(cls.base / variant, paired_clock=True, normal_end_bridge=True, variant=variant)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def copy(self, variant):
        temp = tempfile.TemporaryDirectory(dir=self.base)
        self.addCleanup(temp.cleanup)
        out = Path(temp.name) / 'artifact'
        shutil.copytree(self.base / variant, out)
        return out

    def rewrite(self, out, variant, metadata):
        archive = out / f'Baiqi-paired{metadata["source_version"]}-{variant}-normal-end.zip'
        package(out / 'Baiqi', archive)
        metadata['archive_sha256'] = digest(archive)
        (out / 'static-control-build.json').write_text(json.dumps(metadata), encoding='utf-8')

    def test_both_actual_variants_are_qualified_without_changing_any_bytes(self):
        for variant in ('enabled', 'control'):
            out = self.base / variant
            before = {p.relative_to(out): digest(p) for p in out.rglob('*') if p.is_file()}
            self.assertEqual(verify_pair(out, ROOT / 'mod/Baiqi', variant)['variant'], variant)
            self.assertEqual(before, {p.relative_to(out): digest(p) for p in out.rglob('*') if p.is_file()})

    def test_control_prefix_or_disabled_body_cannot_be_blessed_by_new_hash_metadata(self):
        for name in ('UI/BaiqiExecutor.lua', 'Lua/BaiqiController.lua'):
            with self.subTest(name=name):
                out = self.copy('control')
                meta = json.loads((out / 'static-control-build.json').read_text(encoding='utf-8'))
                file = out / 'Baiqi' / name
                with file.open('ab') as f:
                    f.write(b'\nBaiqiController=nil\n')
                meta['control_hashes'][name] = digest(file)
                self.rewrite(out, 'control', meta)
                with self.assertRaisesRegex(ValueError, 'canonical'):
                    verify_pair(out, ROOT / 'mod/Baiqi', 'control')

    def test_flags_variant_or_current_helper_hash_must_match(self):
        for key, value in (('normal_end_bridge', 'true'), ('variant', 'control'), ('clock_prefix_sha256', 'stale')):
            with self.subTest(key=key):
                out = self.copy('enabled')
                file = out / 'static-control-build.json'
                meta = json.loads(file.read_text(encoding='utf-8'));meta[key] = value
                file.write_text(json.dumps(meta), encoding='utf-8')
                with self.assertRaises(ValueError):
                    verify_pair(out, ROOT / 'mod/Baiqi', 'enabled')

    def test_tampered_archive_is_rejected(self):
        out = self.copy('enabled')
        version = json.loads((out / 'static-control-build.json').read_text(encoding='utf-8'))['source_version']
        with (out / f'Baiqi-paired{version}-enabled-normal-end.zip').open('ab') as f:
            f.write(b'tampered')
        with self.assertRaisesRegex(ValueError, 'Archive hash'):
            verify_pair(out, ROOT / 'mod/Baiqi', 'enabled')

    def test_duplicate_archive_entries_reject_even_with_updated_digest(self):
        out = self.copy('enabled')
        version = json.loads((out / 'static-control-build.json').read_text(encoding='utf-8'))['source_version']
        archive = out / f'Baiqi-paired{version}-enabled-normal-end.zip'
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(archive, 'a') as z:
                z.writestr('Baiqi/Baiqi.modinfo', (out / 'Baiqi/Baiqi.modinfo').read_bytes())
        file = out / 'static-control-build.json';meta = json.loads(file.read_text(encoding='utf-8'))
        meta['archive_sha256'] = digest(archive);file.write_text(json.dumps(meta), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            verify_pair(out, ROOT / 'mod/Baiqi', 'enabled')


if __name__ == '__main__':
    unittest.main()
