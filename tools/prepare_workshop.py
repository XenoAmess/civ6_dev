"""Check/stage the pinned Alpha Workshop package locally; never contacts Steam."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

try:
    from .build_mod import contained, manifest_files
except ImportError:
    from build_mod import contained, manifest_files

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE = "v0.1.0-alpha.1"
DOCS = ROOT / "docs/workshop" / DEFAULT_RELEASE


def release_docs(release: str) -> Path:
    if not isinstance(release, str) or not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+-alpha\.[0-9]+", release):
        raise ValueError("Expected an explicit Alpha release name")
    return contained(contained(ROOT, "docs/workshop"), release)


def validated_product(plan: dict, verification: dict, release: str, source: Path) -> tuple[int, list[str]]:
    """Compare the current product against this release's immutable inventory."""
    if plan.get("release") != release or verification.get("release") != release:
        raise ValueError("Release mismatch")
    build, pinned_build = plan.get("internal_build"), verification.get("internal_build")
    count = verification.get("product_files")
    if (type(build) is not int or build <= 0 or type(pinned_build) is not int
            or build != pinned_build or type(count) is not int or count <= 0):
        raise ValueError("Invalid product build or file count")
    manifest = verification.get("product_manifest")
    if not isinstance(manifest, list) or len(manifest) != count:
        raise ValueError("Invalid product manifest")
    expected, resolved = {}, set()
    for row in manifest:
        if not isinstance(row, dict):
            raise ValueError("Invalid manifest row")
        name, sha = row.get("path"), row.get("sha256")
        if (not isinstance(name, str) or not name or name in expected
                or PurePosixPath(name).as_posix() != name or "\\" in name
                or not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha)):
            raise ValueError("Invalid or duplicate manifest path/hash")
        path = contained(source, name)
        if path in resolved:
            raise ValueError("Aliased product paths")
        resolved.add(path)
        expected[name] = sha
    files = manifest_files(source)
    actual = {name: digest(contained(source, name)) for name in files}
    if len(files) != count or len(actual) != count or actual != expected:
        raise ValueError(f"Product differs from the pinned {release} inventory")
    return build, files


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


def prepare(stage: Path | None = None, *, release: str = DEFAULT_RELEASE) -> dict:
    docs = release_docs(release)
    current = contained(docs, "package-current.json")
    plan_path = current if current.exists() else contained(docs, "package.json")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    pin = contained(contained(ROOT, "docs/releases"), f"{release}/verification.json")
    alpha = json.loads(pin.read_text(encoding="utf-8"))
    source = ROOT / "mod/Baiqi"
    build, files = validated_product(plan, alpha, release, source)
    copy_map = {f"content/{name}": contained(source, name).read_bytes() for name in files}
    descriptions = {}
    for name in ("description.bbcode", plan.get("change_notes", "changenotes.bbcode")):
        description = contained(docs, name)
        descriptions[name] = bbcode(description)
        copy_map[name] = description.read_bytes()
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
            if name in copy_map:
                raise ValueError(f"Duplicate staged media name: {name}")
            if not re.fullmatch(r"(?:preview|gallery/[a-z0-9-]+)\.jpg", name):
                raise ValueError("Unexpected staged image filename")
            copy_map[name] = asset.read_bytes()
    copy_map["package.json"] = plan_path.read_bytes()
    if stage is not None:
        stage = stage.resolve()
        allowed = contained(ROOT, "dist/workshop")
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
            "internal_build": build, "product_files": len(files), "alpha_hashes_match": True,
            "bbcode": descriptions, "media": media, "stage_readback": stage is not None,
            "steam_api_initialized": False, "steam_upload_attempted": False,
            "scope": "Local files only; no Steam publication or game acceptance credit."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path)
    parser.add_argument("--release", default=DEFAULT_RELEASE)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.stage, release=args.release), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Workshop preparation failed: {exc}\n")


if __name__ == "__main__":
    main()
