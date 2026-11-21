"""Guard result contracts; the stock typed consumer is modeled without game writes."""
from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as Lua51
from lupa.lua53 import LuaRuntime as Lua53

ROOT = Path(__file__).resolve().parents[1]


def guarded(runtime):
    lua = runtime(unpack_returned_tuples=True)
    lua.execute((ROOT / 'tests/lua/mock_guard.lua').read_text(encoding='utf-8'))
    lua.execute('rawset=nil;_G=nil;CityCommandTypes.MANAGE=23')
    for name in ('BaiqiConfig', 'BaiqiPolicy', 'BaiqiUIGuard'):
        lua.execute((ROOT / f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
    return lua


class CityCommandReturnContractTests(unittest.TestCase):
    def test_rejected_results_fit_nullable_table_consumer_and_remain_falsey(self):
        for runtime in (Lua51, Lua53):
            for command in (22, 23):
                with self.subTest(vm=runtime.__module__, command=command):
                    lua = guarded(runtime)
                    lua.globals().TestGuard.command = command
                    lua.execute('''
                      local function pack(...) return {n=select('#',...),...} end
                      local result=pack(CityManager.RequestCommand(TestCity(7),TestGuard.command,{}))
                      -- Stock PlotInfo declares this result as table. Nil is allowed;
                      -- the real engine probe is recorded separately from this VM test.
                      assert(result[1]==nil or type(result[1])=='table','stock nullable-table result contract')
                      assert(result.n==1 and result[1]==nil and not result[1])
                      assert(TestGuard.cityCalls==0)
                      assert(UnitManager.RequestCommand(TestUnit(1,7,101),99,{})==false)
                      assert(CityManager.RequestOperation(TestCity(7),99,{})==false)
                    ''')

    def test_allowed_commands_preserve_native_identity_arguments_and_full_returns(self):
        cases = [('LEADER_BAIQI', 7, 20, True, False, False),
                 ('LEADER_BAIQI', 7, 21, True, False, False),
                 ('LEADER_BAIQI', 8, 23, True, False, False),
                 ('LEADER_TRAJAN', 7, 23, True, False, False),
                 ('LEADER_BAIQI', 7, 23, False, False, False),
                 ('LEADER_BAIQI', 7, 23, True, True, False),
                 ('LEADER_BAIQI', 7, 23, True, False, True)]
        for runtime in (Lua51, Lua53):
            for leader, owner, command, human, multi, hotseat in cases:
                with self.subTest(vm=runtime.__module__, leader=leader, owner=owner,
                                  command=command, human=human, multi=multi, hotseat=hotseat):
                    lua = guarded(runtime)
                    w = lua.globals().TestGuard
                    w.leader, w.human, w.multi, w.hotseat = leader, human, multi, hotseat
                    w.expectedCity = lua.globals().TestCity(owner)
                    w.command = command
                    lua.execute('''
                      GameConfiguration.IsHotseat=function() return TestGuard.hotseat end
                      local native=getmetatable(CityManager).__index
                      local token={native_result=true}
                      native.RequestCommand=function(city,command,...)
                        assert(city==TestGuard.expectedCity and command==TestGuard.command)
                        assert(select('#',...)==3)
                        local a,b,c=...;assert(a==nil and b==false and c==nil)
                        TestGuard.cityCalls=TestGuard.cityCalls+1
                        return token,false,nil,'native_tail'
                      end
                      local function pack(...) return {n=select('#',...),...} end
                      local r=pack(CityManager.RequestCommand(TestGuard.expectedCity,TestGuard.command,nil,false,nil))
                      assert(r.n==4 and r[1]==token and r[2]==false and r[3]==nil and r[4]=='native_tail')
                      assert(TestGuard.cityCalls==1)
                    ''')

    def test_cached_request_rechecks_current_delegation_authority(self):
        for runtime in (Lua51, Lua53):
            with self.subTest(vm=runtime.__module__):
                lua = guarded(runtime)
                lua.execute('''
                  local request=CityManager.RequestCommand
                  local city=TestCity(7)
                  assert(request(city,23,{})==nil)
                  TestGuard.leader='LEADER_TRAJAN';assert(request(city,23,{})==true)
                  TestGuard.leader='LEADER_BAIQI';assert(request(city,23,{})==nil)
                  TestGuard.human=false;assert(request(city,23,{})==true)
                  TestGuard.human=true;assert(request(city,23,{})==nil)
                  TestGuard.multi=true;assert(request(city,23,{})==true)
                  TestGuard.multi=false;assert(request(city,23,{})==nil)
                  assert(TestGuard.cityCalls==3)
                ''')


if __name__ == '__main__':
    unittest.main()
