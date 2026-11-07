"""Verify release pins, immutable staging and the pre-SDK occupancy gate offline."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools import prepare_workshop as workshop
from tools import publish_workshop as publisher
from tools.build_mod import MOD_ID


class WorkshopReleaseTests(unittest.TestCase):
    def setUp(self):
        parent = workshop.ROOT / ".local-model"
        parent.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix="workshop-release-", dir=parent)
        self.root = Path(temp.name).resolve()
        self.assertTrue(self.root.is_relative_to(parent.resolve()))
        self.addCleanup(temp.cleanup)
        self.addCleanup(patch.stopall)
        patch.object(workshop, "ROOT", self.root).start()
        self.release = "v0.1.0-alpha.2"
        self.source = self.root / "mod/Baiqi"
        self.source.mkdir(parents=True)
        (self.source / "Baiqi.modinfo").write_text(
            f'<Mod id="{MOD_ID}" version="82"><Files><File>A.sql</File></Files></Mod>', encoding="utf-8")
        (self.source / "A.sql").write_text("SELECT 1;", encoding="utf-8")
        self.docs = workshop.release_docs(self.release)
        self.docs.mkdir(parents=True)
        (self.docs / "description.bbcode").write_text("[h2]实机[/h2]测试版。", encoding="utf-8")
        (self.docs / "changenotes.bbcode").write_text("[b]Alpha 2[/b]", encoding="utf-8")
        self.plan = {"release": self.release, "internal_build": 82, "media": []}
        self.pin = {"release": self.release, "internal_build": 82, "product_files": 2,
                    "product_manifest": [{"path": name, "sha256": workshop.digest(self.source / name)}
                                         for name in ("Baiqi.modinfo", "A.sql")]}
        self.write_plans()

    def write_plans(self):
        (self.docs / "package.json").write_text(json.dumps(self.plan), encoding="utf-8")
        pin = self.root / "docs/releases" / self.release / "verification.json"
        pin.parent.mkdir(parents=True, exist_ok=True)
        pin.write_text(json.dumps(self.pin), encoding="utf-8")

    def validate(self, plan=None, pin=None):
        return workshop.validated_product(plan or self.plan, pin or self.pin, self.release, self.source)

    def test_selected_release_uses_verified_build_count_and_stage_readback(self):
        stage = self.root / "dist/workshop/alpha2-fixture"
        result = workshop.prepare(stage, release=self.release)
        self.assertEqual((result["internal_build"], result["product_files"]), (82, 2))
        self.assertFalse(result["steam_api_initialized"])
        self.assertFalse(result["steam_upload_attempted"])
        self.assertEqual((stage / "content/A.sql").read_bytes(), (self.source / "A.sql").read_bytes())
        self.assertEqual(workshop.prepare(stage, release=self.release), result)

    def test_release_names_reject_traversal_and_unrecognized_formats(self):
        for name in ("../alpha", "/v0.1.0-alpha.2", "v0.1.0", "v1.2.3-alpha.4/../x", "v1.2.3-alpha.4\n"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                workshop.release_docs(name)

    def test_build_release_and_count_are_strictly_pinned(self):
        for field, value in (("release", "v0.1.0-alpha.1"), ("internal_build", 74),
                             ("internal_build", True), ("internal_build", "82"),
                             ("product_files", True), ("product_files", 3), ("product_files", 0)):
            pin = copy.deepcopy(self.pin)
            pin[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.validate(pin=pin)
        for value in (True, 0, "82", 74):
            plan = dict(self.plan, internal_build=value)
            with self.subTest(plan=value), self.assertRaises(ValueError):
                self.validate(plan=plan)

    def test_malformed_duplicate_aliased_and_escaping_inventory_is_rejected(self):
        for name in ("A.sql", "../A.sql", "./A.sql", "folder/../A.sql", "folder//A.sql", "C:/A.sql", "A\\sql"):
            pin = copy.deepcopy(self.pin)
            pin["product_manifest"][0]["path"] = name
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.validate(pin=pin)
        for sha in ("A" * 64, "z" * 64, "0" * 63, None):
            pin = copy.deepcopy(self.pin)
            pin["product_manifest"][0]["sha256"] = sha
            with self.subTest(sha=sha), self.assertRaises(ValueError):
                self.validate(pin=pin)

    def test_content_tamper_and_manifest_inventory_change_are_rejected(self):
        (self.source / "A.sql").write_text("SELECT 2;", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.validate()
        (self.source / "A.sql").unlink()
        with self.assertRaises(ValueError):
            self.validate()

    def test_release_symlink_cannot_escape_the_workshop_tree(self):
        other = self.root / "other"
        other.mkdir()
        link = self.root / "docs/workshop/v1.0.0-alpha.1"
        try:
            link.symlink_to(other, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Directory symlink unavailable: {exc}")
        with self.assertRaises(ValueError):
            workshop.release_docs("v1.0.0-alpha.1")
    def test_stage_outside_scope_extra_files_and_changed_content_are_preserved(self):
        with self.assertRaises(ValueError):
            workshop.prepare(self.root / "elsewhere", release=self.release)
        stage = self.root / "dist/workshop/reused"
        workshop.prepare(stage, release=self.release)
        extra = stage / "other.txt"
        extra.write_text("keep", encoding="utf-8")
        with self.assertRaises(ValueError):
            workshop.prepare(stage, release=self.release)
        self.assertEqual(extra.read_text(encoding="utf-8"), "keep")
        extra.unlink()
        target = stage / "content/A.sql"
        target.write_text("different", encoding="utf-8")
        with self.assertRaises(ValueError):
            workshop.prepare(stage, release=self.release)
        self.assertEqual(target.read_text(encoding="utf-8"), "different")

    def test_default_alpha1_pin_is_not_silently_replaced_by_current_product(self):
        old = self.root / "docs/workshop" / workshop.DEFAULT_RELEASE
        old.mkdir(parents=True)
        old_plan = dict(self.plan, release=workshop.DEFAULT_RELEASE, internal_build=74)
        (old / "package.json").write_text(json.dumps(old_plan), encoding="utf-8")
        old_pin = self.root / "docs/releases" / workshop.DEFAULT_RELEASE / "verification.json"
        old_pin.parent.mkdir(parents=True)
        old_pin.write_text(json.dumps(dict(self.pin, release=workshop.DEFAULT_RELEASE)), encoding="utf-8")
        with self.assertRaises(ValueError):
            workshop.prepare()


class PublisherOccupancyGateTests(unittest.TestCase):
    def test_page_edits_share_new_release_mutation_intents_and_preserve_legacy_paths(self):
        a = publisher.publication_paths("v0.1.0-alpha.2", 1, "1" * 12)
        b = publisher.publication_paths("v0.1.0-alpha.2", 2, "2" * 12)
        self.assertEqual(a[1], b[1])
        self.assertNotEqual(a[0], b[0])
        self.assertNotEqual(a[2], b[2])
        old = publisher.publication_paths(workshop.DEFAULT_RELEASE, 2, "1" * 12)
        self.assertEqual(old[1], publisher.ROOT / ".local-model/steam/workshop-alpha1/page-2")
        self.assertEqual(old[2].name, "input.json")

    def test_cli_refuses_before_reading_a_nonexistent_sdk_or_release(self):
        root = Path(__file__).resolve().parents[1]
        for mode in ("inspect", "update-content", "append-preview", "download"):
            p = subprocess.run([sys.executable, str(root / "tools/publish_workshop.py"), "--mode", mode,
                                "--sdk-dir", str(root / ".local-model/nonexistent-sdk"),
                                "--release", "../invalid", "--item-id", "3833805495"],
                               cwd=root, capture_output=True, text=True)
            self.assertEqual(p.returncode, 2)
            self.assertIn("Remote game occupancy must be confirmed", p.stderr)
            self.assertNotIn("Traceback", p.stderr)


if __name__ == "__main__":
    unittest.main()
