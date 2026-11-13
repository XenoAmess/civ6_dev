"""A batch-local journal must be fresh again before any result is returned."""
import unittest

from tests import test_baiqi_food_tile_rescue as rescue_fixture


class FoodTileBatchSnapshotTests(unittest.TestCase):
    def world(self):
        return rescue_fixture.FoodTileRescueTests().world()

    def test_three_city_canonical_batch_loads_twice_and_never_caches_next_call(self):
        lua = self.world()
        lua.execute('''
          local b=ExposedMembers.BaiqiFoodTileRescueBridge
          local own=Players[0]:GetCities();local find=own.FindID
          local third={GetID=function()return 65537 end,GetOwner=function()return 0 end}
          own.FindID=function(self,id)if id==65537 then return third end;return find(self,id)end
          local get=Players[0].GetProperty;local reads=0
          Players[0].GetProperty=function(self,key)
            assert(key=='FOOD_TEST_V1');reads=reads+1;return get(self,key)
          end
          local request={{cityID=458758},{cityID=65536},{cityID=65537}}
          for i=1,2 do
            local status,rows=b.InspectBatch(0,request)
            assert(status=='READY' and rows['65537'].stage=='OPEN')
            assert(reads==i*2)
          end
          assert(#W.requests==0 and (W.propertyWrites or 0)==0)
        ''')

    def test_changed_final_journal_discards_all_rows_and_cannot_grant_a_send(self):
        lua = self.world()
        lua.execute('''
          local b=ExposedMembers.BaiqiFoodTileRescueBridge
          assert(b.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208))
          local armed=CopyProperty(W.props.FOOD_TEST_V1);W.props.FOOD_TEST_V1=nil
          local batch=b.InspectBatch
          b.InspectBatch=function(...)
            local status,rows=batch(...);W.batchStatus=status;W.batchHadRows=rows~=nil
            return status,rows
          end
          local get=Players[0].GetProperty;local reads=0
          Players[0].GetProperty=function(self,key)
            reads=reads+1;if reads==2 then W.props.FOOD_TEST_V1=armed end
            return get(self,key)
          end
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(reads==2 and #W.requests==0 and W.propertyWrites==1)
          assert(W.batchStatus=='UNAVAILABLE' and W.batchHadRows==false)
          assert(W.props.FOOD_TEST_V1.records['458758'].stage=='ARMED')
        ''')

    def test_throwing_corrupt_or_changed_context_at_final_read_returns_unknown(self):
        for change in ("error('unknown final journal')", "W.props[key]={version=9}",
                       "W.turn=W.turn+1", "W.human=false",
                       "ExposedMembers.BaiqiFoodTileRescueBridge.Inspect=function()return 'OPEN'end"):
            with self.subTest(change=change):
                lua = self.world()
                lua.execute('''
                  local b=ExposedMembers.BaiqiFoodTileRescueBridge
                  local get=Players[0].GetProperty;local reads=0
                  Players[0].GetProperty=function(self,key)
                    reads=reads+1;if reads==2 then ''' + change + ''' end
                    return get(self,key)
                  end
                  local status,rows=b.InspectBatch(0,{{cityID=458758},{cityID=65536}})
                  assert(status=='UNAVAILABLE' and rows==nil and reads==2)
                  assert(#W.requests==0 and (W.propertyWrites or 0)==0)
                ''')

    def test_observed_working_bank_is_propagated_and_reverified_after_write(self):
        lua = self.world()
        lua.execute('''
          local b=ExposedMembers.BaiqiFoodTileRescueBridge
          assert(b.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208))
          W.transferred=true;W.surplus=0;W.turn=210
          local status,rows=b.InspectBatch(0,{{cityID=458758},{cityID=65536}})
          assert(status=='READY' and rows['458758'].stage=='OBSERVED')
          assert(rows['458758'].token=='foodtile:0:1' and rows['65536'].stage=='OPEN')
          assert(W.props.FOOD_TEST_V1.records['458758'].stage=='OBSERVED')
          assert(W.propertyWrites==2 and #W.requests==0)
        ''')

    def test_unconfirmed_observation_write_never_returns_a_usable_batch(self):
        lua = self.world()
        lua.execute('''
          local b=ExposedMembers.BaiqiFoodTileRescueBridge
          assert(b.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208))
          W.transferred=true;W.surplus=0;W.turn=210
          W.afterPersist=function()W.readError=true end
          local status,rows=b.InspectBatch(0,{{cityID=458758},{cityID=65536}})
          assert(status=='UNAVAILABLE' and rows==nil)
          assert(W.props.FOOD_TEST_V1.records['458758'].stage=='OBSERVED' and #W.requests==0)
          W.afterPersist=nil;W.readError=false;BaiqiFoodTileRescueRunner.Run(E,0)
          assert(W.propertyWrites==2 and #W.requests==0)
        ''')

    def test_changed_owner_before_pending_observation_never_persists_receipt(self):
        lua = self.world()
        lua.execute('''
          local b=ExposedMembers.BaiqiFoodTileRescueBridge
          assert(b.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208))
          W.transferred=true;W.surplus=0;W.turn=210
          local get=Players[0].GetProperty
          Players[0].GetProperty=function(self,key)
            local value=get(self,key);W.human=false;return value
          end
          local status,rows=b.InspectBatch(0,{{cityID=458758},{cityID=65536}})
          assert(status=='UNAVAILABLE' and rows==nil and W.propertyWrites==1 and #W.requests==0)
          assert(W.props.FOOD_TEST_V1.records['458758'].stage=='ARMED')
        ''')


if __name__ == '__main__':
    unittest.main()
