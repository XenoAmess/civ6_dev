"""Static suppression in private benchmark copies; never a product toggle."""
from __future__ import annotations

NOOP = 'function(...) return false,nil,"private_static_control" end'
UNAVAILABLE = 'function(...) return "UNAVAILABLE",nil,"private_static_control" end'


def edits() -> dict[str,list[tuple[str,str]]]:
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
    return result


def transform(source: str,key: str) -> tuple[str,list[dict]]:
    """Insert reviewed lexical assignments before consumers capture callbacks."""
    if not isinstance(source,str) or not isinstance(key,str):raise TypeError('Expected source/key strings')
    report=[]
    for anchor,body in edits().get(key,[]):
        if anchor=='@EOF':
            source+=body
        else:
            if source.count(anchor)!=1:raise ValueError(f'Nonunique private control anchor: {key}')
            source=source.replace(anchor,body+anchor,1)
        report.append({'anchor':anchor,'insert_before':body,'scope':'Private static copy only'})
    return source,report
