from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53

from tools.build_mod import manifest_files, contained
from tools.diagnostic_native_sites import prepare, core_closure, PROVIDER

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'tools/lua/diagnostic_native_sites.lua'
HARNESS = r'''
return function(M,which)
 local h={calls=0,turn=139,localPlayer=0,sdkWrites=0};local marker={};local journal=setmetatable({},{__index=function()error('Do not traverse native arguments')end});local result={}
 local actor;local backing={}
 local function Native(...)
  h.calls=h.calls+1;h.args={n=select('#',...),...}
  if h.after then h.after()end
  if h.raise then error(marker)end;if h.void then return end;if h.falseReturn then return false end
  return nil,false,result,nil
 end
 backing.SetProperty=Native;actor=setmetatable({},{__index=backing,__newindex=function()h.sdkWrites=h.sdkWrites+1;error('SDK read-only')end})
 local o={context='actual-fixture',capacity=2,unpack=table.unpack or unpack,frame=function()if h.frameError then error(marker)end;return h.turn,h.localPlayer end,describe=function(kind,target)
  assert(target==actor);if h.ownerError then error(marker)end
  if h.badOwner then return{owner=true}end;if h.reservedMetadata then return{owner=0,returned=true}end;if h.fractionalID then return{owner=0,id=1.5}end;if h.longMetadata then local d={owner=0};for i=1,9 do d[tostring(i)]=i end;return d end
  return{owner=h.foreign and 1 or 0,id=42}
 end}
 local s=M.New(o);local fn
 if which=='static-global'then fn=s.Static('site','GLOBAL',Native)
 elseif which=='static-city'then fn=s.Static('site','CITY',Native)
 elseif which=='static-unit'then fn=s.Static('site','UNIT',Native)
 else fn=s.Method('site','PLAYER',actor,'SetProperty')end
 if which=='frame-error'then h.frameError=true elseif which=='owner-error'then h.ownerError=true elseif which=='bad-owner'then h.badOwner=true elseif which=='long-metadata'then h.longMetadata=true elseif which=='fractional-turn'then h.turn=139.5 elseif which=='unknown-local'then h.localPlayer=-1 elseif which=='foreign'then h.foreign=true elseif which=='native-error'or which=='metadata-and-native-error'then h.raise=true;h.ownerError=which=='metadata-and-native-error'elseif which=='void'then h.void=true elseif which=='false-return'then h.falseReturn=true end
 if which=='before-store-error'then setmetatable(s.rows,{__newindex=function()error(marker)end})end
 if which=='reserved-metadata'then h.reservedMetadata=true elseif which=='fractional-id'then h.fractionalID=true end
 if which=='after-store-error'then h.after=function()setmetatable(s.rows[1],{__newindex=function()error(marker)end})end end
 local function Call()
  if which=='static-global'then return fn('KEY',journal,nil)
  elseif which=='static-city'or which=='static-unit'then return fn(actor,7,journal,nil)
  else return fn('KEY',journal,nil)end
 end
 if which=='native-error'or which=='metadata-and-native-error'then local ok,e=pcall(Call);assert(not ok and e==marker and h.calls==1 and not s.rows[1].returned)
 elseif which=='void'then assert(select('#',Call())==0 and s.rows[1].returnCount==0)
 elseif which=='false-return'then assert(select('#',Call())==1 and s.rows[1].returnCount==1)
 else local r={n=0};local function Capture(...)r={n=select('#',...),...}end;Capture(Call());assert(r.n==4 and r[1]==nil and r[2]==false and r[3]==result and r[4]==nil)end
 assert(h.calls==1 and h.sdkWrites==0 and h.args[h.args.n]==nil)
 if which=='static-global'then assert(h.args.n==3 and h.args[1]=='KEY'and h.args[2]==journal and s.rows[1].ownerScope=='GLOBAL'and s.rows[1].owner==nil)
 else assert(h.args.n==4 and h.args[1]==actor and h.args[3]==journal)end
 local metadataError=which=='frame-error'or which=='owner-error'or which=='bad-owner'or which=='long-metadata'or which=='fractional-turn'or which=='unknown-local'or which=='metadata-and-native-error'or which=='before-store-error'or which=='reserved-metadata'or which=='fractional-id'
 assert(s.metadataErrors==(metadataError and 1 or 0));if which=='before-store-error'then assert(#s.rows==0)else assert(s.rows[1].metadataKnown==not metadataError)end
 if which=='foreign'then assert(s.rows[1].owner==1 and s.rows[1].localPlayer==0)end
 assert(s.afterErrors==(which=='after-store-error'and 1 or 0))
 if which=='capacity'then for i=1,6 do Call()end;assert(h.calls==7 and s.calls==7 and #s.rows==2 and s.dropped==5)end
 if which=='freeze'then assert(s.Freeze());local prior=s.calls;Call();assert(s.calls==prior and h.calls==2 and fn~=Native)end
 if which=='retire'then assert(s.Retire());local prior=s.calls;Call();assert(s.calls==prior and h.calls==2 and s.retired and not s.active)end
 if which=='lookup-order'then
  local receiverReads=0;local function GetActor()receiverReads=receiverReads+1;return actor end
  local function Argument()backing.SetProperty=function()error('Wrong late lookup')end;return 'KEY'end
  s.Method('lookup','PLAYER',GetActor(),'SetProperty')(Argument(),journal,nil)
  assert(receiverReads==1 and h.calls==2)
 end
 return true
end
'''


class NativeSiteObserverTests(unittest.TestCase):
    def payload(self):
        root = ROOT/'mod/Baiqi'
        return {n: contained(root, n).read_bytes() for n in manifest_files(root)}

    def test_real_producer_native_arguments_errors_readonly_receivers_and_finite_lifecycle(self):
        cases = ['normal', 'static-global', 'static-city', 'static-unit', 'frame-error', 'owner-error',
                 'bad-owner', 'long-metadata', 'fractional-turn', 'unknown-local', 'foreign',
                 'native-error', 'metadata-and-native-error', 'void', 'false-return', 'before-store-error',
                 'after-store-error', 'capacity', 'freeze', 'retire', 'lookup-order', 'reserved-metadata', 'fractional-id']
        for VM in (L51, L53):
            lua = VM(); run = lua.execute(HARNESS); module = lua.execute(MODULE.read_text(encoding='utf-8'))
            for case in cases:
                with self.subTest(vm=VM.__module__, case=case):
                    self.assertTrue(run(module, case))

    def test_actual_provider_resolves_same_ids_foreign_owners_global_and_treasury_without_sdk_mutation(self):
        fixture = r'''
H={calls=0,writes=0};Game={GetCurrentGameTurn=function()return 139 end,GetLocalPlayer=function()return 0 end}
local function ReadOnly(t)return setmetatable({},{__index=t,__newindex=function()H.writes=H.writes+1;error('SDK read-only')end})end
local function Native(...)H.calls=H.calls+1;H.args={n=select('#',...),...};return nil,false end
local treasury0,treasury1=ReadOnly({ChangeGoldBalance=Native}),ReadOnly({ChangeGoldBalance=Native})
local player0=ReadOnly({SetProperty=Native,GetTreasury=function()return treasury0 end})
local player1=ReadOnly({SetProperty=Native,GetTreasury=function()return treasury1 end})
Players=ReadOnly({[0]=player0,[1]=player1});PlayerManager=ReadOnly({GetAliveIDs=function()return{0,1}end})
Targets={player0,player1,treasury0,treasury1,ReadOnly({SetProperty=Native,GetOwner=function()return 1 end,GetID=function()return 42 end}),ReadOnly({SetProperty=Native,GetOwner=function()return 0 end,GetID=function()return 42 end}),ReadOnly({SetProperty=Native,GetOwner=function()return -1 end,GetX=function()return 5 end,GetY=function()return 7 end})}
'''
        exercise = r'''
local s=P6CoreSites174
for _,v in ipairs({{1,'PLAYER',0},{2,'PLAYER',1},{3,'TREASURY',0},{4,'TREASURY',1},{5,'UNIT',1},{6,'UNIT',0},{7,'PLOT',-1}})do
 local key=v[2]=='TREASURY'and'ChangeGoldBalance'or'SetProperty';local a,b=s.Method('actual-provider',v[2],Targets[v[1]],key)('KEY',{})
 local r=s.rows[#s.rows];assert(a==nil and b==false and r.owner==v[3]and r.localPlayer==0 and r.metadataKnown and r.returned and r.returnCount==2 and H.args[1]==Targets[v[1]])
end
assert(H.calls==7 and H.writes==0 and s.metadataErrors==0)
'''
        for VM in (L51, L53):
            lua = VM(); lua.execute(fixture)
            lua.execute('local Factory=(function()\n' + MODULE.read_text(encoding='utf-8') + '\nend)()\n' + PROVIDER)
            lua.execute(exercise)

    def test_actual_40_file_core_closure_all28_sites_exact_inverse_and_both_compilers(self):
        original = self.payload(); payload, receipt = prepare(original, MODULE.read_bytes())
        self.assertEqual(len(original), 119)
        self.assertEqual(len(core_closure(original)), 40)
        self.assertEqual(len(receipt['sites']), 28)
        self.assertTrue(receipt['all_original_bytes_inverse_verified'])
        self.assertEqual(sum(payload[n] != original[n] for n in original), 14)
        self.assertIn('Lua/BaiqiArchaeologyIntentGameplay.lua', receipt['closure'])
        self.assertEqual(receipt['counts']['CityManager.TransferCity'], 1)
        self.assertIn('type(CityManager.TransferCity)', payload['Lua/BaiqiCapture.lua'].decode())
        for VM in (L51, L53):
            lua = VM()
            for name, source in payload.items():
                if name.endswith('.lua'):
                    lua.compile(source.decode('utf-8-sig'))
        with self.assertRaises(ValueError):
            prepare(payload, MODULE.read_bytes())
        incomplete = dict(original); del incomplete['Lua/BaiqiArchaeologyIntentGameplay.lua']
        with self.assertRaises(ValueError):
            prepare(incomplete, MODULE.read_bytes())

    def test_real_capture_transactions_match_original_cost_transfer_failures_and_permissions(self):
        original = self.payload(); patched, _ = prepare(original, MODULE.read_bytes())
        cases = ['success', 'fail-transfer', 'throw-after-transfer', 'fail-charge',
                 'non-baiqi', 'wrong-local', 'missing-native-transfer']
        outcomes = {}
        for VM in (L51, L53):
            for case in cases:
                for instrumented in (False, True):
                    with self.subTest(vm=VM.__module__, case=case, instrumented=instrumented):
                        lua = VM(unpack_returned_tuples=True)
                        lua.execute((ROOT/'tests/lua/mock_requisition.lua').read_text(encoding='utf-8'))
                        lua.execute('''
PlayerManager={GetAliveIDs=function()return{7,3}end};TestCapture.sdkWrites=0
local function ReadOnly(t)return setmetatable({},{__index=t,__newindex=function()TestCapture.sdkWrites=TestCapture.sdkWrites+1;error('SDK read-only')end})end
if ...=='missing-native-transfer'then CityManager.TransferCity=nil end
Game=ReadOnly(Game);CityManager=ReadOnly(CityManager);UnitManager=ReadOnly(UnitManager);Players=ReadOnly(Players);PlayerManager=ReadOnly(PlayerManager)
''', case)
                        for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiPlanner', 'BaiqiRequisition'):
                            lua.execute(original['Lua/'+name+'.lua'].decode('utf-8-sig'))
                        if instrumented:
                            lua.execute('local Factory=(function()\n' + MODULE.read_text(encoding='utf-8') + '\nend)()\n' + PROVIDER)
                        lua.execute((patched if instrumented else original)['Lua/BaiqiCapture.lua'].decode('utf-8-sig'))
                        params = lua.globals().TestParams()
                        lua.execute('''
local case=...
if case=='fail-transfer'then TestCapture.failTransfer=true
elseif case=='throw-after-transfer'then TestCapture.throwAfterTransfer=true
elseif case=='fail-charge'then TestCapture.failCharge=true
elseif case=='non-baiqi'then TestCapture.leader='LEADER_QIN'
elseif case=='wrong-local'then TestCapture.localPlayer=3 end
''', case)
                        returned = lua.globals().BaiqiCapture.Request(7, params)
                        state = lua.execute('''
local w=TestCapture;local journal=w.props.BAIQI_REQUISITION_V1;local record=journal and journal.lastID and journal.operations[journal.lastID]
return w.gold,w.moves,w.owner,w.transferCalls,w.charges,w.finishCalls,w.unitProps.BAIQI_REQUISITION_TURN,record and record.stage,record and record.phase,w.sdkWrites
''')
                        self.assertEqual(state[-1], 0)
                        key = VM.__module__, case
                        if instrumented:
                            self.assertEqual((returned, state), outcomes[key])
                            lua.execute('''
local case=...;local s=P6CoreSites174;assert(s.metadataErrors==0 and s.afterErrors==0 and s.dropped==0)
if case=='non-baiqi'or case=='wrong-local'or case=='missing-native-transfer'then assert(s.calls==0)
else
 assert(s.calls>0);local transfer=0;local incomplete=0
 for _,r in ipairs(s.rows)do
  if r.kind=='CITY'then transfer=transfer+1;assert(r.owner==3 and r.localPlayer==7)end
  if not r.returned then incomplete=incomplete+1 end
 end
 assert(transfer==1)
 if case=='success'then assert(incomplete==0)else assert(incomplete==1)end
end
''', case)
                        else:
                            outcomes[key] = returned, state


if __name__ == '__main__':
    unittest.main()
