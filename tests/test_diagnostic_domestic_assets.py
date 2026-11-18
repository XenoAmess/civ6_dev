"""Read-only diagnostic assets: isolated ports, actual Lua reader and JSON shape."""
from pathlib import Path
import json
import unittest
from lupa.lua51 import LuaRuntime as L51,lua_type as Type51
from lupa.lua53 import LuaRuntime as L53,lua_type as Type53
R=Path(__file__).resolve().parents[1]
sources={'reader':R/'tools/lua/diagnostic_domestic_assets.lua','fixture':R/'tests/lua/mock_domestic_assets.lua','queue':R/'tools/lua/diagnostic_production_snapshot.lua'}
def plain(v,lua_type,hint=False):
 if lua_type(v)!='table':return v
 keys=list(v.keys())
 if hint:
  assert set(keys)==set(range(1,len(keys)+1));return[plain(v[i],lua_type)for i in range(1,len(keys)+1)]
 return{k:plain(value,lua_type,k in('fields','items'))for k,value in v.items()}
def decode(n):
 if n['kind']=='nil':return None
 if n['kind'] in('number','boolean','string'):return n['value']
 assert n['kind']=='table';return{decode(x['key']):decode(x['value'])for x in n['items']}
cases=[('baseline','',True),('ordinaryLeader',"F.S.leader='LEADER_GORGO';F.request.expectedLeader='LEADER_GORGO'",True),
 ('configNilPlayerFallback','F.config.IsHuman=nil',True),('coreTypeFallback','for _,u in pairs(F.unitMap)do u.GetUnitType=nil end',True),
 ('nativeZeroReturnProperty','F.unitMap[111].GetProperty=function()end',True),
 ('emptyQueue','F.S.queueSize=0;F.S.hash=0;F.entries[0]=nil;F.entries[1]=nil',True),
 ('unitCorpsHead','F.S.queueSize=1;F.S.hash=205;F.entries[0]={Directive=1,UnitType=5,MilitaryFormationType=1};F.entries[1]=nil',True),
 ('knownAbsentSelectedUnit','F.unitMap[111]=nil',True),
 ('unknownFaith','F.religion.GetFaithBalance=nil',False),('zeroArityFaith','F.religion.GetFaithBalance=function()end',False),
 ('nonfiniteGold','F.S.gold=0/0',False),('wrongLeader',"F.S.leader='LEADER_GORGO'",False),
 ('nonCallableConfigHuman','F.config.IsHuman=false',False),('falseConfigHuman','F.config.IsHuman=function()return false end',False),
 ('configUnknownMustNotFallback','F.config.IsHuman=function()end',False),('missingBothHumanPorts','F.config.IsHuman=nil;F.p.IsHuman=nil',False),
 ('foreignCityID','F.city.GetID=function()return 78 end',False),('foreignUnitOwner','F.unitMap[111].GetOwner=function()return 1 end',False),
 ('missingListedCity','F.cities.FindID=function()end',False),('missingListedUnit','F.units.FindID=function()end',False),
 ('inconsistentCollectionCount','F.units.GetCount=function()return 4 end',False),('changedCollection',"F.units.GetCount=function()F.S.count=(F.S.count or 0)+1;return F.S.count>2 and 2 or 3 end",False),
 ('partialTailQueue','F.entries[1]=nil',False),('queueHeadMismatch','F.entries[0]={Directive=1,UnitType=5,MilitaryFormationType=0}',False),
 ('badQueueDatabaseID','F.entries[1].UnitType=999',False),('unknownQueueDirective','F.entries[1].Directive=999',False),
 ('nonSerializableQueueTail','F.entries[1].opaque=function()end',False),('cyclicQueueEntry','F.entries[1].cycle=F.entries[1]',False),
 ('extraQueueRow','F.entries[2]={Directive=2,BuildingType=10}',False),('queueNonfiniteCost','F.q.GetBuildingCost=function()return math.huge end',False),
 ('unknownFocus','F.citizen.IsFavoredYield=function()end',False),('missingCitizenLock','F.target[5][12]=nil',False),
 ('extraCitizenLock','F.target[5][99]=0',False),('duplicateCitizenPlot','F.target[3][12]=901',False),
 ('duplicatePurchasedPlot','F.purchased[8]=901',False),('foreignPlotID','F.plot.GetIndex=function()return 904 end',False),
 ('zeroArityCharge','F.unitMap[111].GetBuildCharges=function()end',False),('unknownReligiousCharges','F.unitMap[222].GetReligion=function()return{}end',False),
 ('turnChanged','F.E.Game.GetCurrentGameTurn=function()F.S.reads=F.S.reads+1;return F.S.reads>1 and 115 or 114 end',False),
 ('balanceChangedDuringRead','F.treasury.GetGoldBalance=function()F.S.gold=F.S.gold+1;return F.S.gold end',False),
 ('sparseRequestedIDs','F.request.cityIDs={[2]=77}',False),('duplicateRequestedIDs','F.request.unitIDs={111,111}',False),
 ('foreignPlayer','F.request.playerID=1',False),('requestDetachedAtEntry','F.treasury.GetGoldBalance=function()F.request.cityIDs[1]=999;return F.S.gold end',True),
 ('uiReligionPorts','for _,id in ipairs({222,333})do local u=F.unitMap[id];u.GetReligion=nil;u.GetReligionType=function()return 4 end;u.GetSpreadCharges=function()return 2 end end',True),
 ('nonCallableCoreReligionMustNotFallback','F.unitMap[222].GetReligion=false;F.unitMap[222].GetReligionType=function()return 4 end;F.unitMap[222].GetSpreadCharges=function()return 2 end',False),
 ('zeroArityUIReligionCharges','F.unitMap[222].GetReligion=nil;F.unitMap[222].GetReligionType=function()return 4 end;F.unitMap[222].GetSpreadCharges=function()end',False),
 ('missingBothReligiousPorts','F.unitMap[222].GetReligion=nil',False)]

class DomesticAssetsTests(unittest.TestCase):
 def test_reader_boundaries_and_json_roundtrip(self):
  for version,VM,lua_type in(('Lua51',L51,Type51),('Lua53',L53,Type53)):
   for name,change,expected in cases:
    with self.subTest(VM=version,scenario=name):
     v=VM(unpack_returned_tuples=True)
     env=v.globals()
     env.F=v.execute(sources['fixture'].read_text(encoding='utf-8'))
     env.Q=v.execute(sources['queue'].read_text(encoding='utf-8'))
     env.M=v.execute(sources['reader'].read_text(encoding='utf-8'))
     assert env.F['S']['reads']==env.F['S']['writes']==0,'Module import performed Native activity'
     env.F['E']['QueueSnapshot']=env.Q
     v.execute(change)
     raw=env.M['Read'](env.F['E'],env.F['request'])
     saved=json.loads(json.dumps(plain(raw,lua_type),ensure_ascii=False,allow_nan=False))
     assert saved['qualified_no_unknowns'] is expected,(version,name,saved)
     assert env.F['S']['writes']==0,(version,name,'Native write')
     unknown=[f['key'] for f in saved['fields'] if f['value']['kind']=='UNKNOWN']
     assert saved['errors']==len(unknown) and (not unknown)==expected,(version,name,unknown)
     if expected:
        f={r['key']:decode(r['value'])for r in saved['fields']};assert f['gold']==100.25 and f['faith']==200.5
        assert f['city.77.focus'][1]['favored'] is True and f['city.77.focus'][6]['disfavored'] is True
        assert f['city.77.citizens'][1]=={'key':4,'plotID':901,'count':1,'locked':1}
        assert f['city.77.citizens'][2]=={'key':12,'plotID':902,'count':2,'locked':0}
        assert f['plot.903']['owner']==-1 and f['unit.222.religion']['charges']==2 and f['unit.333.type']['type']=='UNIT_APOSTLE'
        if name=='knownAbsentSelectedUnit':assert f['unit.111.present'] is False
        else:assert f['unit.111.BuildCharges']==3 and f['unit.111.cooldown'] is None
        if name=='emptyQueue':assert f['city.77.queue']['head']['status']=='EMPTY' and f['city.77.queue']['items']=={}
        elif name=='unitCorpsHead':assert f['city.77.queue']['head']['cost']==40 and f['city.77.queue']['items'][1]['entry']['MilitaryFormationType']==1
        else:assert f['city.77.queue']['head']['progress']==7 and f['city.77.queue']['items'][2]['entry']['UnitType']==5

 def test_tail_changes_are_visible_and_prior_snapshot_is_detached(self):
  for version,VM,lua_type in(('Lua51',L51,Type51),('Lua53',L53,Type53)):
   with self.subTest(VM=version):
    v=VM(unpack_returned_tuples=True);env=v.globals()
    env.F=v.execute(sources['fixture'].read_text(encoding='utf-8'))
    env.Q=v.execute(sources['queue'].read_text(encoding='utf-8'))
    env.M=v.execute(sources['reader'].read_text(encoding='utf-8'))
    env.F['E']['QueueSnapshot']=env.Q
    old=env.M.Read(env.F.E,env.F.request)
    before=json.loads(json.dumps(plain(old,lua_type),allow_nan=False))
    v.execute('F.entries[1].UnitType=6')
    after=json.loads(json.dumps(plain(env.M.Read(env.F.E,env.F.request),lua_type),allow_nan=False))
    self.assertTrue(before['qualified_no_unknowns'] and after['qualified_no_unknowns'])
    self.assertEqual(plain(old,lua_type),before)
    a={r['key']:decode(r['value'])for r in before['fields']}
    b={r['key']:decode(r['value'])for r in after['fields']}
    self.assertEqual(a['city.77.queue']['head'],b['city.77.queue']['head'])
    self.assertEqual(a['city.77.queue']['items'][2]['entry']['UnitType'],5)
    self.assertEqual(b['city.77.queue']['items'][2]['entry']['UnitType'],6)
    self.assertEqual(env.F.S.writes,0)

if __name__=='__main__':unittest.main()
