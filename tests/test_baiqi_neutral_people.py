"""Actual Core grants and UI commands for native unowned-border merchant use."""
import unittest
import test_baiqi_scientist as fixture

KEY = 'BAIQI_GREAT_PERSON_INTENTS_V1'


class NeutralGreatPersonTests(unittest.TestCase):
    def setUp(self):
        fixture.BaiqiScientistTests.setUp(self)
        self.lua.execute('''
local w=TestWorld
local function row(t,key,index,hash,data)
 data.Index=index;data.Hash=hash;t[key]=data;t[index]=data;t[hash]=data
end
row(GameInfo.Units,'UNIT_GREAT_MERCHANT',7,207,{UnitType='UNIT_GREAT_MERCHANT'})
row(GameInfo.GreatPersonClasses,'GREAT_PERSON_CLASS_MERCHANT',3,903,{GreatPersonClassType='GREAT_PERSON_CLASS_MERCHANT'})
row(GameInfo.GreatPersonIndividuals,'GREAT_PERSON_INDIVIDUAL_MARCUS_LICINIUS_CRASSUS',76,776,{
 GreatPersonClassType='GREAT_PERSON_CLASS_MERCHANT',ActionCharges=3,
 ActionRequiresOwnedTile=false,ActionRequiresUnownedTile=true,ActionRequiresAdjacentOwnedTile=true,
 ActionRequiresCityStateTerritory=false,ActionRequiresSuzerainTerritory=false,
 ActionRequiresEnemyTerritory=false,ActionRequiresNonHostileTerritory=false})
w.scientistType=7;w.scientistClass=3;w.scientistIndividual=76;w.scientistCharges=3
w.owners={[42]=7,[43]=-1,[44]=8,[45]=-1,[46]=7};w.hidden={};w.invisible={};w.paths={};w.hiddenOwnerReads=0;w.borderScans=0
local xy={[42]={2,3},[43]={3,3},[44]={4,3},[45]={3,4},[46]={2,4}}
local plots={}
for index,pos in pairs(xy) do
 plots[index]={GetIndex=function() return index end,GetX=function() return pos[1] end,
  GetY=function() return pos[2] end,
  GetOwner=function()
   if w.hidden[index] then w.hiddenOwnerReads=w.hiddenOwnerReads+1;error('hidden owner read') end
   return w.owners[index]
  end,IsWater=function() return w.water==index end,IsImpassable=function() return w.impassable==index end}
end
Map.GetPlotByIndex=function(index) return plots[index] end
Map.GetPlot=function(x,y) for _,p in pairs(plots) do if p:GetX()==x and p:GetY()==y then return p end end end
Map.GetPlotDistance=function(x,y,x2,y2) return math.abs(x-x2)+math.abs(y-y2) end
Map.GetPlotXYWithRangeCheck=function(x,y,dx,dy) if dx==0 and dy==0 then return Map.GetPlot(x,y) end end
local neighbors={[42]={43,46},[43]={42,44,45},[44]={43},[45]={43,46},[46]={42,45}}
Map.GetAdjacentPlot=function(x,y,direction)
 local p=Map.GetPlot(x,y);local list=p and neighbors[p:GetIndex()]
 return list and plots[list[direction+1]]
end
Map.GetCityPlots=function() w.borderScans=w.borderScans+1;return {GetPurchasedPlots=function() return {42,46,42} end} end
PlayersVisibility[7].IsRevealed=function(_,x,y) local p=Map.GetPlot(x,y);return p and not w.hidden[p:GetIndex()] or false end
PlayersVisibility[7].IsVisible=function(_,x,y) local p=Map.GetPlot(x,y);return p and not w.invisible[p:GetIndex()] or false end
local u=w.objects.player:GetUnits():FindID(4)
u.GetX=function() return plots[w.scientistPlot]:GetX() end
u.GetY=function() return plots[w.scientistPlot]:GetY() end
UnitManager.GetMoveToPathEx=function(unit,index)
 w.paths[#w.paths+1]=index
 local start=Map.GetPlot(unit:GetX(),unit:GetY()):GetIndex()
 if w.noPath==index then return {plots={}} end
 if start==index then return {plots={index}} end
 if start==42 and index==45 then return {plots={42,46,45}} end
 if start==46 and index==43 then return {plots={46,42,43}} end
 return {plots={start,index}}
end
-- Deliberately permissive native double. Actual Core/UI plot guards must
-- independently reject wrong territory, even if this predicate says true.
UnitManager.CanStartCommand=function(unit,hash)
 assert(unit:GetID()==4 and hash==501)
 return (w.scientistPlot==43 or w.scientistPlot==45) and not w.rejectActivation
end
UI.RequestPlayerOperation=function() error('Unexpected diplomatic/player operation') end
''')
        self.h = self.lua.globals().TestBridge
        self.bridge = self.lua.globals().ExposedMembers.BaiqiGreatPersonIntentBridge

    def entry(self):
        return self.h.store[KEY].operations['4']

    def prepare(self):
        unit = self.w.objects.player.GetUnits(self.w.objects.player).FindID(None, 4)
        return self.bridge.Prepare(7, 4, 'UNIT_GREAT_MERCHANT', 3, 76, self.w.scientistCharges,
                                   unit.GetX(unit), unit.GetY(unit))

    def test_native_merchant_moves_from_owned_plot_to_neutral_then_activates_with_core_receipt(self):
        self.c.RunNow()
        self.assertEqual((self.w.unitRequests[1].op, self.w.unitRequests[1].params[14], self.w.unitRequests[1].params[15]), (10, 3, 3))
        self.assertEqual(len(self.w.commandRequests), 0)
        self.w.scientistPlot = 43
        self.c.Update(.35)
        self.assertEqual(len(self.w.commandRequests), 1)
        self.assertEqual((self.entry().stage, self.entry().charges, self.entry().unitType), ('ARMED', 3, 'UNIT_GREAT_MERCHANT'))

    def test_current_neutral_plot_activates_without_move_or_ui_property_ack(self):
        self.w.scientistPlot = 43
        self.lua.execute('''
local original=UnitManager.RequestCommand
UnitManager.RequestCommand=function(unit,...)
 assert(TestBridge.store.BAIQI_GREAT_PERSON_INTENTS_V1.operations['4'].stage=='ARMED')
 assert(Players[7]:GetProperty('BAIQI_GREAT_PERSON_INTENTS_V1')==nil)
 return original(unit,...)
end
''')
        self.c.RunNow()
        self.assertEqual((len(self.w.commandRequests), len(self.w.unitRequests)), (1, 0))

    def test_retained_border_destination_moves_next_step_without_rescanning_borders(self):
        self.w.noPath = 43
        self.c.RunNow()
        self.assertEqual((self.w.unitRequests[1].params[14], self.w.unitRequests[1].params[15]), (2, 4))
        scans = self.w.borderScans
        self.w.scientistPlot = 46
        self.w.noPath = None
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual((self.w.unitRequests[2].params[14], self.w.unitRequests[2].params[15]), (3, 4))
        self.assertEqual(self.w.borderScans, scans)
        self.assertEqual(list(self.w.paths.values()), [43, 45, 45])

    def test_retained_border_target_that_turns_foreign_is_replanned_before_write(self):
        self.w.noPath = 43
        self.c.RunNow()
        self.w.scientistPlot = 46
        self.w.noPath = None
        self.w.owners[45] = 8
        self.w.turn += 1
        self.c.RunNow()
        self.assertEqual((self.w.unitRequests[2].params[14], self.w.unitRequests[2].params[15]), (2, 3))
        self.assertEqual(len(self.w.commandRequests), 0)

    def test_foreign_and_city_state_territory_never_grant_even_with_permissive_native_gate(self):
        for owner in (8, 9):
            with self.subTest(owner=owner):
                self.setUp();self.w.scientistPlot = 43;self.w.owners[43] = owner
                self.assertFalse(self.prepare()[0])
                self.c.RunNow()
                self.assertIsNone(self.entry())
                self.assertEqual(len(self.w.commandRequests), 0)

    def test_missing_adjacent_owned_plot_denies_current_site(self):
        self.w.scientistPlot = 43
        self.w.owners[42] = 8
        self.assertFalse(self.prepare()[0])
        self.assertIsNone(self.entry())

    def test_core_grant_then_adjacent_ownership_loss_holds_unknown_without_any_command(self):
        self.w.scientistPlot = 43
        self.lua.execute('''
local b=ExposedMembers.BaiqiGreatPersonIntentBridge;local prepare=b.Prepare
b.Prepare=function(...)
 local granted,token,reason=prepare(...);TestWorld.owners[42]=8
 return granted,token,reason
end
''')
        self.c.RunNow()
        self.assertEqual(self.entry().stage, 'ARMED')
        self.assertEqual((len(self.w.commandRequests), len(self.w.unitRequests)), (0, 0))
        self.w.turn += 1;self.c.RunNow()
        self.assertEqual((len(self.w.commandRequests), len(self.w.unitRequests)), (0, 0))

    def test_target_becoming_foreign_after_core_grant_is_not_dispatched(self):
        self.w.scientistPlot = 43
        self.lua.execute('''
local b=ExposedMembers.BaiqiGreatPersonIntentBridge;local prepare=b.Prepare
b.Prepare=function(...)
 local granted,token,reason=prepare(...);TestWorld.owners[43]=8
 return granted,token,reason
end
''')
        self.c.RunNow()
        self.assertEqual((self.entry().stage, len(self.w.commandRequests)), ('ARMED', 0))

    def test_consumed_charge_and_claimed_tile_require_a_new_neutral_site_for_next_grant(self):
        self.w.scientistPlot = 43
        self.c.RunNow()
        first = self.entry().token
        self.w.scientistCharges = 2
        self.w.owners[43] = 7
        self.c.RunNow()
        self.assertEqual(len(self.w.commandRequests), 1)
        self.assertEqual(self.entry().stage, 'OBSERVED')
        self.w.scientistPlot = 45
        self.c.Update(.35)
        self.assertEqual(len(self.w.commandRequests), 2)
        self.assertNotEqual(self.entry().token, first)
        self.assertEqual((self.entry().charges, self.entry().sequence), (2, 2))

    def test_mixed_diplomatic_flags_and_unknown_values_do_not_widen_neutral_authority(self):
        for change in (
            "ActionRequiresCityStateTerritory=true", "ActionRequiresSuzerainTerritory=true",
            "ActionRequiresEnemyTerritory=true", "ActionRequiresNonHostileTerritory=true",
            "ActionRequiresOwnedTile=nil", "ActionRequiresUnownedTile='yes'",
            "ActionRequiresAdjacentOwnedTile=nil", "ActionRequiresCityStateTerritory='unknown'",
        ):
            with self.subTest(change=change):
                self.setUp();self.w.scientistPlot = 43
                self.lua.execute('GameInfo.GreatPersonIndividuals[76].'+change)
                self.assertFalse(self.prepare()[0])
                self.c.RunNow()
                self.assertEqual(len(self.w.commandRequests), 0)

    def test_explicit_numeric_and_string_boolean_encodings_match_real_flag_contract(self):
        self.w.scientistPlot = 43
        self.lua.execute('''
local r=GameInfo.GreatPersonIndividuals[76]
r.ActionRequiresOwnedTile=0;r.ActionRequiresUnownedTile='True';r.ActionRequiresAdjacentOwnedTile=1
r.ActionRequiresCityStateTerritory='false';r.ActionRequiresSuzerainTerritory='False'
r.ActionRequiresEnemyTerritory=0;r.ActionRequiresNonHostileTerritory=false
''')
        self.c.RunNow()
        self.assertEqual(len(self.w.commandRequests), 1)

    def test_hidden_sites_never_read_owner_or_receive_activation(self):
        self.w.scientistPlot = 43
        self.w.hidden[43] = True
        self.assertFalse(self.prepare()[0])
        self.c.RunNow()
        self.assertEqual((len(self.w.commandRequests), self.w.hiddenOwnerReads), (0, 0))

    def test_water_impassable_invisible_and_missing_adjacency_api_fail_closed(self):
        for condition in ('water', 'impassable', 'invisible', 'api'):
            with self.subTest(condition=condition):
                self.setUp();self.w.scientistPlot = 43
                if condition in ('water', 'impassable'):self.w[condition] = 43
                elif condition=='invisible':self.w.invisible[43] = True
                else:self.lua.execute('Map.GetAdjacentPlot=nil')
                self.assertFalse(self.prepare()[0])
                self.assertIsNone(self.entry())

    def test_armed_neutral_intent_remains_held_without_movement_or_skip(self):
        self.w.scientistPlot = 43
        self.assertTrue(self.prepare()[0])
        for _ in range(2):
            self.w.turn += 1;self.c.RunNow();self.c.Update(3600)
        self.assertEqual((self.entry().stage, len(self.w.commandRequests), len(self.w.unitRequests)), ('ARMED', 0, 0))

    def test_other_great_person_classes_do_not_receive_neutral_plot_grants(self):
        self.w.scientistPlot, self.w.scientistType = 43, 3
        self.w.scientistClass, self.w.scientistIndividual = 5, 70
        result = self.bridge.Prepare(7, 4, 'UNIT_GREAT_SCIENTIST', 5, 70, 3, 3, 3)
        self.assertFalse(result[0])
        self.assertIsNone(self.entry())


if __name__ == '__main__':
    unittest.main()
