"""Run the official Civ6 SDK managed Workshop API after explicit occupancy clearance."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

from prepare_workshop import DOCS, ROOT, prepare


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-dir", type=Path, required=True, help="Official Civ6 SDK installation directory")
    parser.add_argument("--remote-idle-confirmed", action="store_true",
                        help="Only supply after a fresh reliable check or explicit user report; never override a Steam conflict")
    parser.add_argument("--mode", choices=["list", "create-draft", "readback", "publish", "download", "append-preview", "update-page"], default="list")
    parser.add_argument("--item-id", type=int)
    args = parser.parse_args()
    if not args.remote_idle_confirmed:
        parser.error("Remote game occupancy must be confirmed before initializing Steam; no login or override is performed")
    if args.mode in {"readback", "publish", "download", "append-preview", "update-page"} and (args.item_id is None or args.item_id <= 0):
        parser.error("An explicit existing item ID is required")
    if args.mode in {"list", "create-draft"} and args.item_id is not None:
        parser.error("This mode does not accept an item ID")
    try:
        plan_path = DOCS / "package-current.json"
        if not plan_path.exists():
            plan_path = DOCS / "package.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        if args.mode == "create-draft" and plan.get("published_file_id"):
            raise ValueError("This package already has a published item; update its explicit existing ID instead of creating another")
        page_revision = int(plan.get("page_revision", 1))
        body_hash = hashlib.sha256((DOCS / "description.bbcode").read_bytes()).hexdigest()[:12]
        stage = ROOT / "dist/workshop" / f"alpha1-page{page_revision}-{body_hash}"
        prepare(stage)
        sdk = args.sdk_dir.resolve() / "ModUploader"
        bridge = ROOT / ".local-model/tools/workshop-sdk-bridge"
        bridge.mkdir(parents=True, exist_ok=True)
        binaries = {}
        for name in ("Steamworks.NET.dll", "CSteamworks.dll", "steam_api64.dll"):
            source, target = sdk / name, bridge / name
            data = source.read_bytes()
            if target.exists() and target.read_bytes() != data:
                raise ValueError("Different SDK bridge binary already present; inspect before replacing it")
            if not target.exists():
                with target.open("xb") as stream:
                    stream.write(data)
            binaries[name] = hashlib.sha256(data).hexdigest()
        csc = Path(os.environ["SystemRoot"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
        source_hash = hashlib.sha256((ROOT / "tools/BaiqiWorkshopPublisher.cs").read_bytes()).hexdigest()[:12]
        executable = bridge / ("BaiqiWorkshopPublisher-" + source_hash + ".exe")
        subprocess.run([str(csc), "/nologo", "/platform:x64", "/target:exe",
                        "/reference:" + str(bridge / "Steamworks.NET.dll"), "/reference:System.Web.Extensions.dll",
                        "/out:" + str(executable), str(ROOT / "tools/BaiqiWorkshopPublisher.cs")], check=True)
        private = ROOT / ".local-model/steam/workshop-alpha1" / f"page-{page_revision}"
        private.mkdir(parents=True, exist_ok=True)
        gallery = [row for row in plan["media"] if row["upload"] and row["role"] != "primary_preview"]
        config = {"remote_occupancy_source": "user_explicit_idle", "mod_id": plan["mod_id"],
                  "title": plan["title"], "description": (DOCS / "description.bbcode").read_text(encoding="utf-8"),
                  "change_notes": (DOCS / plan.get("change_notes", "changenotes.bbcode")).read_text(encoding="utf-8"),
                  "content": str(stage / "content"), "preview": str(stage / "preview.jpg"),
                  "overview": str(stage / "gallery/overview.jpg"), "city": str(stage / "gallery/city-readonly.jpg")}
        config["expected_previews"] = len(gallery)
        config["new_gallery"] = [str(stage / "gallery" / row.get("upload_filename", Path(row["repository_path"]).name))
                                 for row in gallery if row["role"] not in {"gameplay_overview", "gameplay_city"}]
        # Journal location is stable so a second create/publish refuses to overwrite an existing intent.
        config_path = private / "input.json"
        encoded = json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8")
        if config_path.exists() and config_path.read_bytes() != encoded:
            raise ValueError("Existing publication input differs; inspect its journal before proceeding")
        if not config_path.exists():
            with config_path.open("xb") as stream:
                stream.write(encoded)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        receipt = {"utc": datetime.now(timezone.utc).isoformat(), "mode": args.mode,
                   "remote_occupancy": "Operator explicitly confirmed idle; not an automated absence proof",
                   "sdk_sha256": binaries, "item_id": args.item_id, "no_forced_login": True}
        with (private / (stamp + "-invocation.json")).open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2)
        env = os.environ.copy()
        running_app = "289070" if args.mode == "download" else "404350"
        env.update(SteamAppId=running_app, SteamGameId=running_app)
        command = [str(executable), str(config_path), str(private), args.mode]
        if args.item_id is not None:
            command.append(str(args.item_id))
        with (private / (stamp + "-raw.log")).open("x", encoding="utf-8") as log:
            process = subprocess.Popen(command, cwd=bridge, env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            for line in process.stdout:
                log.write(line)
                log.flush()
                if line.lstrip().startswith("{"):
                    try:
                        json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    print(line.rstrip(), flush=True)
            process.wait()
            if process.returncode:
                parser.exit(process.returncode, "Publication stopped; inspect private receipts before retrying any mutation\n")
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Workshop publisher stopped: {exc}\n")


if __name__ == "__main__":
    main()
