"""Check/stage the pinned Alpha Workshop package locally; never contacts Steam."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

try:
    from .build_mod import contained, manifest_files
except ImportError:
    from build_mod import contained, manifest_files

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/workshop/v0.1.0-alpha.1"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bbcode(path: Path) -> dict:
    from urllib.parse import urlsplit

    value = path.read_text(encoding="utf-8")
    stack = []
    image_start = None
    for token in re.finditer(r"\[(/?)([^\]]+)\]", value):
        closing, raw = token.groups()
        tag = raw.split("=", 1)[0]
        if tag not in {"h1", "h2", "b", "list", "*", "url", "img"}:
            raise ValueError(f"Unsupported BBCode in {path.name}: {raw}")
        if stack and stack[-1] == "img" and not (closing and tag == "img"):
            raise ValueError("An image must contain a URL only")
        if tag == "img" and raw != "img":
            raise ValueError("Image attributes are not supported")
        if tag == "*":
            if closing or not stack or stack[-1] != "list":
                raise ValueError("List item outside list")
            continue
        if closing:
            if not stack or stack.pop() != tag:
                raise ValueError(f"Unbalanced BBCode in {path.name}")
            if tag == "img":
                url = value[image_start:token.start()]
                parsed = urlsplit(url)
                if (not re.fullmatch(r"https://[^\s\x00-\x1f\x7f\[\]<>]+", url)
                        or not parsed.hostname or parsed.username is not None or parsed.password is not None):
                    raise ValueError("Expected an absolute HTTPS image URL without credentials or whitespace")
                image_start = None
        else:
            if tag == "url" and not raw.startswith("url=https://"):
                raise ValueError("Expected an explicit HTTPS link")
            stack.append(tag)
            if tag == "img":
                image_start = token.end()
    if stack or not value.strip():
        raise ValueError(f"Incomplete BBCode in {path.name}")
    return {"bytes": path.stat().st_size, "sha256": digest(path)}


def put_identical(target: Path, data: bytes) -> None:
    if target.exists():
        if not target.is_file() or target.read_bytes() != data:
            raise ValueError(f"Refusing to replace different existing file: {target}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(data)


def prepare(stage: Path | None = None) -> dict:
    current = DOCS / "package-current.json"
    plan_path = current if current.exists() else DOCS / "package.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    alpha = json.loads((ROOT / "docs/releases/v0.1.0-alpha.1/verification.json").read_text(encoding="utf-8"))
    source = ROOT / "mod/Baiqi"
    files = manifest_files(source)
    expected = {row["path"]: row["sha256"] for row in alpha["product_manifest"]}
    actual = {name: digest(contained(source, name)) for name in files}
    if actual != expected or len(files) != 87:
        raise ValueError("Product differs from the published Alpha 1 inventory")
    copy_map = {f"content/{name}": contained(source, name).read_bytes() for name in files}
    descriptions = {}
    for name in ("description.bbcode", plan.get("change_notes", "changenotes.bbcode")):
        descriptions[name] = bbcode(DOCS / name)
        copy_map[name] = (DOCS / name).read_bytes()
    media = []
    for entry in plan["media"]:
        asset = contained(ROOT, entry["repository_path"])
        if digest(asset) != entry["sha256"]:
            raise ValueError(f"Media hash differs: {entry['repository_path']}")
        if entry["upload"] and not 0 < asset.stat().st_size < 1_000_000:
            raise ValueError("Upload image must be smaller than 1,000,000 bytes")
        media.append({key: entry[key] for key in ("role", "sha256", "upload")})
        if entry["upload"]:
            name = "preview.jpg" if entry["role"] == "primary_preview" else f"gallery/{entry.get('upload_filename', asset.name)}"
            copy_map[name] = asset.read_bytes()
    copy_map["package.json"] = plan_path.read_bytes()
    if stage is not None:
        stage = stage.resolve()
        allowed = (ROOT / "dist/workshop").resolve()
        if not stage.is_relative_to(allowed) or stage == allowed:
            raise ValueError("Stage must be a child of this workspace's dist/workshop")
        if stage.exists():
            existing = {p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()}
            if existing - set(copy_map):
                raise ValueError("Unexpected existing staging files; select a new target")
        for name, data in copy_map.items():
            target = contained(stage, name)
            if target.exists() and (not target.is_file() or target.read_bytes() != data):
                raise ValueError(f"Different staging content: {name}")
        for name, data in copy_map.items():
            put_identical(contained(stage, name), data)
        if any(contained(stage, name).read_bytes() != data for name, data in copy_map.items()):
            raise ValueError("Staging readback differs")
    return {"schema": "civ6.workshop-local-verification/v1", "release": plan["release"],
            "internal_build": 74, "product_files": len(files), "alpha_hashes_match": True,
            "bbcode": descriptions, "media": media, "stage_readback": stage is not None,
            "steam_api_initialized": False, "steam_upload_attempted": False,
            "scope": "Local files only; no Steam publication or game acceptance credit."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.stage), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Workshop preparation failed: {exc}\n")


if __name__ == "__main__":
    main()
