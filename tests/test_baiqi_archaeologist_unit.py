from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class ArchaeologistUnitTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.module = self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiArchaeologistUnit.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
          F={id=5046313,owner=0,kind='UNIT_ARCHAEOLOGIST',x=11,y=7,moves=4,formation=1}
          Unit={GetID=function() return F.id end,GetOwner=function() return F.owner end,
            GetType=function() return 19 end,GetX=function() return F.x end,GetY=function() return F.y end,
            GetMovesRemaining=function() return F.moves end,
            GetFormationUnitCount=function() return F.formation end}
          UnitsPort={FindID=function(self,id) assert(self==UnitsPort and id==5046313);return Unit end}
          PlayerPort={GetUnits=function(self) assert(self==PlayerPort);return UnitsPort end,
            SetProperty=function() error('forbidden write') end}
          GameInfo={Units={[19]=setmetatable({},{__index=function(_,key)
            if key=='UnitType' then return F.kind end
          end})}}
        ''')
        self.f = self.lua.globals().F

    def read(self, player=None, pid=0, unit_id=5046313):
        return self.module.Read(player if player is not None else self.lua.globals().PlayerPort, pid, unit_id)

    def test_exact_plain_snapshot_and_export(self):
        result = self.read()
        self.assertEqual(dict(result), {'unitID':5046313, 'unitType':'UNIT_ARCHAEOLOGIST',
                                       'x':11, 'y':7, 'moves':4, 'formation':1})
        self.assertIsNone(self.lua.eval('getmetatable')(result))
        self.assertTrue(self.lua.eval('rawequal')(self.module, self.lua.globals().BaiqiArchaeologistUnit))

    def test_zero_fractional_moves_and_formation_are_observations(self):
        for moves in (0, 0.5):
            self.f.moves, self.f.formation = moves, 2
            self.assertEqual((self.read().moves, self.read().formation), (moves, 2))

    def test_bad_owner_and_unit_id_inputs(self):
        for value in (True, -1, 0.5, 2147483648, float('nan'), float('inf'), '0'):
            with self.subTest(value=value):
                self.assertIsNone(self.read(pid=value))
                self.assertIsNone(self.read(unit_id=value))

    def test_wrong_full_identity_owner_and_type(self):
        for field, value in (('id',1769529), ('owner',1), ('kind','UNIT_NATURALIST')):
            with self.subTest(field=field):
                self.setUp()
                self.f[field] = value
                self.assertIsNone(self.read())

    def test_coordinate_bounds_and_types(self):
        for key in ('x','y'):
            for value in (-1, 0.5, 2147483648, True, float('nan'), float('inf'), '11'):
                with self.subTest(key=key, value=value):
                    self.setUp()
                    self.f[key] = value
                    self.assertIsNone(self.read())

    def test_moves_and_formation_bounds(self):
        for key, values in (('moves',(-1, True, float('inf'), float('nan'), '4')),
                            ('formation',(0, 65, 1.5, True, float('inf'), '1'))):
            for value in values:
                with self.subTest(key=key, value=value):
                    self.setUp()
                    self.f[key] = value
                    self.assertIsNone(self.read())

    def test_missing_native_members_and_row(self):
        for setup in ('PlayerPort.GetUnits=nil', 'UnitsPort.FindID=nil', 'Unit.GetType=nil',
                      'Unit.GetMovesRemaining=nil', 'Unit.GetFormationUnitCount=nil', 'GameInfo.Units[19]=nil'):
            with self.subTest(setup=setup):
                self.setUp()
                self.lua.execute(setup)
                self.assertIsNone(self.read())

    def test_throwing_getter_and_metatable_provider_fail_closed(self):
        for setup in ("Unit.GetX=function() error('getter') end",
                      "PlayerPort=setmetatable({},{__index=function() error('provider') end})",
                      "GameInfo.Units=setmetatable({},{__index=function() error('row') end})"):
            with self.subTest(setup=setup):
                self.setUp()
                self.lua.execute(setup)
                self.assertIsNone(self.read())
        self.assertIsNone(self.read(player='primitive'))

    def test_identity_changes_after_observations_are_rejected(self):
        for key,value in (('owner',1),('id',1769529)):
            with self.subTest(key=key):
                self.setUp()
                self.lua.execute(f'Unit.GetFormationUnitCount=function() F.{key}={value};return 1 end')
                self.assertIsNone(self.read())

    def test_core_only_contract_needs_no_ui_methods_or_writes(self):
        self.lua.execute('''
          assert(Unit.GetUnitType==nil and Unit.GetArchaeology==nil and Unit.GetArchaeologyHomeCity==nil)
          Unit.SetProperty=function() error('forbidden write') end
          UnitManager=setmetatable({},{__index=function() error('forbidden native action') end})
        ''')
        self.assertEqual(self.read().unitID, 5046313)


if __name__ == '__main__':
    unittest.main()
