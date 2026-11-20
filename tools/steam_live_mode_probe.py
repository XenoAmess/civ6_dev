"""Read the current Steam mode without input, screenshots, or window activation.

The official mode menu must already be open. Missing or cloaked surfaces are
unavailable evidence, including when UI Automation reports them as visible.
"""
from datetime import datetime, timezone
from pathlib import Path
import ctypes
from ctypes import wintypes
import json
import os
import socket

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    "上线...": "offline", "上线…": "offline",
    "Go Online...": "offline", "Go Online…": "offline",
    "进入离线模式...": "online", "进入离线模式…": "online",
    "Go Offline...": "online", "Go Offline…": "online",
}


class WindowsReadOnly:
    def __init__(self):
        if os.name != "nt":
            raise RuntimeError("Windows read-only backend unavailable")
        import psutil
        import win32gui
        import win32process
        from pywinauto import Desktop
        self.psutil = psutil
        self.gui = win32gui
        self.process = win32process
        self.desktop = Desktop

    def current_steam(self):
        clients = [p for p in self.psutil.process_iter(["name"])
                   if (p.info["name"] or "").lower() == "steam.exe"]
        if len(clients) != 1:
            raise RuntimeError("Current Steam client is not unique")
        return clients[0].pid, clients[0].create_time()

    def foreground(self):
        return self.gui.GetForegroundWindow()

    def windows(self):
        rows = []
        self.gui.EnumWindows(lambda hwnd, _: rows.append(hwnd), None)
        foreground = self.foreground()
        if foreground not in rows:
            rows.append(foreground)
        return rows

    def visible(self, hwnd):
        return bool(self.gui.IsWindowVisible(hwnd))

    def rect(self, hwnd):
        return self.gui.GetWindowRect(hwnd)

    def belongs(self, hwnd, identity):
        process = self.psutil.Process(self.process.GetWindowThreadProcessId(hwnd)[1])
        if process.pid == identity[0]:
            return process.create_time() == identity[1]
        return (process.name().lower() == "steamwebhelper.exe"
                and any(p.pid == identity[0] and p.create_time() == identity[1]
                        for p in process.parents()))

    def cloak(self, hwnd):
        query = ctypes.windll.dwmapi.DwmGetWindowAttribute
        query.argtypes = [wintypes.HWND, wintypes.DWORD,
                          ctypes.c_void_p, wintypes.DWORD]
        query.restype = ctypes.c_long
        value = wintypes.DWORD()
        result = query(hwnd, 14, ctypes.byref(value), ctypes.sizeof(value))
        return result, value.value

    def hit(self, point):
        return self.gui.WindowFromPoint(point)

    def root(self, hwnd):
        return self.gui.GetAncestor(hwnd, 2)

    def item(self, point):
        item = self.desktop(backend="uia").from_point(*point)
        rect = item.rectangle()
        return {"label": item.window_text().strip(),
                "type": item.element_info.control_type,
                "visible": item.is_visible(),
                "rect": (rect.left, rect.top, rect.right, rect.bottom)}


def query_mode(output_dir=None, api=None):
    started = datetime.now(timezone.utc)
    before = after = identity = None
    rows = []
    failure = None
    stable = False
    try:
        api = WindowsReadOnly() if api is None else api
        before = api.foreground()
        identity = api.current_steam()
        for hwnd in api.windows():
            try:
                if not api.visible(hwnd) or not api.belongs(hwnd, identity):
                    continue
                rect = api.rect(hwnd)
                # This is the known desktop Steam mode popup, not a search of
                # hidden UIA trees. A changed client layout fails closed.
                if not (100 <= rect[2] - rect[0] <= 260
                        and 180 <= rect[3] - rect[1] <= 400):
                    continue
                if api.cloak(hwnd) != (0, 0):
                    rows.append({"popup": hwnd, "rejected": "CLOAKED_OR_UNKNOWN_DWM_SURFACE"})
                    continue
                point = (rect[0] + 80, rect[1] + 82)
                hit = api.hit(point)
                hit_root = api.root(hit)
                if not api.belongs(hit, identity) or api.cloak(hit_root) != (0, 0):
                    rows.append({"popup": hwnd, "rejected": "FOREIGN_OR_CLOAKED_POINT_SURFACE"})
                    continue
                item = api.item(point)
                bounds = item["rect"]
                if (item["type"] != "MenuItem" or not item["visible"]
                        or not (bounds[0] <= point[0] < bounds[2]
                                and bounds[1] <= point[1] < bounds[3])
                        or item["label"] not in LABELS):
                    continue
                if (api.cloak(hwnd) != (0, 0) or api.cloak(hit_root) != (0, 0)
                        or not api.visible(hwnd) or api.rect(hwnd) != rect
                        or api.hit(point) != hit):
                    rows.append({"popup": hwnd, "rejected": "SURFACE_CHANGED_DURING_READ"})
                    continue
                rows.append({"popup": hwnd, "point": list(point), "hit_hwnd": hit,
                             "hit_root": hit_root, "control_type": "MenuItem",
                             "label": item["label"], "visible": True,
                             "DWM_cloaked": 0, "hit_root_DWM_cloaked": 0,
                             "mode": LABELS[item["label"]]})
            except Exception as error:
                rows.append({"popup": hwnd, "rejected": type(error).__name__})
        stable = api.current_steam() == identity
    except Exception as error:
        stable = False
        failure = type(error).__name__
    finally:
        if api is not None and before is not None:
            try:
                after = api.foreground()
            except Exception as error:
                stable = False
                failure = failure or type(error).__name__
    modes = {row["mode"] for row in rows if "mode" in row}
    mode = next(iter(modes)) if len(modes) == 1 and stable and before == after else "unavailable"
    proof = {
        "schema": "civ6.steam-background-uncloaked-live-menu/v2",
        "utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "machine": os.environ.get("COMPUTERNAME") or socket.gethostname(),
        "steam_pid": identity[0] if identity else None,
        "steam_birth": identity[1] if identity else None,
        "mode": mode, "instance_stable": stable,
        "input_sent": False, "activation_api_called": False,
        "focus_changed": before != after, "window_move_api_called": False,
        "screenshot_used": False, "items": rows, "failure_type": failure,
        "surface_rule": "Visible current owned popup and hit root both DWM0 before/after UIA read. Unknown/cloaked surfaces rejected. CEF popup and hit roots need not be identical.",
    }
    destination = ROOT / ".local-model" / "steam" if output_dir is None else Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    name = "live-mode-dwm-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json"
    with (destination / name).open("x", encoding="utf-8") as stream:
        json.dump(proof, stream, ensure_ascii=False, indent=2)
    return proof


def require_offline():
    proof = query_mode()
    print(json.dumps(proof, ensure_ascii=False), flush=True)
    if proof["mode"] != "offline":
        raise RuntimeError("Mode query mode mismatch: " + proof["mode"])
    import psutil
    process = psutil.Process(proof["steam_pid"])
    if process.name().lower() != "steam.exe" or process.create_time() != proof["steam_birth"]:
        raise RuntimeError("Steam instance changed after mode query")
    return proof, process


if __name__ == "__main__":
    print(json.dumps(query_mode(), ensure_ascii=False), flush=True)
