"""Exercise Controller orders with the native primary/religious layer split."""
import unittest
import test_baiqi_civilian_overlap as overlap


class ReligiousLayerTests(unittest.TestCase):
    def setUp(self):
        overlap.CivilianOverlapTests.setUp(self)
        self.lua.execute('''
MapLayers={PRIMARY=0,TRADE=1,SPY=2,RELIGIOUS=3,ANY=-1}
TestWorld.religiousReads={}
GameInfo.Units[61]={UnitType='UNIT_APOSTLE',Index=61,Hash=661,
 FormationClass='FORMATION_CLASS_CIVILIAN'}
local own={GetID=function() return 19 end,GetOwner=function() return 7 end,
 GetUnitType=function() return 61 end}
local foreign={GetID=function() return 19 end,GetOwner=function() return 8 end,
 GetUnitType=function() return 61 end}
Units.GetUnitsInPlotLayerID=function(plot,layer)
 assert(layer==3,'Background must not query spy, trade or all map layers')
 local index=plot:GetIndex()
 TestWorld.religiousReads[index]=(TestWorld.religiousReads[index] or 0)+1
 if index==42 and TestWorld.religiousOverlap then return {own} end
 if index==43 and TestWorld.religiousTarget then return {own} end
 if index==43 and TestWorld.religiousEnemy then return {foreign} end
 return {}
end
''')

    def test_religious_overlap_moves_only_the_managed_civilian(self):
        self.w.overlap = False
        self.w.religiousOverlap = True
        self.c.RunNow()
        requests = list(self.w.unitRequests.values())
        self.assertEqual([(r.unit, r.op) for r in requests], [(4, 10)])
        self.assertEqual((requests[0].params[14], requests[0].params[15]), (3, 3))

    def test_religious_occupied_parking_is_not_empty(self):
        self.w.religiousTarget = True
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_visible_at_war_religious_unit_blocks_relocation(self):
        self.w.religiousEnemy = True
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_hidden_target_is_not_queried(self):
        self.w.hiddenTarget = True
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 0)
        self.assertIsNone(self.w.religiousReads[43])

    def test_invisible_current_plot_is_not_queried(self):
        self.w.hiddenEnemy = True
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 0)
        self.assertEqual(len(self.w.religiousReads), 0)

    def test_missing_layer_binding_does_not_assume_empty(self):
        self.lua.execute('Units.GetUnitsInPlotLayerID=nil')
        self.c.RunNow()
        self.assertEqual(len(self.w.unitRequests), 0)

    def test_missing_or_invalid_religious_enum_does_not_assume_empty(self):
        for value in ('nil', "'3'"):
            with self.subTest(value=value):
                self.setUp()
                self.lua.execute('MapLayers.RELIGIOUS=' + value)
                self.c.RunNow()
                self.assertEqual(len(self.w.unitRequests), 0)

    def test_unavailable_or_invalid_layer_result_does_not_assume_empty(self):
        for value in ('nil', 'false', '1'):
            with self.subTest(value=value):
                self.setUp()
                self.lua.execute('Units.GetUnitsInPlotLayerID=function() return ' + value + ' end')
                self.c.RunNow()
                self.assertEqual(len(self.w.unitRequests), 0)

    def test_primary_and_religious_occupants_never_send_army_orders(self):
        self.w.religiousOverlap = True
        self.c.RunNow()
        self.assertEqual([(r.unit, r.op) for r in self.w.unitRequests.values()], [(4, 10)])

    def test_native_wait_keeps_both_layers_in_place(self):
        self.w.religiousOverlap = True
        self.w.allowWait = True
        self.c.RunNow()
        self.assertEqual([(r.unit, r.op) for r in self.w.unitRequests.values()], [(4, 17)])


if __name__ == '__main__':
    unittest.main()
