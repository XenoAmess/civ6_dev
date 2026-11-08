from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = r'''
function Op(n,stage)
 local v={token='missionary-purchase:0:'..n,sequence=n,cityID=65536,unitType='UNIT_MISSIONARY',
 unitHash=-199,religionIndex=4,x=16,y=14,cost=75,faithBefore=175,reserve=100,turn=119,
 stage=stage or'ARMED',baselineUnitIDs={2,5}}
 if stage=='OBSERVED'then v.newUnitID=9;v.faithAfter=100 end
 return v
end
S={version=1,owner=0,serial=1,operations={['1']=Op(1)}}
'''


class MissionaryPurchaseJournalTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.j = self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiMissionaryPurchaseJournal.lua').read_text(encoding='utf-8'))
        self.lua.globals().J=self.j
        self.lua.execute(FIXTURE+'\nGame=nil;Players=nil;rawget=nil')
        self.s=self.lua.globals().S

    def test_zero_owner_helpers_and_new(self):
        self.assertEqual(self.j.Token(0,1),'missionary-purchase:0:1')
        self.assertEqual(self.j.Key(1),'1')
        self.assertTrue(self.j.Validate(self.j.New(0),0))
        for v in [True,-1,0.5,float('nan'),2147483648]:
            self.assertIsNone(self.j.New(v));self.assertFalse(self.j.Integer(v,2147483647))

    def test_armed_and_observed_are_distinct(self):
        self.assertTrue(self.j.Validate(self.s,0))
        self.lua.execute("S.operations['1']=Op(1,'OBSERVED')")
        self.assertTrue(self.j.Validate(self.s,0))
        for code in ["S.operations['1'].newUnitID=2", "S.operations['1'].faithAfter=101",
                     "S.operations['1'].faithAfter=nil"]:
            with self.subTest(code=code):
                self.setUp();self.lua.execute("S.operations['1']=Op(1,'OBSERVED');"+code)
                self.assertFalse(self.j.Validate(self.s,0))

    def test_unknown_fields_old_types_tokens_and_tampered_economy_rejected(self):
        for code in ["S.extra=true", "S.operations['1'].extra=true",
                     "S.operations['1'].unitType='UNIT_NATURALIST'", "S.operations['1'].token='purchase:0:1'",
                     "S.operations['1'].religionIndex=-1", "S.operations['1'].religionIndex=2147483648",
                     "S.operations['1'].cost=76", "S.operations['1'].cost=math.huge",
                     "S.operations['1'].newUnitID=9", "S.operations['1'].faithAfter=100",
                     "S.operations['1'].stage='OPEN'", "S.operations['1'].token='missionary-purchase:0:01'"]:
            with self.subTest(code=code):
                self.setUp();self.lua.execute(code)
                self.assertFalse(self.j.Validate(self.s,0));self.assertIsNone(self.j.Clone(self.s,0))

    def test_dense_sorted_unique_baselines(self):
        for value in ['{[1]=2,[3]=5}', "{[1]=2,extra=5}", '{5,2}', '{2,2}', '{true}',
                      '{[0]=1}', '{-1}', '{2147483648}']:
            with self.subTest(value=value):
                self.setUp();self.lua.execute("S.operations['1'].baselineUnitIDs="+value)
                self.assertFalse(self.j.Validate(self.s,0))
        self.setUp();self.lua.execute("S.operations['1'].baselineUnitIDs={}")
        self.assertTrue(self.j.Validate(self.s,0))

    def test_plain_tables_and_canonical_operation_keys(self):
        for code in ["setmetatable(S,{__index=function()error('must_not_run')end})",
                     "setmetatable(S.operations,{})", "setmetatable(S.operations['1'].baselineUnitIDs,{})",
                     "S.operations['01']=S.operations['1'];S.operations['1']=nil",
                     "S.operations[1]=S.operations['1'];S.operations['1']=nil",
                     "S.operations['1'].sequence=0"]:
            with self.subTest(code=code):
                self.setUp();self.lua.execute(code);self.assertFalse(self.j.Validate(self.s,0))

    def test_limits_and_multiple_unresolved(self):
        self.lua.execute("S.serial=2;S.operations['2']=Op(2)")
        self.assertFalse(self.j.Validate(self.s,0))
        self.setUp();self.lua.execute("S.serial=256;for i=1,256 do S.operations[tostring(i)]=Op(i,'OBSERVED')end")
        self.assertTrue(self.j.Validate(self.s,0))
        self.lua.execute("S.serial=257;S.operations['257']=Op(257,'OBSERVED')")
        self.assertFalse(self.j.Validate(self.s,0))
        self.setUp();self.lua.execute("for i=1,257 do S.operations['1'].baselineUnitIDs[i]=i end")
        self.assertFalse(self.j.Validate(self.s,0))

    def test_clone_is_deep_and_equality_is_symmetric(self):
        self.lua.execute("C=J.Clone(S,0);assert(C~=S and C.operations~=S.operations and C.operations['1'].baselineUnitIDs~=S.operations['1'].baselineUnitIDs)")
        c=self.lua.globals().C
        self.assertTrue(self.j.Equal(self.s,c,0))
        self.lua.execute("C.operations['1'].baselineUnitIDs[2]=6")
        self.assertEqual(self.s.operations['1'].baselineUnitIDs[2],5)
        self.assertFalse(self.j.Equal(self.s,c,0));self.assertFalse(self.j.Equal(c,self.s,0))
        self.setUp();self.lua.execute("C=J.Clone(S,0);C.serial=2;C.operations['2']=Op(2,'OBSERVED')")
        c=self.lua.globals().C
        self.assertFalse(self.j.Equal(self.s,c,0));self.assertFalse(self.j.Equal(c,self.s,0))

    def test_validation_never_repairs_or_expires_unresolved(self):
        self.lua.execute("S.operations['1'].turn=1;C=J.Clone(S,0);assert(J.Validate(S,0)and J.Equal(S,C,0))")
        self.assertEqual(self.s.operations['1'].stage,'ARMED')
        self.assertFalse(self.j.Validate(self.s,1))
        self.assertFalse(self.j.Equal(self.s,None,0))


if __name__ == '__main__':
    unittest.main()
