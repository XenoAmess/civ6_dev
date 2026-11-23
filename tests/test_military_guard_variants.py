"""Military ranks and escort counts must never change manual-control routing."""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53


ROOT = Path(__file__).resolve().parents[1]
MILITARY = (
    'UNIT_WARRIOR', 'UNIT_SCOUT', 'UNIT_ARCHER', 'UNIT_BATTERING_RAM',
    'UNIT_GALLEY', 'UNIT_FIGHTER', 'UNIT_MILITARY_ENGINEER',
    'UNIT_APOSTLE', 'UNIT_INQUISITOR', 'UNIT_GURU',
    'UNIT_GREAT_GENERAL', 'UNIT_GREAT_ADMIRAL', 'UNIT_UNKNOWN_NONWHITE',
)
FORMATIONS = ((-1, 1), (0, 1), (1, 1), (2, 1), (0, 2))


def runtime(vm):
    lua = vm(unpack_returned_tuples=True)
    lua.execute((ROOT / 'tests/lua/mock_guard.lua').read_text(encoding='utf-8'))
    lua.execute('rawset=nil')
    for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiUIGuard'):
        lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
    return lua


class MilitaryGuardVariants(unittest.TestCase):
    def test_nonwhite_policy_rejects_before_reading_escort_or_moves(self):
        for vm in (Lua51, Lua53):
            lua = runtime(vm)
            check = lua.eval("""function(kind,rank)
              local ctx={isBaiqi=true,enabled=true,activeTurn=true,player=7,localPlayer=7}
              local snapshot=setmetatable({owner=7,type=kind,militaryFormation=rank},
                {__index=function(_,key)error('Nonwhite policy read '..key)end})
              local allowed,reason=BaiqiPolicy.CanCivilian(ctx,snapshot)
              assert(allowed==false and reason=='not_whitelisted')
              for _,op in ipairs({'MOVE_TO','SKIP_TURN','FOUND_CITY','SPREAD_RELIGION',
                'ACTIVATE_GREAT_PERSON','REBASE','ENTER_FORMATION'})do
                assert(BaiqiPolicy.ActionAllowed(kind,op)==false)
              end
            end""")
            for kind in MILITARY:
                for rank in (-1, 0, 1, 2):
                    with self.subTest(vm=vm.__module__, kind=kind, rank=rank):
                        check(kind, rank)

    def test_all_manual_sinks_preserve_native_identity_arguments_and_rejection(self):
        for vm in (Lua51, Lua53):
            lua = runtime(vm)
            check = lua.eval("""function(kind,rank,escort)
              GameInfo.Units[100]={UnitType=kind,Combat=0,FormationClass='FORMATION_CLASS_CIVILIAN'}
              local unit=TestUnit(100,7,90001)
              local reads=0
              unit.GetMilitaryFormation=function()reads=reads+1;return rank end
              unit.GetFormationUnitCount=function()reads=reads+1;return escort end
              local params,opaque={},{}
              local total=0
              local function pack(...)return {n=select('#',...),...}end
              for _,name in ipairs({'CanStartOperation','RequestOperation','CanStartCommand','RequestCommand'})do
                local count=0
                TestGuard.nativeUnit[name]=function(actual,code,...)
                  assert(actual==unit and code==55 and select('#',...)==4)
                  local p,a,b,c=...;assert(p==params and a==nil and b==false and c==nil)
                  count=count+1;total=total+1
                  return nil,false,opaque,nil
                end
                local result=pack(UnitManager[name](unit,55,params,nil,false,nil))
                assert(count==1 and result.n==4 and result[1]==nil and result[2]==false
                  and result[3]==opaque and result[4]==nil)
              end
              assert(total==4 and reads==0 and BaiqiUIGuard.Civilian(unit)==false)
            end""")
            for kind in MILITARY:
                for rank, escort in FORMATIONS:
                    with self.subTest(vm=vm.__module__, kind=kind, rank=rank, escort=escort):
                        check(kind, rank, escort)

    def test_type_changes_recheck_cached_manual_sink_without_unlocking_civilians(self):
        for vm in (Lua51, Lua53):
            lua = runtime(vm)
            lua.execute("""
              local unit=TestUnit(0,7,90002)
              local current=0;unit.GetUnitType=function()return current end
              local request=UnitManager.RequestOperation
              assert(request(unit,55,{})==true and TestGuard.unitCalls==1)
              current=1 -- Existing builder definition, no second proxy installation.
              assert(request(unit,55,{})==false and TestGuard.unitCalls==1)
              current=0
              assert(request(unit,55,{})==true and TestGuard.unitCalls==2)
              for _,kind in ipairs({1,13})do
                local civilian=TestUnit(kind,7,90100+kind)
                for _,name in ipairs({'CanStartOperation','RequestOperation','CanStartCommand','RequestCommand'})do
                  assert(UnitManager[name](civilian,55,{})==false)
                end
              end
              assert(TestGuard.unitCalls==2)
              local ctx={isBaiqi=true,enabled=true,activeTurn=true,player=7,localPlayer=7}
              for _,kind in ipairs({'UNIT_BUILDER','UNIT_MISSIONARY'})do
                assert(BaiqiPolicy.CanCivilian(ctx,{owner=7,type=kind,formationCount=1,moves=2})==true)
                local allowed,why=BaiqiPolicy.CanCivilian(ctx,{owner=7,type=kind,formationCount=2,moves=2})
                assert(allowed==false and why=='formation_or_unknown')
              end
            """)

    def test_native_error_object_is_preserved_for_nonwhite_zero_combat_unit(self):
        for vm in (Lua51, Lua53):
            lua = runtime(vm)
            lua.execute("""
              GameInfo.Units[100]={UnitType='UNIT_MILITARY_ENGINEER',Combat=0}
              local unit=TestUnit(100,7,90003);local opaque={};local count=0
              TestGuard.nativeUnit.RequestOperation=function(actual)
                assert(actual==unit);count=count+1;error(opaque,0)
              end
              local ok,why=pcall(UnitManager.RequestOperation,unit,55,{})
              assert(ok==false and why==opaque and count==1)
            """)


if __name__ == '__main__':
    unittest.main()
