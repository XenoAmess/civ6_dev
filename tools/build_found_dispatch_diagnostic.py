"""Build an isolated source152/153 live-FOUND diagnostic; never install or run it."""
from pathlib import Path
import argparse
import json
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''):
    sys.path.insert(0, str(ROOT))
from tools.build_mod import contained, digest, manifest_files, package

HELPER = ROOT / 'tools/lua/diagnostic_found_dispatch.lua'
ANCHOR = b'local C = BaiqiConfig\n'
OLD = b'''    dispatch=function()
      if entered or checking or not Bound() then return false,"armed_live_dispatch_held" end
      checking=true
      local ok,fresh,why=pcall(Qualify)
      checking=false
      if not ok or not fresh or not Bound() then return false,why or "armed_live_qualification_unavailable" end
      -- Consume before entering the writer. False, void and throw are all
      -- unresolved native outcomes, never permission for another dispatch.
      entered=true;pending.dispatch=nil
      Log("request", "id="..id.."|source=BACKGROUND|unit="..unitID.."|operation=FOUND_CITY|plot="..founding.index.."|from="..founding.index)
      local called=pcall(foundingNative.writer,fresh,action,params)
      if not called then Log("settler_request_unresolved","id="..id.."|unit="..unitID.."|native_call_error=true|token="..settlementToken) end
      return true,"submitted"
    end'''
NEW = b'''    dispatch=function()
      if entered or checking or not Bound() then
        _P6FoundDispatch(unitID,id,armedTurn,turn,"held","armed_live_dispatch_held",entered)
        return false,"armed_live_dispatch_held"
      end
      checking=true
      local ok,fresh,why=pcall(Qualify)
      checking=false
      if not ok or not fresh or not Bound() then
        _P6FoundDispatch(unitID,id,armedTurn,turn,"qualification",
          not ok and "qualify_error" or why or "armed_live_qualification_unavailable",entered,ok)
        return false,why or "armed_live_qualification_unavailable"
      end
      -- Consume before entering the writer. False, void and throw are all
      -- unresolved native outcomes, never permission for another dispatch.
      entered=true;pending.dispatch=nil
      Log("request", "id="..id.."|source=BACKGROUND|unit="..unitID.."|operation=FOUND_CITY|plot="..founding.index.."|from="..founding.index)
      local called=pcall(foundingNative.writer,fresh,action,params)
      _P6FoundDispatch(unitID,id,armedTurn,turn,"writer","submitted",entered,ok,called)
      if not called then Log("settler_request_unresolved","id="..id.."|unit="..unitID.."|native_call_error=true|token="..settlementToken) end
      return true,"submitted"
    end'''


def declaration():
    return (b'-- PRIVATE live-FOUND outcome observation; no new native reads.\n'
            b'local _P6FoundDispatch\ndo\nlocal Record,Snapshot=(function()\n' + HELPER.read_bytes()
            + b'\nend)()\n_P6FoundDispatch=Record\nBaiqiController.P6FoundDispatchSnapshot=Snapshot\nend\n')


def instrument(raw):
    if not isinstance(raw, bytes):
        raise TypeError('Controller bytes required')
    if b'_P6FoundDispatch' in raw or raw.count(ANCHOR) != 1 or raw.count(OLD) != 1:
        raise ValueError('Unknown or already instrumented controller')
    return raw.replace(ANCHOR, declaration() + ANCHOR, 1).replace(OLD, NEW, 1)


def recover(raw):
    inserted = declaration() + ANCHOR
    if not isinstance(raw, bytes) or raw.count(inserted) != 1 or raw.count(NEW) != 1:
        raise ValueError('Unknown diagnostic controller')
    return raw.replace(inserted, ANCHOR, 1).replace(NEW, OLD, 1)


def build(output):
    from lupa.lua51 import LuaRuntime as L51
    from lupa.lua53 import LuaRuntime as L53
    source = ROOT / 'mod/Baiqi'
    version = ET.fromstring((source / 'Baiqi.modinfo').read_bytes()).get('version')
    if version not in ('152', '153','154','155','156','157','158','159','160','161','162','163','164','165','166','167','168','169'):
        raise ValueError('Only source152/153 is qualified')
    out = Path(output).resolve()
    if not out.is_relative_to(ROOT / '.local-model') or out.exists():
        raise ValueError('New private output directory required')
    names = manifest_files(source)
    files = {n: contained(source, n).read_bytes() for n in names}
    controller = 'Lua/BaiqiController.lua'
    original = files[controller]
    files[controller] = instrument(original)
    if recover(files[controller]) != original:
        raise ValueError('Source recovery mismatch')
    for runtime in (L51(), L53()):
        for n, raw in files.items():
            if n.endswith('.lua'):
                runtime.compile(raw)
    target = out / 'Baiqi'
    target.mkdir(parents=True)
    for n, raw in files.items():
        p = contained(target, n)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open('xb') as f:
            f.write(raw)
    archive = out / f'Baiqi-found-dispatch{version}.zip'
    package(target, archive)
    result = {'mode': f'baiqi{version}-found-dispatch-v1', 'source_version': int(version), 'files': len(names),
              'changed_files': [controller], 'source_hashes': {n: digest(source / n) for n in names},
              'instrumented_hashes': {n: digest(target / n) for n in names},
              'helper_sha256': digest(HELPER), 'archive_sha256': digest(archive),
              'lua51_compiled': True, 'lua53_compiled': True, 'event_capacity': 32,
              'performance_capture': False, 'installed': False}
    with (out / 'diagnostic-build.json').open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.output_dir), indent=2))
