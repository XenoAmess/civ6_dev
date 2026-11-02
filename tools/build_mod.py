"""Validate, package and optionally install the Baiqi mod. Python standard library only."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MOD_ID = "7d682641-0673-4c3a-8d1d-d28aff0b614a"
MARKER = ".baiqi-install.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contained(base: Path, relative: str) -> Path:
    name = PurePosixPath(relative.replace("\\", "/"))
    if name.is_absolute() or ".." in name.parts or ":" in relative or not name.parts:
        raise ValueError(f"Unsafe relative path: {relative!r}")
    target = base.joinpath(*name.parts).resolve()
    if not target.is_relative_to(base.resolve()) or target == base.resolve():
        raise ValueError(f"Path leaves target directory: {relative!r}")
    return target


def validate_dds(path: Path) -> tuple[int, int]:
    """Accept the exported single-image, single-mip legacy BGRA8 textures only."""
    with path.open("rb") as stream:
        header = stream.read(128)
    if len(header) != 128 or header[:4] != b"DDS ":
        raise ValueError(f"Invalid DDS header: {path.name}")
    fields = struct.unpack("<31I", header[4:])
    size, flags, height, width, pitch, depth, mips = fields[:7]
    pixel_format = fields[18:26]
    if (size != 124 or flags & 0x100F != 0x100F
            or not 1 <= width <= 8192 or not 1 <= height <= 8192
            or pitch != width * 4 or depth not in (0, 1) or mips != 1
            or flags & 0x800000
            or pixel_format != (32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
            or fields[26] != 0x1000 or any(fields[27:30])
            or path.stat().st_size != 128 + width * height * 4):
        raise ValueError(f"Unsupported or truncated BGRA8 DDS: {path.name}")
    return width, height


def manifest_files(source: Path) -> list[str]:
    manifest = source / "Baiqi.modinfo"
    root = ET.fromstring(manifest.read_text(encoding="utf-8-sig"))
    if root.tag != "Mod" or root.get("id") != MOD_ID:
        raise ValueError("Unexpected mod identity")
    files = [(node.text or "").strip() for node in root.findall("./Files/File")]
    if not files or len(files) != len(set(files)):
        raise ValueError("Empty or duplicate manifest inventory")
    inventory = set(files)
    for section in ("FrontEndActions", "InGameActions"):
        for entry in root.findall(f"./{section}//File"):
            if (entry.text or "").strip() not in inventory:
                raise ValueError(f"Action references a file outside Files: {entry.text}")
    for relative in files:
        path = contained(source, relative)
        if not path.is_file() or path.suffix.lower() not in {".sql", ".xml", ".lua", ".dds", ".dep", ".artdef"}:
            raise ValueError(f"Missing or unsupported source file: {relative}")
        if path.suffix.lower() == ".dds":
            validate_dds(path)
            continue
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix.lower() in {".xml", ".dep", ".artdef"}:
            ET.fromstring(text)
    return ["Baiqi.modinfo", *files]


def package(source: Path, output: Path) -> list[str]:
    files = manifest_files(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in files:
            archive.write(contained(source, relative), f"Baiqi/{relative}")
    return files


def install(source: Path, mods_dir: Path) -> Path:
    files = manifest_files(source)
    mods_dir = mods_dir.resolve()
    target = contained(mods_dir, "Baiqi")
    marker = target / MARKER
    old_files: dict[str, str] = {}
    if target.exists() and any(target.iterdir()):
        if not marker.is_file():
            raise ValueError(f"Refusing to overwrite an unmanaged folder: {target}")
        state = json.loads(marker.read_text(encoding="utf-8"))
        if state.get("mod_id") != MOD_ID or not isinstance(state.get("files"), dict):
            raise ValueError("Invalid install ownership marker")
        old_files = state["files"]
        for relative, expected in old_files.items():
            path = contained(target, relative)
            if not path.is_file() or digest(path) != expected:
                raise ValueError(f"Installed managed file was modified or removed: {relative}")
        for relative in files:
            if contained(target, relative).exists() and relative not in old_files:
                raise ValueError(f"Unmanaged file would be overwritten: {relative}")
    # Every owned path and digest was checked before any write. Only retire exact
    # unchanged files absent from the new inventory; never recursively remove folders.
    target.mkdir(parents=True, exist_ok=True)
    new_files = {}
    for relative in files:
        src, dst = contained(source, relative), contained(target, relative)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        new_files[relative] = digest(dst)
    for relative in old_files.keys() - new_files.keys():
        contained(target, relative).unlink()
    marker.write_text(json.dumps({"mod_id": MOD_ID, "files": new_files}, indent=2) + "\n", encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "mod/Baiqi")
    parser.add_argument("--output", type=Path, default=ROOT / "dist/Baiqi.zip")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--mods-dir", type=Path,
                        default=Path.home() / "Documents/My Games/Sid Meier's Civilization VI/Mods")
    args = parser.parse_args()
    try:
        files = package(args.source.resolve(), args.output.resolve())
        print(json.dumps({"archive": str(args.output.resolve()), "files": len(files),
                          "sha256": digest(args.output)}, ensure_ascii=False))
        if args.install:
            print(json.dumps({"installed": str(install(args.source.resolve(), args.mods_dir))}, ensure_ascii=False))
    except (OSError, ValueError, ET.ParseError) as exc:
        parser.exit(1, f"Build/install failed: {exc}\n")


if __name__ == "__main__":
    main()
