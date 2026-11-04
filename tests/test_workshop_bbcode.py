"""Exercise the published document format, including malformed image payloads."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from tools.prepare_workshop import ROOT, bbcode


class WorkshopBBCodeTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / ".local-model"
        parent.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="workshop-bbcode-", dir=parent)
        self.assertTrue(Path(self.temp.name).resolve().is_relative_to(parent.resolve()))
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "description.bbcode"

    def check_text(self, text):
        self.path.write_text(text, encoding="utf-8", newline="\n")
        return bbcode(self.path)

    def test_inline_steam_image_and_chinese_prose(self):
        text = "[h2]地图上的选择[/h2]\n[img]https://images.steamusercontent.com/ugc/1/ABC/[/img]\n玩家确认。"
        result = self.check_text(text)
        self.assertEqual(result["bytes"], len(text.encode("utf-8")))
        self.assertEqual(result["sha256"], hashlib.sha256(text.encode("utf-8")).hexdigest())

    def test_legacy_list_and_links(self):
        self.check_text("[h1]Alpha[/h1][list][*][b]军队[/b][*][url=https://github.com/XenoAmess/civ6_dev]源码[/url][/list]")

    def test_image_must_be_an_absolute_https_url_without_credentials(self):
        for url in ["", "http://example.com/a.png", "javascript:alert(1)", "/a.png", "https:///a.png",
                    "https://name:secret@example.com/a.png", "https://name@example.com/a.png",
                    "https://example.com/a b.png", "https://example.com/a\n.png", "https://example.com/\x00a.png"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.check_text("[img]" + url + "[/img]")

    def test_image_and_tag_structure_cannot_hide_nested_markup(self):
        for text in ["[img=https://example.com/a.png][/img]", "[img][b]https://example.com/a.png[/b][/img]",
                     "[img]https://example.com/a.png", "[h2]text[/img]", "[img]https://example.com/a.png[/h2]",
                     "[unknown]text[/unknown]", "[*]orphan"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.check_text(text)


if __name__ == "__main__":
    unittest.main()
