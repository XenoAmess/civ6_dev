"""Optional official-SDK compile and local-helper checks; no Steam initialization."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class WorkshopManagedTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt" and os.environ.get("BAIQI_WORKSHOP_SDK_ASSEMBLY"),
                         "Set BAIQI_WORKSHOP_SDK_ASSEMBLY to an installed official Steamworks.NET.dll")
    def test_csharp5_compile_and_pure_helpers_without_publisher_main(self):
        root = Path(__file__).resolve().parents[1]
        parent = (root / ".local-model").resolve()
        parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="workshop-managed-", dir=parent) as temp:
            folder = Path(temp).resolve()
            self.assertTrue(folder.is_relative_to(parent))
            sdk = Path(os.environ["BAIQI_WORKSHOP_SDK_ASSEMBLY"]).resolve(strict=True)
            shutil.copyfile(sdk, folder / "Steamworks.NET.dll")
            csc = Path(os.environ["SystemRoot"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
            executable = folder / "WorkshopOfflineTests.exe"
            p = subprocess.run([str(csc), "/nologo", "/platform:x64", "/target:exe", "/main:WorkshopOfflineTests",
                                "/reference:" + str(sdk), "/reference:System.Web.Extensions.dll",
                                "/out:" + str(executable), str(root / "tools/BaiqiWorkshopPublisher.cs"),
                                str(root / "tests/workshop-publisher-offline.cs")], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            p = subprocess.run([str(executable), str(folder)], cwd=folder, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn("WORKSHOP_OFFLINE_HELPERS_PASS cases=20", p.stdout)
            self.assertIn("steam_api_initialized=false publisher_main_called=false", p.stdout)


if __name__ == "__main__":
    unittest.main()
