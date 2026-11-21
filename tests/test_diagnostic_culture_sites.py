from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
from tools.build_mod import manifest_files, contained
from tools.diagnostic_culture_sites import prepare, PROVIDER

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT/'tools/lua/diagnostic_native_sites.lua'


class CultureSourceSiteTests(unittest.TestCase):
    def payload(self):
        root = ROOT/'mod/Baiqi'
        return {n: contained(root, n).read_bytes() for n in manifest_files(root)}

    def test_exact_three_source_sites_inverse_missing_and_double_compilation(self):
        raw = self.payload(); patched, receipt = prepare(raw, MODULE.read_bytes())
        self.assertEqual(len(raw), 119)
        self.assertEqual(sum(raw[n] != patched[n] for n in raw), 1)
        self.assertEqual([r['line'] for r in receipt['sites']], [768, 775, 864])
        self.assertTrue(receipt['all_original_bytes_inverse_verified'])
        for VM in (L51, L53):
            lua = VM()
            for name, source in patched.items():
                if name.endswith('.lua'):
                    lua.compile(source.decode('utf-8-sig'))
        with self.assertRaises(ValueError):
            prepare(patched, MODULE.read_bytes())
        missing = dict(raw); missing['Lua/BaiqiAdmin.lua'] = raw['Lua/BaiqiAdmin.lua'].replace(b'culture:RequestPolicyChanges(', b'culture:Unknown(')
        with self.assertRaises(ValueError):
            prepare(missing, MODULE.read_bytes())

    def test_real_admin_results_and_native_targets_match_all_three_writes_and_gates(self):
        raw = self.payload(); patched, _ = prepare(raw, MODULE.read_bytes())
        cases = ['government', 'retained', 'policies', 'non-baiqi', 'non-human', 'inactive',
                 'multiplayer', 'hotseat', 'strategic-denied', 'missing-player']
        for VM in (L51, L53):
            for case in cases:
                before = None
                for instrumented in (False, True):
                    with self.subTest(vm=VM.__module__, case=case, instrumented=instrumented):
                        lua = VM(unpack_returned_tuples=True)
                        lua.execute((ROOT/'tests/lua/mock_admin.lua').read_text(encoding='utf-8'))
                        lua.execute((ROOT/'tests/lua/mock_government.lua').read_text(encoding='utf-8'))
                        lua.execute('''
PlayerManager={GetAliveIDs=function()return{7,3}end}
local otherCulture={};Players[3]={GetCulture=function()return otherCulture end}
local w=TestAdmin;local case=...
if case=='retained'then w.government.current=2;w.government.blocker=88
elseif case=='policies'then w.government.changed=true
elseif case=='non-baiqi'then w.leader='LEADER_QIN'
elseif case=='non-human'then PlayerConfigurations[7].IsHuman=function()return false end
elseif case=='inactive'then w.active=false
elseif case=='multiplayer'then GameConfiguration.IsAnyMultiplayer=function()return true end
elseif case=='hotseat'then GameConfiguration.IsHotseat=function()return true end
elseif case=='strategic-denied'then Game.IsAllowStrategicCommands=function()return false end
elseif case=='missing-player'then Players[7]=nil end
''', case)
                        lua.execute(raw['Lua/BaiqiConfig.lua'].decode('utf-8'))
                        lua.execute((patched if instrumented else raw)['Lua/BaiqiAdmin.lua'].decode('utf-8'))
                        lua.execute('for i=1,14 do BaiqiAdmin.Run()end')
                        result = lua.execute('''
local w=TestAdmin;local g=w.government
return #w.requests,w.policyCalls,w.slots[1],w.slots[2],#g.requests,g.requests[1],g.retained,g.current
''')
                        if not instrumented:
                            before = result
                        else:
                            self.assertEqual(result, before)
                            lua.execute('''
local s=P6CultureSites174;local case=...
assert(s.metadataErrors==0 and s.afterErrors==0 and s.dropped==0)
local expected=case=='retained'and 2 or((case=='government'or case=='policies')and 1 or 0)
assert(s.calls==expected and #s.rows==expected)
for _,r in ipairs(s.rows)do assert(r.owner==7 and r.id==7 and r.localPlayer==7 and r.metadataKnown and r.returned)end
if case=='government'then assert(s.rows[1].firstParameter==702)
elseif case=='retained'then assert(s.rows[1].firstParameter==true)
elseif case=='policies'then assert(s.rows[1].argumentTypes[2]=='table'and s.rows[1].argumentTypes[3]=='table')end
''', case)

    def test_actual_provider_foreign_ambiguous_error_identity_and_frozen_forwarding(self):
        fixture = r'''
H={calls=0,writes=0};local marker={};H.marker=marker
local function Native(self,...)H.calls=H.calls+1;H.args={n=select('#',...),...};if H.throw then error(marker,0)end;return nil,false,marker,nil end
local function RO(t)return setmetatable({},{__index=t,__newindex=function()H.writes=H.writes+1;error('read-only SDK')end})end
Targets={RO({RequestPolicyChanges=Native}),RO({RequestPolicyChanges=Native})}
Players=RO({[0]=RO({GetCulture=function()return H.ambiguous and Targets[2]or Targets[1]end}),[1]=RO({GetCulture=function()return Targets[2]end})})
PlayerManager=RO({GetAliveIDs=function()return{0,1}end});Game=RO({GetCurrentGameTurn=function()return 140 end,GetLocalPlayer=function()return 0 end})
'''
        for VM in (L51, L53):
            lua = VM(); lua.execute(fixture)
            lua.execute('local Factory=(function()\n'+MODULE.read_text(encoding='utf-8')+'\nend)()\n'+PROVIDER)
            lua.execute('''
local s=P6CultureSites174;local t=Targets[2]
local function Pack(...)return{n=select('#',...),...}end
local a,b={},{};local fn=s.Method('native-culture-test','PLAYER',t,'RequestPolicyChanges')
local r=Pack(fn(a,b,nil));assert(r.n==4 and r[2]==false and r[3]==H.marker and r[4]==nil)
assert(H.args.n==3 and H.args[1]==a and H.args[2]==b and H.args[3]==nil and H.calls==1 and H.writes==0)
assert(s.rows[1].owner==1 and s.rows[1].localPlayer==0 and s.rows[1].metadataKnown)
H.ambiguous=true;fn(a,b);assert(H.calls==2 and s.metadataErrors==1 and not s.rows[2].metadataKnown)
H.ambiguous=false;H.throw=true;local ok,e=pcall(fn,a,b);assert(not ok and e==H.marker and H.calls==3 and not s.rows[3].returned)
H.throw=false;assert(s.Freeze());fn(a,b);assert(H.calls==4 and s.calls==3 and H.writes==0)
''')


if __name__ == '__main__':
    unittest.main()
