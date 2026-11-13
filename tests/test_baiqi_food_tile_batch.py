"""Batch receipts retain the real persistence and final single-send gates."""
from pathlib import Path
import unittest

from tests import test_baiqi_food_tile_rescue as rescue_fixture

ROOT = Path(__file__).resolve().parents[1]
UI_SOURCE = (ROOT / 'mod/Baiqi/Lua/BaiqiFoodTileRescueRunner.lua').read_text(encoding='utf-8')


class FoodTileBatchTests(unittest.TestCase):
    def world(self):
        return rescue_fixture.FoodTileRescueTests().world()

    def test_real_batch_reads_every_city_once_per_positive_callback(self):
        lua = self.world()
        lua.execute('''
          W.surplus=1;local b=ExposedMembers.BaiqiFoodTileRescueBridge
          local inspect,batch=b.Inspect,b.InspectBatch;local reads,batches=0,0
          b.Inspect=function(...)reads=reads+1;return inspect(...)end
          b.InspectBatch=function(pid,requests)
            batches=batches+1;assert(#requests==2)
            assert(requests[1].cityID==458758 and requests[2].cityID==65536)
            return batch(pid,requests)
          end
          BaiqiFoodTileRescueRunner.Run(E,0);BaiqiFoodTileRescueRunner.Run(E,0)
          assert(batches==2 and reads==4 and #W.requests==0 and (W.propertyWrites or 0)==0)
        ''')

    def test_late_old_arm_is_observed_even_in_a_positive_city(self):
        lua = self.world()
        lua.execute('''
          local b=ExposedMembers.BaiqiFoodTileRescueBridge
          assert(b.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208))
          W.transferred=true;W.surplus=0;W.turn=210
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(W.props.FOOD_TEST_V1.records['458758'].stage=='OBSERVED')
          assert(W.propertyWrites==2 and #W.requests==0)
        ''')

    def test_old_unknown_arm_survives_batch_reload_without_new_permission(self):
        lua = self.world()
        lua.execute('''
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==1 and W.propertyWrites==1)
        ''')
        lua.execute(UI_SOURCE)
        lua.execute('''
          W.turn=211;BaiqiFoodTileRescueRunner.Run(E,0);BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==1 and W.propertyWrites==1)
          assert(W.props.FOOD_TEST_V1.records['458758'].stage=='ARMED')
        ''')

    def test_core_validates_whole_input_before_any_observer(self):
        bad = (
            'nil', '{}', '{[2]={cityID=458758}}',
            '{{cityID=458758},{cityID=458758}}',
            '{{cityID=458758},{cityID=999}}',
            '{{cityID=458758},{cityID=65536,extra=true}}',
            '{{cityID=458758},{cityID=65536,token={}}}',
            'setmetatable({{cityID=458758}}, {})',
            '{setmetatable({cityID=458758}, {})}',
            '(function()local r={};for i=1,129 do r[i]={cityID=i}end;return r end)()',
        )
        for value in bad:
            with self.subTest(value=value):
                lua = self.world()
                lua.execute('''
                  local b=ExposedMembers.BaiqiFoodTileRescueBridge;local calls=0
                  b.Inspect=function()calls=calls+1;error('unexpected inspection')end
                  local status,rows=b.InspectBatch(0,''' + value + ''')
                  assert(status=='UNAVAILABLE' and rows==nil and calls==0)
                  assert(#W.requests==0 and (W.propertyWrites or 0)==0)
                ''')

    def test_core_keeps_validated_request_values_when_caller_table_changes(self):
        lua = self.world()
        lua.execute('''
          local b=ExposedMembers.BaiqiFoodTileRescueBridge;local inspect=b.Inspect
          local requests={{cityID=458758},{cityID=65536}};local calls=0
          b.Inspect=function(pid,id,token)
            calls=calls+1
            if calls==1 then requests[2].cityID=999 end
            assert(id==458758 or id==65536);return inspect(pid,id,token)
          end
          local status,rows=b.InspectBatch(0,requests)
          assert(status=='READY' and calls==2 and rows['65536'].cityID==65536 and rows['999']==nil)
        ''')

    def test_core_detects_changed_turn_binding_or_reader_exception(self):
        for change in ("W.turn=W.turn+1", "b.Inspect=function()error('new')end", "error('reader')"):
            with self.subTest(change=change):
                lua = self.world()
                lua.execute('''
                  local b=ExposedMembers.BaiqiFoodTileRescueBridge;local calls=0
                  b.Inspect=function()calls=calls+1;''' + change + ''';return 'OPEN',nil,'no_record'end
                  local status,rows=b.InspectBatch(0,{{cityID=458758},{cityID=65536}})
                  assert(status=='UNAVAILABLE' and rows==nil and calls==1)
                  assert(#W.requests==0 and (W.propertyWrites or 0)==0)
                ''')

    def test_core_preserves_per_city_unknown_tokens(self):
        lua = self.world()
        lua.execute('''
          local b=ExposedMembers.BaiqiFoodTileRescueBridge
          assert(b.Prepare(0,458758,59,32,65536,55,34,2277,57,30,208))
          local status,rows=b.InspectBatch(0,{{cityID=458758,token='wrong'},{cityID=65536}})
          assert(status=='READY' and rows['458758'].stage=='UNKNOWN' and rows['458758'].token=='wrong')
          assert(rows['65536'].stage=='OPEN' and rows['65536'].token==nil)
          assert(#W.requests==0 and W.propertyWrites==1)
        ''')

    def test_present_unavailable_or_throwing_batch_never_falls_back(self):
        for method in ("function()return 'UNAVAILABLE'end", "function()error('reply lost')end", 'false'):
            with self.subTest(method=method):
                lua = self.world()
                lua.execute('''
                  local b=ExposedMembers.BaiqiFoodTileRescueBridge
                  b.InspectBatch=''' + method + '''
                  b.Inspect=function()error('individual fallback forbidden')end
                  b.Prepare=function()W.unexpectedPrepare=true end
                  BaiqiFoodTileRescueRunner.Run(E,0)
                  assert(not W.unexpectedPrepare and #W.requests==0 and (W.propertyWrites or 0)==0)
                ''')

    def test_ui_rejects_bad_envelope_rows_stages_tokens_and_ids(self):
        mutations = (
            "rows['65536']=nil", "rows[1]=rows['65536']", "rows['458758'].cityID=65536",
            "rows['458758'].stage='SUCCESS'", "rows['458758'].stage='ARMED'",
            "rows['458758'].token='unexpected'", "rows['458758'].extra=true",
            "setmetatable(rows,{})", "setmetatable(rows['458758'],{})",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                lua = self.world()
                lua.execute('''
                  local b=ExposedMembers.BaiqiFoodTileRescueBridge;local batch=b.InspectBatch
                  b.InspectBatch=function(...)
                    local status,rows=batch(...);assert(status=='READY');''' + mutation + '''
                    return status,rows
                  end
                  b.Prepare=function()W.unexpectedPrepare=true end
                  BaiqiFoodTileRescueRunner.Run(E,0)
                  assert(not W.unexpectedPrepare and #W.requests==0 and (W.propertyWrites or 0)==0)
                ''')

    def test_replaced_prepare_after_batch_aborts_before_a_new_grant(self):
        lua = self.world()
        lua.execute('''
          local b=ExposedMembers.BaiqiFoodTileRescueBridge;local batch=b.InspectBatch
          b.InspectBatch=function(...)
            local status,rows=batch(...)
            b.Prepare=function()W.foreignPrepare=true end
            return status,rows
          end
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(not W.foreignPrepare and #W.requests==0 and (W.propertyWrites or 0)==0)
        ''')

    def test_absent_optional_method_retains_legacy_real_permission_flow(self):
        lua = self.world()
        lua.execute('''
          ExposedMembers.BaiqiFoodTileRescueBridge.InspectBatch=nil
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==1 and W.propertyWrites==1)
          W.transferred=true;W.surplus=0;W.turn=209
          BaiqiFoodTileRescueRunner.Run(E,0)
          assert(#W.requests==1 and W.props.FOOD_TEST_V1.records['458758'].stage=='OBSERVED')
        ''')


if __name__ == '__main__':
    unittest.main()
