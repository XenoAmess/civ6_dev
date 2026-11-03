from pathlib import Path
import json
import unittest
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class NaturalistPurchaseTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.module = self.lua.execute((ROOT / 'mod/Baiqi/Lua/BaiqiNaturalistPurchase.lua').read_text(encoding='utf-8'))
        self.lua.execute('''
          F={cityID=65536,owner=0,x=16,y=14,unitType='UNIT_NATURALIST',unitHash=1877270220,
            faithYieldIndex=5,formation=0,purchaseOp=1490793096,unitParam=-1899860717,
            yieldParam=730511874,formationParam=2126768863,faith=400,cost=300,reserve=100,
            nativeQualifies=true,qualifications=0,writes=0,costCalls={}}
          local function metadata(values)
            return setmetatable({},{__index=function(_,key)
              if F.throwMetadata then error('metadata') end
              local field=values[key];return field and F[field]
            end})
          end
          GameInfo={Units={UNIT_NATURALIST=metadata({UnitType='unitType',Hash='unitHash'})},
            Yields={YIELD_FAITH=metadata({Index='faithYieldIndex'})}}
          MilitaryFormationTypes=metadata({STANDARD_MILITARY_FORMATION='formation'})
          CityCommandTypes=metadata({PURCHASE='purchaseOp',PARAM_UNIT_TYPE='unitParam',
            PARAM_YIELD_TYPE='yieldParam',PARAM_MILITARY_FORMATION_TYPE='formationParam'})
          local gold={GetPurchaseCost=function(self,yieldIndex,hash,formation)
            F.costCalls[#F.costCalls+1]={yieldIndex=yieldIndex,hash=hash,formation=formation}
            return F.cost
          end}
          FreshCity={GetID=function() return F.foundID or F.cityID end,GetOwner=function() return F.owner end,
            GetX=function() return F.x end,GetY=function() return F.y end,GetGold=function() return gold end}
          local cities={}
          function cities:FindID(id) assert(self==cities);F.requestedID=id;return FreshCity end
          local religion={GetFaithBalance=function() return F.faith end}
          Player={GetCities=function() return cities end,GetReligion=function() return religion end,
            SetProperty=function() F.writes=F.writes+1;error('forbidden write') end}
          CityManager={CanStartCommand=function(city,op,visible,params,results)
            F.qualifications=F.qualifications+1
            assert(city==FreshCity and op==F.purchaseOp and visible==false and results==true)
            assert(params[F.unitParam]==F.unitHash and params[F.yieldParam]==F.faithYieldIndex
              and params[F.formationParam]==F.formation)
            for key,value in pairs(F) do
              if type(key)=='string' and string.sub(key,1,4)=='late' then
                local suffix=string.sub(key,5)
                F[string.lower(string.sub(suffix,1,1))..string.sub(suffix,2)]=value
              end
            end
            if F.throwNative then error('qualification') end
            return F.nativeQualifies
          end,RequestCommand=function() F.writes=F.writes+1;error('forbidden purchase') end}
        ''')
        self.f = self.lua.globals().F

    def quote(self, city=None, pid=0):
        return self.module.Quote(self.lua.globals().Player, pid,
                                 city if city is not None else self.lua.globals().FreshCity, self.f.reserve)

    def test_curated_model_data(self):
        cases = json.loads((ROOT / 'tests/fixtures/naturalist_purchase_cases.json').read_text(encoding='utf-8'))['cases']
        for case in cases:
            with self.subTest(case=case['name']):
                self.setUp()
                for key,value in case['changes'].items():
                    self.f[key] = value
                self.assertEqual(self.quote() is not None, case['expect'])
                self.assertEqual(self.f.writes, 0)

    def test_exact_plain_scalar_quote_without_write(self):
        result = self.quote()
        self.assertEqual(dict(result), {'cityID':65536,'owner':0,'x':16,'y':14,
                                       'unitType':'UNIT_NATURALIST','unitHash':1877270220,
                                       'faithYieldIndex':5,'formationType':0,'cost':300,'faithBalance':400})
        self.assertIsNone(self.lua.eval('getmetatable')(result))
        self.assertEqual((self.f.qualifications,self.f.writes,self.f.requestedID), (1,0,65536))

    def test_all_native_metadata_rechecked_after_qualification(self):
        for field,value in (('lateUnitHash',123),('lateFaithYieldIndex',6),('lateFormation',1),
                            ('latePurchaseOp',22),('lateUnitParam',23),('lateYieldParam',24),('lateFormationParam',25)):
            with self.subTest(field=field):
                self.setUp()
                self.f[field] = value
                self.assertIsNone(self.quote())

    def test_provider_and_native_exceptions_fail_closed(self):
        for source in ("F.throwMetadata=true", "F.throwNative=true",
                       "Player=setmetatable({},{__index=function() error('player') end})",
                       "CityManager=setmetatable({},{__index=function() error('manager') end})",
                       "GameInfo.Units='primitive'", "FreshCity.GetGold=nil"):
            with self.subTest(source=source):
                self.setUp()
                self.lua.execute(source)
                self.assertIsNone(self.quote())

    def test_fresh_city_resolved_before_native_qualification(self):
        self.lua.execute('''
          StaleCity={GetID=FreshCity.GetID,GetOwner=FreshCity.GetOwner,GetX=FreshCity.GetX,GetY=FreshCity.GetY,
            GetGold=function() error('Do not price stale caller object') end}
        ''')
        self.assertIsNotNone(self.quote(city=self.lua.globals().StaleCity))
        self.assertEqual(self.f.qualifications, 1)

    def test_full_identity_owner_and_position_changes(self):
        for field,value in (('foundID',131072),('owner',1),('lateOwner',1),('lateCityID',131072),('lateX',17),('lateY',15)):
            with self.subTest(field=field):
                self.setUp()
                self.f[field] = value
                if field == 'foundID':
                    self.lua.execute('''Caller={GetID=function() return 65536 end,
                      GetOwner=FreshCity.GetOwner,GetX=FreshCity.GetX,GetY=FreshCity.GetY}''')
                    self.assertIsNone(self.quote(city=self.lua.globals().Caller))
                else:
                    self.assertIsNone(self.quote())

    def test_numeric_boundaries(self):
        for field,value in (('cityID',2147483648),('cityID',True),('x',-1),('y',0.5),
                            ('faith',float('nan')),('cost',float('inf')),('cost',0),('reserve',-1),
                            ('unitHash',True),('unitHash',1.5),('faithYieldIndex',-1),('purchaseOp',4294967296)):
            with self.subTest(field=field):
                self.setUp()
                self.f[field] = value
                self.assertIsNone(self.quote())
        self.setUp()
        self.assertIsNone(self.quote(pid=True))

    def test_native_boolean_and_single_qualification(self):
        for value in (False,1,'true',None):
            with self.subTest(value=value):
                self.setUp()
                self.f.nativeQualifies = value
                self.assertIsNone(self.quote())
                self.assertEqual((self.f.qualifications,self.f.writes), (1,0))


if __name__ == '__main__':
    unittest.main()
