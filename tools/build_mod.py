"""Validate, package and optionally install the Baiqi mod. Python standard library only."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
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
        if not path.is_file() or path.suffix.lower() not in {".sql", ".xml", ".lua"}:
            raise ValueError(f"Missing or unsupported source file: {relative}")
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix.lower() == ".xml":
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
    # Keep extra files and old managed files; never recursively delete or move folders.
    target.mkdir(parents=True, exist_ok=True)
    new_files = dict(old_files)
    for relative in files:
        src, dst = contained(source, relative), contained(target, relative)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        new_files[relative] = digest(dst)
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
