from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]

FIXTURE = r'''
F={id=65536,owner=0,x=16,y=14,hash=-199,yieldIndex=5,formation=0,op=77,
 uk=11,yk=12,fk=13,cost=75,faith=175,created=4,majority=4,must=true,purchaseYield='YIELD_FAITH',
 unitType='UNIT_MISSIONARY',qualifies=true,queries=0,religionReads=0,writes=0}
function metadata(fields)return setmetatable({},{__index=function(_,key)
 if F.metadataError then error('metadata')end;return F[fields[key]]end})end
Gold={GetPurchaseCost=function(self,y,h,f)assert(self==Gold and y==F.yieldIndex and h==F.hash and f==F.formation);return F.cost end}
Religion={GetFaithBalance=function(self)assert(self==Religion);return F.faith end,
 GetReligionTypeCreated=function(self)assert(self==Religion);return F.created end}
CityReligion={GetMajorityReligion=function(self)assert(self==CityReligion);return F.majority end}
City={GetID=function(self)assert(self==City);return F.foundID or F.id end,
 GetOwner=function(self)assert(self==City);return F.owner end,
 GetX=function(self)assert(self==City);return F.x end,GetY=function(self)assert(self==City);return F.y end,
 GetGold=function(self)assert(self==City);return Gold end,GetReligion=function(self)assert(self==City);return CityReligion end}
Cities={FindID=function(self,id)assert(self==Cities);F.findID=id;return City end}
Player={GetCities=function(self)assert(self==Player);return Cities end,
 GetReligion=function(self)assert(self==Player);F.religionReads=F.religionReads+1;return Religion end,
 SetProperty=function()F.writes=F.writes+1;error('no write')end}
E={GameInfo={Units={UNIT_MISSIONARY=metadata({UnitType='unitType',Hash='hash',MustPurchase='must',PurchaseYield='purchaseYield'})},
 Yields={YIELD_FAITH=metadata({Index='yieldIndex'})}},
 MilitaryFormationTypes=metadata({STANDARD_MILITARY_FORMATION='formation'}),
 CityCommandTypes=metadata({PURCHASE='op',PARAM_UNIT_TYPE='uk',PARAM_YIELD_TYPE='yk',PARAM_MILITARY_FORMATION_TYPE='fk'})}
E.CityManager={CanStartCommand=function(c,o,visible,params,results)
 assert(c==City and o==F.op and visible==false and results==true)
 assert(params[F.uk]==F.hash and params[F.yk]==F.yieldIndex and params[F.fk]==F.formation)
 F.queries=F.queries+1
 if F.late then for k,v in pairs(F.late)do F[k]=v end end
 if F.nativeError then error('native')end
 return F.qualifies
end,RequestCommand=function()F.writes=F.writes+1;error('no command')end}
GameInfo=nil;CityManager=nil;MilitaryFormationTypes=nil;CityCommandTypes=nil;rawget=nil
'''


class MissionaryQuoteTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(FIXTURE)
        self.m = self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiMissionaryPurchase.lua').read_text(encoding='utf-8'))
        self.g = self.lua.globals()

    def quote(self, city=None, pid=0, reserve=100):
        return self.m.Quote(self.g.E, self.g.Player, pid, city or self.g.City, reserve)

    def tearDown(self):
        self.assertEqual(self.g.F.writes, 0)

    def test_exact_scalar_quote_includes_native_signature(self):
        result = self.quote()
        self.assertEqual(dict(result), dict(cityID=65536, owner=0, x=16, y=14,
            unitType='UNIT_MISSIONARY', unitHash=-199, religionIndex=4, faithYieldIndex=5,
            formationType=0, cost=75, faithBalance=175, operation=77, unitKey=11,
            yieldKey=12, formationKey=13))
        self.assertEqual(self.g.F.queries, 1)

    def test_same_religion_component_once_each_round(self):
        self.assertIsNotNone(self.quote())
        self.assertEqual(self.g.F.religionReads, 2)

    def test_two_components_cannot_synthesize_faith_and_identity(self):
        self.lua.execute('''
F.created=3
Other={GetReligionTypeCreated=function()return 4 end,GetFaithBalance=function()return 0 end}
Player.GetReligion=function(self)assert(self==Player);F.religionReads=F.religionReads+1
 if F.religionReads%2==1 then return Religion else return Other end end
''')
        self.assertIsNone(self.quote())

    def test_prerequisites_and_budget(self):
        for key, value in [('created',-1),('majority',3),('unitType','UNIT_APOSTLE'),
                           ('unitType','UNIT_GREAT_PROPHET'),('must',False),
                           ('purchaseYield','YIELD_GOLD'),('faith',174),('cost',0)]:
            with self.subTest(field=key):
                self.setUp();self.g.F[key]=value
                self.assertIsNone(self.quote());self.assertEqual(self.g.F.queries,0)

    def test_every_signature_and_religion_field_rechecked(self):
        for key, value in [('hash',-198),('yieldIndex',6),('formation',1),('op',78),
                           ('uk',14),('yk',15),('fk',16),('cost',74),('faith',176),
                           ('created',5),('majority',5),('x',17),('owner',1),('foundID',131073)]:
            with self.subTest(field=key):
                self.setUp();self.g.F.late=self.lua.table_from({key:value})
                self.assertIsNone(self.quote());self.assertEqual(self.g.F.queries,1)

    def test_stale_caller_is_not_priced_and_current_city_id_is_exact(self):
        self.lua.execute("Caller={GetID=function()return 65536 end,GetOwner=function()return 0 end,GetX=function()return 16 end,GetY=function()return 14 end,GetGold=function()error('stale')end}")
        self.assertIsNotNone(self.quote(city=self.g.Caller))
        self.g.F.foundID=65537
        self.assertIsNone(self.quote(city=self.g.Caller))

    def test_exceptions_function_values_and_parameter_aliases(self):
        for code in ["F.metadataError=true", "F.nativeError=true", "F.uk=F.yk",
                     "E=setmetatable({},{__index=function()error('environment')end})",
                     "Gold.GetPurchaseCost=function()return function()F.called=true end end",
                     "City.GetReligion=nil"]:
            with self.subTest(code=code):
                self.setUp();self.lua.execute(code)
                self.assertIsNone(self.quote());self.assertFalse(self.g.F.called)

    def test_numeric_and_strict_boolean_boundaries(self):
        for key, value in [('hash',True),('hash',1.5),('op',4294967296),('yieldIndex',-1),
                           ('cost',float('inf')),('faith',float('nan')),('x',-1),
                           ('qualifies',1),('qualifies','true'),('qualifies',None)]:
            with self.subTest(field=key):
                self.setUp();self.g.F[key]=value;self.assertIsNone(self.quote())
        self.setUp();self.assertIsNone(self.quote(pid=True));self.assertIsNone(self.quote(reserve=-1))

    def test_userdata_and_zero_religion_are_valid(self):
        self.lua.execute('''
function wrap(v)local p=newproxy(true);getmetatable(p).__index=v;return p end
Player=wrap(Player);City=wrap(City);Cities=wrap(Cities);Gold=wrap(Gold)
Religion=wrap(Religion);CityReligion=wrap(CityReligion)
E.GameInfo.Units.UNIT_MISSIONARY=wrap(E.GameInfo.Units.UNIT_MISSIONARY)
E.GameInfo.Units=wrap(E.GameInfo.Units);E.GameInfo.Yields=wrap(E.GameInfo.Yields)
E.GameInfo=wrap(E.GameInfo)
E.MilitaryFormationTypes=wrap(E.MilitaryFormationTypes);E.CityCommandTypes=wrap(E.CityCommandTypes)
F.created=0;F.majority=0
''')
        self.assertEqual(self.quote().religionIndex, 0)


if __name__ == '__main__':
    unittest.main()
