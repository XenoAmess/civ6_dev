from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from tools.build_mod import ROOT, contained, install, manifest_files, package


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


if __name__ == "__main__":
    unittest.main()
