from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile
import json
import struct

from tools.build_mod import ROOT, MARKER, contained, digest, install, manifest_files, package


class ModPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = ROOT / "mod/Baiqi"

    def test_package_contains_exact_inventory_once(self):
        output = self.base / "Baiqi.zip"
        files = package(self.source, output)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(len(archive.namelist()), len(files))
            self.assertEqual(set(archive.namelist()), {"Baiqi/" + f for f in files})

    def test_path_traversal_and_symlink_escape_denied(self):
        for relative in ("../outside", "Lua/../../outside", "C:/outside", "/outside", ""):
            with self.assertRaises(ValueError):
                contained(self.base, relative)

    def test_unmanaged_install_refused(self):
        target = self.base / "Baiqi"
        target.mkdir()
        (target / "user.txt").write_text("keep", encoding="utf-8")
        with self.assertRaises(ValueError):
            install(self.source, self.base)
        self.assertEqual((target / "user.txt").read_text(), "keep")

    def test_install_reinstall_and_preserve_local_edits(self):
        target = install(self.source, self.base)
        self.assertEqual(install(self.source, self.base), target)
        edited = target / "Lua/BaiqiPolicy.lua"
        edited.write_text("-- user edit", encoding="utf-8")
        with self.assertRaises(ValueError):
            install(self.source, self.base)
        self.assertEqual(edited.read_text(), "-- user edit")

    def test_bad_inventory_utf8_is_rejected(self):
        copy = self.base / "source"
        shutil.copytree(self.source, copy)
        (copy / "Lua/BaiqiPolicy.lua").write_bytes(b"\xff")
        with self.assertRaises(UnicodeDecodeError):
            manifest_files(copy)

    def test_texture_binary_survives_package_and_install_unchanged(self):
        relative = "Art/Baiqi_Leader32.dds"
        expected = (self.source / relative).read_bytes()
        output = self.base / "Baiqi.zip"
        package(self.source, output)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(archive.read("Baiqi/" + relative), expected)
        target = install(self.source, self.base / "mods")
        self.assertEqual((target / relative).read_bytes(), expected)

    def test_bad_texture_rejected_before_any_install_write(self):
        copy = self.base / "source"
        shutil.copytree(self.source, copy)
        path = copy / "Art/Baiqi_Leader32.dds"
        original = path.read_bytes()
        target = install(self.source, self.base / "mods")
        marker_before = (target / MARKER).read_bytes()
        invalid = {"truncated": original[:-1], "bad_magic": b"PNG " + original[4:]}
        for name, offset, value in (("huge_width", 16, 8193), ("extra_mip", 28, 2),
                                    ("wrong_mask", 92, 0), ("volume", 112, 0x200000)):
            data = bytearray(original)
            struct.pack_into("<I", data, offset, value)
            invalid[name] = data
        for name, data in invalid.items():
            with self.subTest(name=name):
                path.write_bytes(data)
                with self.assertRaises(ValueError):
                    install(copy, self.base / "mods")
                self.assertEqual((target / MARKER).read_bytes(), marker_before)
                self.assertEqual((target / "Art/Baiqi_Leader32.dds").read_bytes(), original)

    def test_modified_installed_texture_prevents_other_file_overwrite(self):
        target = install(self.source, self.base / "mods")
        installed = target / "Art/Baiqi_Leader32.dds"
        installed.write_bytes(installed.read_bytes()[:-4] + b"edit")
        copy = self.base / "source"
        shutil.copytree(self.source, copy)
        changed = copy / "Lua/BaiqiPolicy.lua"
        changed.write_bytes(changed.read_bytes() + b"\n-- next build\n")
        old_policy = (target / "Lua/BaiqiPolicy.lua").read_bytes()
        with self.assertRaises(ValueError):
            install(copy, self.base / "mods")
        self.assertEqual((target / "Lua/BaiqiPolicy.lua").read_bytes(), old_policy)
        self.assertEqual(installed.read_bytes()[-4:], b"edit")

    def stale_file(self):
        target = install(self.source, self.base)
        stale = target / 'Lua/Retired.lua'
        stale.write_text('-- old managed feature', encoding='utf-8')
        state = json.loads((target / MARKER).read_text())
        state['files']['Lua/Retired.lua'] = digest(stale)
        (target / MARKER).write_text(json.dumps(state), encoding='utf-8')
        return target, stale

    def test_retire_only_unchanged_owned_file_and_reinstall_remains_valid(self):
        target, stale = self.stale_file()
        unrelated = target / 'user.txt'
        unrelated.write_text('keep')
        install(self.source, self.base)
        self.assertFalse(stale.exists())
        self.assertNotIn('Lua/Retired.lua', json.loads((target / MARKER).read_text())['files'])
        self.assertEqual(unrelated.read_text(), 'keep')
        install(self.source, self.base)

    def test_modified_retired_file_refuses_all_writes(self):
        target, stale = self.stale_file()
        before = (target / MARKER).read_bytes()
        stale.write_text('-- user modified')
        with self.assertRaises(ValueError):
            install(self.source, self.base)
        self.assertEqual(stale.read_text(), '-- user modified')
        self.assertEqual((target / MARKER).read_bytes(), before)

    def test_unsafe_marker_path_is_refused_before_retirement(self):
        target, stale = self.stale_file()
        state = json.loads((target / MARKER).read_text())
        state['files']['../outside.txt'] = 'untrusted'
        (target / MARKER).write_text(json.dumps(state), encoding='utf-8')
        with self.assertRaises(ValueError):
            install(self.source, self.base)
        self.assertTrue(stale.exists())


if __name__ == "__main__":
    unittest.main()
