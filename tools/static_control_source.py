"""Static suppression in private benchmark copies; never a product toggle."""
from __future__ import annotations
from pathlib import Path
import xml.etree.ElementTree as ET

NOOP = 'function(...) return false,nil,"private_static_control" end'
UNAVAILABLE = 'function(...) return "UNAVAILABLE",nil,"private_static_control" end'


def resolve_source_version(value: int | None = None) -> int:
    if value is None:
        text=ET.fromstring((Path(__file__).resolve().parents[1]/'mod/Baiqi/Baiqi.modinfo').read_bytes()).get('version')
        if text not in ('67','68','69','70','71','72','73','74','75','76','77','78','79','80','81','82','83','84','85','86','87','88','89','90','91','92','93','94','95','96','97','98','99','100','101','102','103','104','105'):raise ValueError('Unsupported actual source version')
        value=int(text)
    if type(value) is not int or value not in (67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105):raise ValueError('Unsupported source version')
    return value


def edits(source_version: int | None = None) -> dict[str,list[tuple[str,str]]]:
    version=resolve_source_version(source_version)
    result = {
        'Lua/BaiqiController.lua': [
            ('print("BAIQI|ui_controller_loaded|version=2|mandatory_admin=true")',
             f'BaiqiController.RunNow={NOOP}\nBaiqiController.Update={NOOP}\n'),
            ('if Events.UnitGreatPersonActivated then Events.UnitGreatPersonActivated.Add(OnGreatPersonActivated) end',
             f'OnGreatPersonActivated={NOOP}\n'),
            ('if Events.GreatWorkCreated then Events.GreatWorkCreated.Add(OnGreatWorkCreated) end',
             f'OnGreatWorkCreated={NOOP}\n'),
        ],
        'Lua/BaiqiAdmin.lua': [('@EOF', f'\nBaiqiAdmin.Run={NOOP}\n')],
        'UI/BaiqiExecutor.lua': [('local function Update(delta)', f'Recover={NOOP}\n')],
        'Lua/BaiqiCreativeIntentGameplay.lua': [('BaiqiCreativeIntentGameplay={}',
             f'Inspect={UNAVAILABLE}\nPrepare={NOOP}\nOnCreated={NOOP}\nBootstrap={NOOP}\n')],
        'Lua/BaiqiNaturalistPurchaseIntentGameplay.lua': [('local bridge={version=1,marker=MARKER}',
             f'Inspect={UNAVAILABLE}\nPrepare={NOOP}\n'),
             ('for _,name in ipairs({"UnitAddedToMap","PlayerTurnDeactivated"}) do',f'ObserveEvent={NOOP}\n')],
        'Lua/BaiqiArchaeologyIntentGameplay.lua': [('local bridge={version=1,marker=BRIDGE_MARKER,PrepareExcavation=Protected(PrepareExcavation,false),',
             f'Inspect={UNAVAILABLE}\nPrepareExcavation={NOOP}\nPrepareChoice={NOOP}\nPreparePendingChoice={NOOP}\nObserveCreated={NOOP}\n')],
    }
    for stem in ('GP','Religious','Naturalist'):
        name=f'Lua/Baiqi{stem}IntentGameplay.lua'
        bridge='local bridge={version=1,marker=MARKER,Inspect=Protected(Inspect,"UNAVAILABLE")'
        body=f'Inspect={UNAVAILABLE}\nPrepare={NOOP}\n'
        if stem=='GP':body+=f'Observe={UNAVAILABLE}\n'
        exposed={'GP':'BaiqiGreatPersonIntentBridge','Religious':'BaiqiReligiousIntentBridge','Naturalist':'BaiqiNaturalistIntentBridge'}[stem]
        result[name]=[(bridge,body),
            (f'if type(ExposedMembers)=="table" and (ExposedMembers.{exposed}==nil',f'Bootstrap={NOOP}\n')]
    if version>=68:
        result['Lua/BaiqiProphetIntentGameplay.lua']=[
            ('local bridge={version=1,marker=MARKER,Inspect=Protected(Inspect,"UNAVAILABLE")',
             f'Inspect={UNAVAILABLE}\nPrepare={NOOP}\nObserve={UNAVAILABLE}\n'),
            ('if type(ExposedMembers)=="table" and (ExposedMembers.BaiqiProphetIntentBridge==nil',
             f'Bootstrap={NOOP}\n')]
    if version>=84:
        result['Lua/BaiqiSettlerGoalsGameplay.lua']=[
            ('local MARKER="baiqi-settler-goals-v1"',
             f'if api then api.Remember={UNAVAILABLE};api.Forget={UNAVAILABLE} end\n')]
    if version>=89:
        result['Lua/BaiqiMissionaryPurchaseIntentGameplay.lua']=[
            ('local bridge={version=1,marker=MARKER}',f'Inspect={UNAVAILABLE}\nPrepare={NOOP}\n'),
            ('for _,name in ipairs({"UnitAddedToMap","PlayerTurnDeactivated"}) do',f'ObserveEvent={NOOP}\n')]
        result['Lua/BaiqiReligiousIntentGameplay.lua'].append(
            ('local function Bootstrap()',f'BaiqiReligiousIntentGameplay.Initialize={NOOP}\n'))
    if version>=105:
        result['Lua/BaiqiReligiousIntentGameplay.lua'].append(
            ('if not InstallFinalSubscriptions() then',f'InstallFinalSubscriptions={NOOP}\n'))
    return result


def transform(source: str,key: str,source_version: int | None = None) -> tuple[str,list[dict]]:
    """Insert reviewed lexical assignments before consumers capture callbacks."""
    if not isinstance(source,str) or not isinstance(key,str):raise TypeError('Expected source/key strings')
    report=[]
    for anchor,body in edits(source_version).get(key,[]):
        if anchor=='@EOF':
            source+=body
        else:
            if source.count(anchor)!=1:raise ValueError(f'Nonunique private control anchor: {key}')
            source=source.replace(anchor,body+anchor,1)
        report.append({'anchor':anchor,'insert_before':body,'scope':'Private static copy only'})
    return source,report
