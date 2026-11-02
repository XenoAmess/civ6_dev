"""Control preparation must retain content and reject unaccounted execution."""
from copy import deepcopy
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
from tools.control_manifest import make_control_manifest

ROOT = Path(__file__).resolve().parents[1]


def semantic(node):
    return (node.tag, sorted(node.attrib.items()), (node.text or "").strip(),
            tuple(semantic(child) for child in node))


class ControlManifestTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / "mod/Baiqi/Baiqi.modinfo").read_bytes()
        self.root = ET.fromstring(self.source)

    def changed(self):
        return ET.tostring(self.root, encoding="utf-8")

    def test_actual_manifest_retains_identity_and_static_content(self):
        output, report = make_control_manifest(self.source)
        control = ET.fromstring(output)
        self.assertEqual(control.attrib, self.root.attrib)
        self.assertEqual(report["mod_id"], self.root.get("id"))
        self.assertEqual(report["mod_version"], self.root.get("version"))
        for source_child, control_child in zip(self.root, control):
            self.assertEqual(source_child.tag, control_child.tag)
            if source_child.tag != "InGameActions":
                self.assertEqual(semantic(source_child), semantic(control_child))
        source_static = [semantic(n) for n in self.root.find("InGameActions")
                         if n.tag not in {"AddGameplayScripts", "AddUserInterfaces", "ReplaceUIScript"}]
        self.assertEqual(source_static, [semantic(n) for n in control.find("InGameActions")])
        self.assertEqual(len(self.root), len(control))
        self.assertFalse(any(n.tag in {"AddGameplayScripts", "AddUserInterfaces", "ReplaceUIScript"}
                             for n in control.iter()))
        original_commands = [(n.tag, n.get("id")) for n in self.root.find("InGameActions")
                             if n.tag in {"AddGameplayScripts", "AddUserInterfaces", "ReplaceUIScript"}]
        self.assertCountEqual(report["removed"], original_commands)
        self.assertEqual(report["removed_count"], len(original_commands))

    def test_wrong_root_with_otherwise_complete_metadata_is_rejected(self):
        self.root.tag = "WrongRoot"
        with self.assertRaises(ValueError):
            make_control_manifest(self.changed())

    def test_duplicate_complete_ingame_groups_are_rejected(self):
        self.root.append(deepcopy(self.root.find("InGameActions")))
        with self.assertRaises(ValueError):
            make_control_manifest(self.changed())

    def test_each_missing_execution_kind_is_rejected(self):
        for tag in ("AddGameplayScripts", "AddUserInterfaces", "ReplaceUIScript"):
            with self.subTest(tag=tag):
                root = ET.fromstring(self.source)
                actions = root.find("InGameActions")
                for node in list(actions):
                    if node.tag == tag:
                        actions.remove(node)
                with self.assertRaises(ValueError):
                    make_control_manifest(ET.tostring(root))

    def test_frontend_nested_execution_is_rejected_with_valid_ingame_group(self):
        frontend = self.root.find("FrontEndActions")
        self.assertIsNotNone(frontend)
        ET.SubElement(frontend, "AddUserInterfaces", id="unexpected")
        with self.assertRaises(ValueError):
            make_control_manifest(self.changed())

    def test_deep_execution_is_rejected_even_when_all_required_kinds_exist(self):
        props = ET.SubElement(self.root.find("InGameActions"), "ExtraContainer")
        ET.SubElement(props, "ReplaceUIScript", id="unexpected")
        with self.assertRaises(ValueError):
            make_control_manifest(self.changed())

    def test_missing_identity_and_group_are_rejected(self):
        for attr in ("id", "version"):
            with self.subTest(attr=attr):
                root = ET.fromstring(self.source)
                del root.attrib[attr]
                with self.assertRaises(ValueError):
                    make_control_manifest(ET.tostring(root))
        self.root.remove(self.root.find("InGameActions"))
        with self.assertRaises(ValueError):
            make_control_manifest(self.changed())


if __name__ == "__main__":
    unittest.main()
