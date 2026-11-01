"""Verify selected sources, run the Windows layout tool, and encode DDS with texconv."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

from build_mod import ROOT, validate_dds


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-kit", type=Path, default=ROOT / ".local-model/art-discovery-20261101/selected")
    parser.add_argument("--texconv", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, default=ROOT / ".local-model/art-export28")
    args = parser.parse_args()
    source_record = json.loads((ROOT / "docs/research/baiqi-art-sources-2026-11-01.json").read_text(encoding="utf-8"))
    sources = [s for s in source_record["sources"] if s["id"] in {"leader-master", "portrait-master"}]
    sources.append(source_record["generated_background"])
    for source in sources:
        path = args.source_kit / (source["id"] + ".png")
        with path.open("rb") as stream:
            header = stream.read(24)
        if (digest(path) != source["sha256"] or header[:8] != b"\x89PNG\r\n\x1a\n"
                or struct.unpack(">II", header[16:24]) != (source["width"], source["height"])):
            raise ValueError(f"Selected source identity or size changed: {path.name}")
    work = args.work_dir.resolve()
    pngs, dds = work / "png", work / "dds"
    for directory in (work, pngs, dds):
        directory.mkdir(parents=True, exist_ok=True)
    compiler = Path(os.environ.get("WINDIR", "C:/Windows")) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    executable = work / "BaiqiArtLayout.exe"
    subprocess.run([str(compiler), "/nologo", "/target:exe", "/reference:System.Drawing.dll",
                    "/out:" + str(executable), str(ROOT / "tools/BaiqiArtLayout.cs")], check=True)
    subprocess.run([str(executable), str(args.source_kit.resolve()), str(pngs)], check=True)
    names = [f"Baiqi_Leader{size}" for size in (32, 45, 50, 55, 64, 80, 256)]
    names += ["Baiqi_LeaderForeground", "Baiqi_LoadingBackground", "Baiqi_DiplomacyBackground"]
    textures = []
    converter = args.texconv.resolve()
    for name in names:
        subprocess.run([str(converter), "-nologo", "-m", "1", "-dx9", "-f", "B8G8R8A8_UNORM", "--ignore-srgb",
                        "-ft", "dds", "-y", "-o", str(dds), str(pngs / (name + ".png"))], check=True)
        path = dds / (name + ".dds")
        width, height = validate_dds(path)
        textures.append({"path": "Art/" + path.name, "width": width, "height": height,
                         "format": "legacy BGRA8, straight alpha, one mip", "sha256": digest(path), "bytes": path.stat().st_size})
    destination = ROOT / "mod/Baiqi/Art"
    destination.mkdir(exist_ok=True)
    for name in names:
        shutil.copy2(dds / (name + ".dds"), destination / (name + ".dds"))
    record = {"schema": "civ6.baiqi-art-export/v1", "exported_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "machine_id": os.environ.get("COMPUTERNAME"), "source_record": "baiqi-art-sources-2026-11-01.json",
              "source_sha256": {s["id"]: s["sha256"] for s in sources},
              "layout_source_sha256": digest(ROOT / "tools/BaiqiArtLayout.cs"), "texconv_sha256": digest(converter),
              "layouts": {"portrait": "92% contain, centered with 4% border", "loading_foreground": "contain in transparent825x1024, no character crop",
                          "loading_background": "cover1920x960, source upscaled1774x887",
                          "diplomacy": "cover1920x1010; original leader height1470 at885,10; lower legs clipped by canvas"},
              "color_encoding": "Preserve PNG sample bytes with --ignore-srgb; do not convert sRGB samples into linear bytes for UI textures.",
              "textures": textures, "native_display_validation": "NOT_RUN"}
    (ROOT / "docs/research/baiqi-art-export-2026-11-01.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"textures": len(textures), "bytes": sum(t["bytes"] for t in textures), "native_display_validation": "NOT_RUN"}))


if __name__ == "__main__":
    main()
