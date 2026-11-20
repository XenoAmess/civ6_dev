"""Exercise the complete read-only mode query and its launch admission boundary."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import steam_live_mode_probe as live


class FakeReadOnly:
    def __init__(self, case):
        self.case = case
        self.identities = self.focuses = self.hits = 0
        self.cloaks = {}

    def current_steam(self):
        self.identities += 1
        if self.case == "no_current_client":
            raise RuntimeError("Missing current client fixture")
        return 777, 123.0 + int(self.case == "reused_instance" and self.identities > 1)

    def foreground(self):
        self.focuses += 1
        if self.case == "foreground_query_error":
            raise RuntimeError("Foreground read failed")
        return 91 + int(self.case == "focus_changed" and self.focuses > 1)

    def windows(self):
        return [10, 20] if self.case == "conflicting_modes" else [10]

    def visible(self, hwnd):
        return self.case != "not_visible"

    def rect(self, hwnd):
        return (9, 34, 191, 269) if hwnd == 10 else (300, 34, 482, 269)

    def belongs(self, hwnd, identity):
        return not (self.case == "foreign_hit" and hwnd == 101)

    def cloak(self, hwnd):
        self.cloaks[hwnd] = self.cloaks.get(hwnd, 0) + 1
        if self.case == "DWM_query_error":
            return -1, 0
        if self.case == "cloaked_popup" and hwnd == 10:
            return 0, 2
        if self.case == "cloaked_hit_root" and hwnd == 301:
            return 0, 4
        if self.case == "cloaked_during_read" and hwnd == 10 and self.cloaks[hwnd] > 1:
            return 0, 1
        return 0, 0

    def hit(self, point):
        self.hits += 1
        if self.case == "hit_changed" and self.hits > 1:
            return 102
        return 101 if point[0] < 200 else 102

    def root(self, hwnd):
        return hwnd + 200

    def item(self, point):
        online = self.case == "online" or self.case == "conflicting_modes" and point[0] > 200
        return {"label": "进入离线模式..." if online else "上线...",
                "type": "Button" if self.case == "wrong_control_type" else "MenuItem",
                "visible": self.case != "UIA_not_visible",
                "rect": (0, 0, 1, 1) if self.case == "wrong_item_bounds" else (0, 100, 500, 133)}


class ModeQueryTests(unittest.TestCase):
    def check_case(self, case):
        # Fake receipts never enter the real Steam evidence directory.
        scratch = ROOT / ".local-model"
        scratch.mkdir(exist_ok=True)
        with TemporaryDirectory(prefix="mode-probe-unit-", dir=scratch) as directory:
            self.assertTrue(Path(directory).resolve().is_relative_to(scratch.resolve()))
            result = live.query_mode(directory, FakeReadOnly(case))
            expected = case if case in ("offline", "online") else "unavailable"
            self.assertEqual(result["mode"], expected)
            for flag in ("input_sent", "activation_api_called", "window_move_api_called", "screenshot_used"):
                self.assertFalse(result[flag])
            files = list(Path(directory).glob("live-mode-dwm-*.json"))
            self.assertEqual(len(files), 1)
            self.assertEqual(json.loads(files[0].read_text(encoding="utf-8")), result)

    def test_missing_backend_is_unavailable(self):
        with TemporaryDirectory() as directory:
            with patch.object(live, "WindowsReadOnly", side_effect=ImportError("Missing backend fixture")):
                result = live.query_mode(directory)
            self.assertEqual(result["mode"], "unavailable")
            self.assertEqual(result["failure_type"], "ImportError")


CASES = (
    "offline", "online", "cloaked_popup", "cloaked_hit_root", "DWM_query_error",
    "cloaked_during_read", "reused_instance", "focus_changed", "foreign_hit",
    "hit_changed", "not_visible", "UIA_not_visible", "wrong_control_type",
    "wrong_item_bounds", "conflicting_modes", "no_current_client", "foreground_query_error",
)
for case in CASES:
    def test(self, case=case):
        self.check_case(case)
    setattr(ModeQueryTests, "test_" + case, test)


class OfflineAdmissionTests(unittest.TestCase):
    def call(self, mode, birth=123.0):
        proof = {"mode": mode, "steam_pid": 777, "steam_birth": 123.0}
        process = Mock()
        process.name.return_value = "steam.exe"
        process.create_time.return_value = birth
        psutil = Mock()
        psutil.Process.return_value = process
        with patch.object(live, "query_mode", return_value=proof):
            with patch.dict(sys.modules, {"psutil": psutil}), redirect_stdout(io.StringIO()):
                result = live.require_offline()
        return proof, process, result

    def test_unavailable_never_admits(self):
        with self.assertRaisesRegex(RuntimeError, "mismatch: unavailable"):
            self.call("unavailable")

    def test_online_never_admits(self):
        with self.assertRaisesRegex(RuntimeError, "mismatch: online"):
            self.call("online")

    def test_current_bound_offline_client(self):
        proof, process, result = self.call("offline")
        self.assertEqual(result, (proof, process))

    def test_reused_pid_never_admits(self):
        with self.assertRaisesRegex(RuntimeError, "instance changed"):
            self.call("offline", birth=456.0)


if __name__ == "__main__":
    unittest.main()
