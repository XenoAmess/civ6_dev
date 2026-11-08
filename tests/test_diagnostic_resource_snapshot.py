"""Own GS resource snapshots preserve raw values and distinguish unknown from zero."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = r'''
w={reads=0,gets=0,rows={{Index=2,ResourceType='RESOURCE_IRON',ResourceClassType='RESOURCECLASS_STRATEGIC'}}}
r={}
for _,k in ipairs({'GetResourceAmount','GetResourceStockpileCap','GetReservedResourceAmount',
 'GetResourceAccumulationPerTurn','GetResourceImportPerTurn','GetBonusResourcePerTurn',
 'GetUnitResourceDemandPerTurn','GetPowerResourceDemandPerTurn'})do
 local name=k
 r[name]=function(self,t)assert(self==r and t=='RESOURCE_IRON');w.gets=w.gets+1;return 0 end
end
p={GetResources=function(self)assert(self==p);w.reads=w.reads+1;return r end}
E={Game={GetLocalPlayer=function()return 0 end},Players={[0]=p},GameInfo={Resources=function()
 local i=0;return function()i=i+1;return w.rows[i]end end}}
'''
CASES = {
    'zero_is_known_all_eight_getters_once': "local a=M.Read(E);assert(a.status=='KNOWN'and #a.rows==1 and a.rows[1].stockpile==0 and a.rows[1].type=='RESOURCE_IRON'and w.gets==8 and w.reads==1)",
    'foreign_player_before_any_owned_reads': "E.Game.GetLocalPlayer=function()return 1 end;E.Players=setmetatable({},{__index=function()error('must_not_read')end});assert(M.Read(E).status=='UNKNOWN'and w.reads==0)",
    'missing_environment_contained': "local ok,a=pcall(M.Read,nil);assert(ok and a.status=='UNKNOWN')",
    'local_getter_exception_contained': "E.Game.GetLocalPlayer=function()error('fixture')end;local ok,a=pcall(M.Read,E);assert(ok and a.status=='UNKNOWN'and w.reads==0)",
    'resource_getter_exception_contained': "r.GetResourceAmount=function()error('fixture')end;local ok,a=pcall(M.Read,E);assert(ok and a.status=='UNKNOWN'and a.rows==nil)",
    'nil_is_unknown_never_zero': "r.GetResourceAmount=function()return nil end;assert(M.Read(E).status=='UNKNOWN')",
    'infinity_is_unknown': "r.GetResourceAmount=function()return math.huge end;assert(M.Read(E).status=='UNKNOWN')",
    'nan_is_unknown': "r.GetResourceAmount=function()return 0/0 end;assert(M.Read(E).status=='UNKNOWN')",
    'negative_is_unknown': "r.GetUnitResourceDemandPerTurn=function()return -1 end;assert(M.Read(E).status=='UNKNOWN')",
    'function_return_not_called': "r.GetResourceAmount=function()return function()w.called=true end end;assert(M.Read(E).status=='UNKNOWN'and not w.called)",
    'over_cap_and_fraction_not_clamped': "r.GetResourceAmount=function()return 41.5 end;r.GetResourceStockpileCap=function()return 40 end;local a=M.Read(E);assert(a.status=='KNOWN'and a.rows[1].stockpile==41.5 and a.rows[1].cap==40)",
    'duplicate_index_rejected': "w.rows[2]={Index=2,ResourceType='RESOURCE_HORSES',ResourceClassType='RESOURCECLASS_STRATEGIC'};local a=M.Read(E);assert(a.status=='UNKNOWN'and a.rows==nil)",
    'duplicate_type_rejected': "w.rows[2]={Index=3,ResourceType='RESOURCE_IRON',ResourceClassType='RESOURCECLASS_STRATEGIC'};assert(M.Read(E).status=='UNKNOWN')",
    'invalid_index_bounds': "w.rows[1].Index=2147483648;assert(M.Read(E).status=='UNKNOWN'and w.gets==0)",
    'fractional_index_rejected': "w.rows[1].Index=2.5;assert(M.Read(E).status=='UNKNOWN'and w.gets==0)",
    'missing_type_rejected': "w.rows[1].ResourceType=nil;assert(M.Read(E).status=='UNKNOWN'and w.gets==0)",
    'nonstrategic_metadata_not_read': "w.rows[2]=setmetatable({ResourceClassType='RESOURCECLASS_BONUS'},{__index=function()error('no_need')end});assert(M.Read(E).status=='KNOWN'and w.gets==8)",
    'empty_strategic_is_unknown': "w.rows={};assert(M.Read(E).status=='UNKNOWN')",
    'bounded_iterator_not_partial_known': "E.GameInfo.Resources=function()return function()return {ResourceClassType='RESOURCECLASS_BONUS'}end end;local a=M.Read(E);assert(a.status=='UNKNOWN'and a.rows==nil and w.gets==0)",
    'userdata_player_resources_and_catalog': "local oldp,oldr=p,r;local pr=newproxy(true);getmetatable(pr).__index=oldp;p=pr;local rr=newproxy(true);getmetatable(rr).__index=oldr;r=rr;E.Players[0]=p;local cat=newproxy(true);getmetatable(cat).__index=E.GameInfo;E.GameInfo=cat;assert(M.Read(E).status=='KNOWN'and w.gets==8)",
}


class ResourceSnapshotTests(unittest.TestCase):
    def test_resource_boundaries(self):
        source = (ROOT / 'tools/lua/diagnostic_resource_snapshot.lua').read_text(encoding='utf-8')
        for name, code in CASES.items():
            with self.subTest(case=name):
                lua = LuaRuntime()
                lua.execute(FIXTURE)
                lua.globals().M = lua.execute(source)
                lua.execute('rawget=nil')
                lua.execute(code)


if __name__ == '__main__':
    unittest.main()
