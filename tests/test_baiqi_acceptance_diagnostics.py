"""Portable Lua 5.1 checks for the adopted acceptance diagnostics (no game input)."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]

QUEUE_FIXTURE = r'''
w={size=1,hash=-99,progress=7.5,cost=40,turns=3,mod=0,calls={},owner=0}
function hit(k)w.calls[k]=(w.calls[k]or 0)+1 end
q={}
function q:GetSize()assert(self==q);hit('size');return w.size end
function q:GetCurrentProductionTypeHash()assert(self==q);hit('hash');return w.hash end
function q:GetCurrentProductionTypeModifier()assert(self==q);hit('mod');return w.mod end
function q:GetTurnsLeft(t,m)assert(self==q);hit('turns');w.turnType=t;w.turnMod=m;return w.turns end
for _,v in ipairs({'Building','District','Unit','Project'})do
 local prefix=v
 q['Get'..prefix..'Progress']=function(self,i)assert(self==q and i==5);hit('progress');return w.progress end
 q['Get'..prefix..'Cost']=function(self,i)assert(self==q and i==5);hit(prefix..'cost');return w.cost end
end
q.GetUnitCorpsCost=function(self,i)assert(self==q and i==5);hit('corps');return 80 end
q.GetUnitArmyCost=function(self,i)assert(self==q and i==5);hit('army');return 120 end
city={GetOwner=function(self)hit('owner');return w.owner end,GetBuildQueue=function(self)hit('queue');return q end}
E={GameInfo={Buildings={[-99]={Hash=-99,Index=5,BuildingType='BUILDING_MONUMENT'}},Districts={},Units={},Projects={}},MilitaryFormationTypes={STANDARD_FORMATION=0,CORPS_FORMATION=1,ARMY_FORMATION=2}}
function choose(kind,field)
 E.GameInfo.Buildings[-99]=nil
 E.GameInfo[kind][-99]={Hash=-99,Index=5,[field]='TYPE_FIXTURE'}
end
'''
QUEUE_CASES = {'current_building_cost_once': "local r=M.Queue(E,city);assert(r.status=='KNOWN'and r.cost==40 and "
                               "r.progress==7.5 and r.type=='BUILDING_MONUMENT'and "
                               'w.calls.owner==1 and w.calls.queue==1 and w.calls.progress==1 and '
                               'w.calls.Buildingcost==1 and w.calls.turns==1)',
 'native_userdata_city_and_queue': 'local c=newproxy(true);getmetatable(c).__index=city;local '
                                   'z=newproxy(true);getmetatable(z).__index=q;city.GetBuildQueue=function()return '
                                   'z end;q.GetSize=function()return w.size '
                                   'end;q.GetCurrentProductionTypeHash=function()return w.hash '
                                   'end;q.GetBuildingProgress=function()return w.progress '
                                   'end;q.GetBuildingCost=function()return w.cost '
                                   'end;q.GetTurnsLeft=function()return w.turns end;local '
                                   "r=M.Queue(E,c);assert(r.status=='KNOWN'and r.cost==40)",
 'district_actual_getters': "choose('Districts','DistrictType');local "
                            "r=M.Queue(E,city);assert(r.status=='KNOWN'and r.kind=='DISTRICT'and "
                            'w.calls.Districtcost==1 and w.calls.Buildingcost==nil)',
 'project_actual_getters': "choose('Projects','ProjectType');local "
                           "r=M.Queue(E,city);assert(r.status=='KNOWN'and r.kind=='PROJECT'and "
                           'w.calls.Projectcost==1)',
 'standard_unit_cost_modifier': "choose('Units','UnitType');local "
                                "r=M.Queue(E,city);assert(r.status=='KNOWN'and r.cost==40 and "
                                'w.calls.Unitcost==1 and w.calls.corps==nil and w.turnMod==0)',
 'corps_cost_not_standard': "choose('Units','UnitType');w.mod=1;local "
                            "r=M.Queue(E,city);assert(r.status=='KNOWN'and r.cost==80 and "
                            'w.calls.corps==1 and w.calls.Unitcost==nil and w.turnMod==1)',
 'army_cost_not_standard': "choose('Units','UnitType');w.mod=2;local "
                           "r=M.Queue(E,city);assert(r.status=='KNOWN'and r.cost==120 and "
                           'w.calls.army==1 and w.calls.Unitcost==nil)',
 'foreign_owner_no_queue_read': "w.owner=1;local r=M.Queue(E,city);assert(r.status=='UNKNOWN'and "
                                'w.calls.queue==nil)',
 'empty_not_unknown': "w.size=0;w.hash=0;local r=M.Queue(E,city);assert(r.status=='EMPTY'and "
                      "r.kind=='EMPTY'and w.calls.progress==nil)",
 'mismatched_empty_unknown': "w.size=0;local r=M.Queue(E,city);assert(r.status=='UNKNOWN')",
 'metadata_index_without_database_call': "setmetatable(E.GameInfo.Buildings,{__call=function()error('must_not_call_database')end});local "
                                         "r=M.Queue(E,city);assert(r.status=='KNOWN')",
 'ambiguous_hash_refused': "E.GameInfo.Districts[-99]={Hash=-99,Index=5,DistrictType='DISTRICT_CAMPUS'};assert(M.Queue(E,city).status=='UNKNOWN')",
 'wrong_metadata_hash_refused': "E.GameInfo.Buildings[-99].Hash=99;assert(M.Queue(E,city).status=='UNKNOWN')",
 'metadata_exception_contained': "E.GameInfo=setmetatable({},{__index=function()error('fixture')end});local "
                                 "ok,r=pcall(M.Queue,E,city);assert(ok and r.status=='UNKNOWN')",
 'finite_numeric_required': "w.cost=math.huge;assert(M.Queue(E,city).status=='UNKNOWN')",
 'function_return_not_called': "w.cost=function()error('never_call')end;assert(M.Queue(E,city).status=='UNKNOWN')",
 'completed_head_preserved': 'w.progress=41;w.cost=40;local '
                             "r=M.Queue(E,city);assert(r.status=='KNOWN'and r.progress==41 and "
                             'r.cost==40 and r.size==1)',
 'unknown_formation_refused': "choose('Units','UnitType');w.mod=9;assert(M.Queue(E,city).status=='UNKNOWN')",
 'missing_type_refused': "E.GameInfo.Buildings[-99].BuildingType=nil;assert(M.Queue(E,city).status=='UNKNOWN')"}
DISTRICT_FIXTURE = r'''
w={calls=0,mapreads=0,impreads=0,imp=9,visible=true};c={GetOwner=function()return 0 end,GetID=function()return 65536 end}
p={GetX=function()return 55 end,GetY=function()return 36 end,GetOwner=function()return 0 end,GetIndex=function()return 2719 end,GetImprovementType=function()w.impreads=w.impreads+1;return w.imp end,GetDistrictType=function()return -1 end}
params={[1]=-99,[2]=55,[3]=36};tail=function()w.tailCalled=true end
function pack(...)return {n=select('#',...),...}end
local original=function(...)w.calls=w.calls+1;w.args=pack(...);w.imp=-1;return false,nil,tail,nil end
E={CityManager={RequestOperation=original},CityOperationTypes={BUILD=7,PARAM_DISTRICT_TYPE=1,PARAM_X=2,PARAM_Y=3},guard=function()return true end,GameInfo={Districts={[-99]={Hash=-99,DistrictType='DISTRICT_HOLY_SITE'}},Improvements={[9]={ImprovementType='IMPROVEMENT_FARM'}}},PlayersVisibility={[0]={IsVisible=function()return w.visible end,IsRevealed=function()return true end}},Map={GetPlot=function()w.mapreads=w.mapreads+1;return p end},Game={GetCurrentGameTurn=function()return 65 end}}
orig=original
'''
DISTRICT_CASES = {'snapshot_before_original_mutation': 'E.CityManager.RequestOperation(c,7,params);local '
                                      'r=h.records[1];assert(w.calls==1 and r.improvementIndex==9 '
                                      "and r.improvementType=='IMPROVEMENT_FARM'and r.hash==-99 "
                                      'and r.plotIndex==2719 and w.imp==-1)',
 'returns_nil_holes_and_function_untouched': 'local '
                                             'r=pack(E.CityManager.RequestOperation(c,7,params));assert(r.n==4 '
                                             'and r[1]==false and r[2]==nil and r[3]==tail and '
                                             'r[4]==nil and not w.tailCalled)',
 'arguments_preserved_identity_and_tail_nil': "E.CityManager.RequestOperation(c,7,params,'extra',nil,42);assert(w.args.n==6 "
                                              'and w.args[1]==c and w.args[3]==params and '
                                              "w.args[4]=='extra'and w.args[5]==nil and "
                                              'w.args[6]==42 and params[1]==-99 and params[2]==55)',
 'other_request_no_map_read': 'E.CityManager.RequestOperation(c,7,{});assert(w.calls==1 and '
                              '#h.records==0 and w.mapreads==0)',
 'repair_no_plot_read': 'E.CityManager.RequestOperation(c,7,{[1]=-99});assert(w.calls==1 and '
                        'h.noPlacement==1 and w.mapreads==0 and #h.records==0)',
 'foreign_city_before_plot_reads': 'c.GetOwner=function()return 1 '
                                   'end;E.CityManager.RequestOperation(c,7,params);assert(w.calls==1 '
                                   'and w.mapreads==0 and #h.records==0)',
 'hidden_never_queries_plot': 'w.visible=false;E.CityManager.RequestOperation(c,7,params);assert(w.calls==1 '
                              'and w.mapreads==0 and #h.records==0 and h.unknown==1)',
 'foreign_plot_before_improvement_read': 'p.GetOwner=function()return 1 '
                                         'end;E.CityManager.RequestOperation(c,7,params);assert(w.calls==1 '
                                         'and w.impreads==0 and h.unknown==1)',
 'unknown_improvement_never_NONE': 'E.GameInfo.Improvements[9]=nil;E.CityManager.RequestOperation(c,7,params);assert(w.calls==1 '
                                   'and h.unknown==1 and #h.records==0)',
 'invalid_xy_before_plot_read': "params[2]='55';E.CityManager.RequestOperation(c,7,params);assert(w.calls==1 "
                                'and w.mapreads==0 and h.unknown==1)',
 'metadata_exception_does_not_block_order': "p.GetImprovementType=function()error('fixture')end;E.CityManager.RequestOperation(c,7,params);assert(w.calls==1 "
                                            'and h.errors==1 and #h.records==0)',
 'guard_exception_does_not_block_order': "E.guard=function()error('fixture')end;E.CityManager.RequestOperation(c,7,params);assert(w.calls==1 "
                                         'and h.errors==1 and w.mapreads==0)',
 'bounded16': 'for i=1,17 do E.CityManager.RequestOperation(c,7,params)end;assert(w.calls==17 and '
              '#h.records==16 and h.drops==1)',
 'restore_then_old_alias_forwards_only': 'local '
                                         'alias=E.CityManager.RequestOperation;assert(h.Restore()and '
                                         'not h.active and '
                                         'E.CityManager.RequestOperation==orig);alias(c,7,params);assert(w.calls==1 '
                                         'and #h.records==0 and w.mapreads==0)',
 'foreign_wrapper_not_overwritten': 'local '
                                    'f=function()end;E.CityManager.RequestOperation=f;assert(not '
                                    'h.Restore()and h.active and '
                                    'E.CityManager.RequestOperation==f)',
 'false_guard_no_reads': 'E.guard=function()return false '
                         'end;E.CityManager.RequestOperation(c,7,params);assert(w.calls==1 and '
                         'w.mapreads==0 and #h.records==0)',
 'noncapital_dynamic_city_id': 'c.GetID=function()return 131073 '
                               'end;E.CityManager.RequestOperation(c,7,params);assert(w.calls==1 '
                               'and #h.records==1 and h.records[1].city==131073 and h.errors==0)',
 'third_and_fourth_city_ids': 'for _,id in ipairs({196610,262147})do c.GetID=function()return id '
                              'end;E.CityManager.RequestOperation(c,7,params)end;assert(w.calls==2 '
                              'and h.records[1].city==196610 and h.records[2].city==262147)',
 'foreign_city_id_never_called': 'c.GetOwner=function()return 1 '
                                 "end;c.GetID=function()error('must_not_read')end;E.CityManager.RequestOperation(c,7,params);assert(w.calls==1 "
                                 'and w.mapreads==0 and h.errors==0 and h.unknown==0)',
 'nil_city_unknown_original_once': 'E.CityManager.RequestOperation(nil,7,params);assert(w.calls==1 '
                                   'and w.mapreads==0 and h.unknown==1)',
 'owner_getter_error_is_counted': "c.GetOwner=function()error('owner_getter_failed')end;E.CityManager.RequestOperation(c,7,params);assert(w.calls==1 "
                                  'and w.mapreads==0 and h.errors==1)',
 'id_getter_error_unknown': "c.GetID=function()error('city_id_unavailable')end;E.CityManager.RequestOperation(c,7,params);assert(w.calls==1 "
                            'and w.mapreads==0 and h.unknown==1)',
 'invalid_id_bounds_no_plot': "for _,id in ipairs({-1,1.5,'131073',true,2147483648,0/0})do "
                              'c.GetID=function()return id '
                              'end;E.CityManager.RequestOperation(c,7,params)end;assert(w.calls==6 '
                              'and w.mapreads==0 and #h.records==0 and h.unknown==6)',
 'maximum_valid_id_preserved': 'c.GetID=function()return 2147483647 '
                               'end;E.CityManager.RequestOperation(c,7,params);assert(w.calls==1 '
                               'and h.records[1].city==2147483647)',
 'missing_city_method_unknown': 'c.GetID=nil;E.CityManager.RequestOperation(c,7,params);assert(w.calls==1 '
                                'and w.mapreads==0 and h.unknown==1)'}


class AcceptanceDiagnosticTests(unittest.TestCase):
    def test_queue_metadata_boundaries(self):
        source = (ROOT / 'tools/lua/diagnostic_production_snapshot.lua').read_text(encoding='utf-8')
        for name, code in QUEUE_CASES.items():
            with self.subTest(case=name):
                lua = LuaRuntime()
                lua.execute(QUEUE_FIXTURE)
                lua.globals().M = lua.execute(source)
                lua.execute('rawget=nil')
                lua.execute(code)

    def test_district_before_witness_and_exact_forwarding(self):
        source = (ROOT / 'tools/lua/diagnostic_district_placement.lua').read_text(encoding='utf-8')
        for name, code in DISTRICT_CASES.items():
            with self.subTest(case=name):
                lua = LuaRuntime()
                lua.execute(DISTRICT_FIXTURE)
                lua.globals().M = lua.execute(source)
                lua.execute('rawget=nil;h=assert(M.Install(E))')
                lua.execute(code)

    def test_original_error_propagates_exactly_once(self):
        lua = LuaRuntime()
        lua.execute(DISTRICT_FIXTURE)
        lua.execute("E.CityManager.RequestOperation=function()w.calls=w.calls+1;error('original_failure',0)end")
        lua.globals().M = lua.execute((ROOT / 'tools/lua/diagnostic_district_placement.lua').read_text(encoding='utf-8'))
        lua.execute("h=M.Install(E);local ok,err=pcall(E.CityManager.RequestOperation,c,7,params);assert(not ok and err=='original_failure'and w.calls==1)")


if __name__ == '__main__':
    unittest.main()
