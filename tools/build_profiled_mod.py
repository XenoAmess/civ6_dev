"""Create a separate diagnostic copy; never modify or install the release source."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''):
    sys.path.insert(0, str(ROOT))
from tools.build_mod import contained, digest, manifest_files, package

CHILDREN = ('ReadBack', 'ProcessCity', 'ProcessBuilder', 'ProcessSettler', 'ProcessTrader')


def diagnostic_suffix(profile_source: str, child_source: str, controller_hash: str, *,
                      stage: str = 'q9', children: tuple | list = CHILDREN) -> str:
    if not re.fullmatch(r'[0-9a-f]{64}', controller_hash):
        raise ValueError('Invalid controller digest')
    if not isinstance(stage, str) or not re.fullmatch(r'q[1-9][0-9]{0,2}', stage):
        raise ValueError('Invalid stage')
    if not isinstance(children, (list, tuple)) or not 1 <= len(children) <= 12:
        raise ValueError('Invalid children count')
    lua_reserved = set('and break do else elseif end false for function goto if in local nil '
                       'not or repeat return then true until while'.split())
    for name in children:
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) or name in lua_reserved:
            raise ValueError('Invalid child name')
    if len(set(children)) != len(children):
        raise ValueError('Duplicate children')
    lines = [
        '\n-- BAIQI_DIAGNOSTIC_ONLY: internal functions; no gameplay switch.\ndo',
        "assert(P6BaiqiInternalProfile==nil,'Existing diagnostic owner')",
        f"local diagnostic={{source='{stage}-internal',active=true,bindings={{}},controllerSha256='{controller_hash}'}}",
        'diagnostic.NewProfile=(function()\n' + profile_source + '\nend)()',
        'diagnostic.WrapChild=(function()\n' + child_source + '\nend)()',
        'diagnostic.profile=diagnostic.NewProfile(Automation.GetTime,4096)',
        f'''diagnostic.getRoot=function()
 if diagnostic.active and P6PerfStageA and P6PerfStageA.source=='{stage}' and P6PerfStageA.enabled then
  return P6PerfStageA.currentEntry
 end
end''',
    ]
    for name in children:
        lines += [
            f'diagnostic.bindings.{name}={{original={name}}}',
            f"diagnostic.bindings.{name}.wrapped=diagnostic.WrapChild(diagnostic.profile,'{name}',{name},diagnostic.getRoot)",
            f'{name}=diagnostic.bindings.{name}.wrapped',
        ]
    lines += ['diagnostic.Restore=function()', ' local same={}']
    for index, name in enumerate(children, 1):
        lines += [
            f' same[{index}]={name}==diagnostic.bindings.{name}.wrapped',
            f' if same[{index}] then {name}=diagnostic.bindings.{name}.original end',
        ]
    lines += [' diagnostic.active=false', ' return same', 'end',
              'P6BaiqiInternalProfile=diagnostic', 'end', '']
    return '\n'.join(lines)


def build(output_dir: Path) -> dict:
    source = ROOT / 'mod/Baiqi'
    files = manifest_files(source)
    if ET.fromstring((source / 'Baiqi.modinfo').read_bytes()).get('version') != '55':
        raise ValueError('This diagnostic assembler targets source version 55 only')
    controller = (source / 'Lua/BaiqiController.lua').read_bytes()
    text = controller.decode('utf-8-sig')
    for name in CHILDREN:
        if len(re.findall(r'\blocal\s+function\s+' + re.escape(name) + r'\s*\(', text)) != 1:
            raise ValueError(f'Expected one current lexical function: {name}')
    profile = (ROOT / 'tools/lua/diagnostic_profile.lua').read_text(encoding='utf-8')
    child = (ROOT / 'tools/lua/diagnostic_child_profile.lua').read_text(encoding='utf-8')
    suffix = diagnostic_suffix(profile, child, hashlib.sha256(controller).hexdigest())
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    target = output_dir / 'Baiqi'
    for name in files:
        src, dst = contained(source, name), contained(target, name)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    instrumented = target / 'Lua/BaiqiController.lua'
    instrumented.write_bytes(controller + suffix.encode('utf-8'))
    changed = [name for name in files if digest(contained(source, name)) != digest(contained(target, name))]
    if changed != ['Lua/BaiqiController.lua']:
        raise ValueError(f'Unexpected diagnostic differences: {changed}')
    archive = output_dir / 'Baiqi-profile55-q9.zip'
    if package(target, archive) != files:
        raise ValueError('Diagnostic inventory changed')
    result = {'mode': 'diagnostic-only-q9-five-children', 'source_version': 55,
              'source': str(source), 'diagnostic_source': str(target), 'files': len(files),
              'changed_files': changed, 'normal_controller_prefix_unchanged': True,
              'controller_sha256': hashlib.sha256(controller).hexdigest(),
              'instrumented_sha256': digest(instrumented), 'archive_sha256': digest(archive),
              'children': list(CHILDREN), 'installed': False,
              'limits': 'Only five child functions; no all-module coverage, CPU clock or performance pass.'}
    (output_dir / 'diagnostic-build.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path,
                        help='New private output directory, e.g. inside .local-model; must not exist')
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.output_dir), ensure_ascii=False))
    except (OSError, ValueError) as exc:
        parser.exit(1, f'Diagnostic build failed: {exc}\n')


if __name__ == '__main__':
    main()
