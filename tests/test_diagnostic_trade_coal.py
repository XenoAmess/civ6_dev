"""Current-view metadata only: never initialize, mutate, or send a deal."""
from pathlib import Path
import os
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('TRADE_COAL_SOURCE', ROOT / 'tools/lua/diagnostic_trade_coal.lua'))


class TradeCoalReaderTests(unittest.TestCase):
    def world(self):
        l = LuaRuntime(unpack_returned_tuples=True)
        l.globals().M = l.execute(SOURCE.read_text(encoding='utf-8'))
        l.execute('''
          W={turn=308,active=true,hidden=false,multi=false,busy=false,processing=false,
            pid=0,otherID=1,human=true,leader='LEADER_BAIQI',met=true,
            items={{ForType=7,MaxAmount=10,IsValid=true}},workingCalls=0,possibleCalls=0,
            forbidden=0,badArgs=0}
          local function forbidden()W.forbidden=W.forbidden+1;error('forbidden mutation')end
          local dip={HasMet=function(_,id)if id~=W.otherID then W.badArgs=W.badArgs+1 end;return W.met end}
          local lp={GetID=function()return W.pid end,IsTurnActive=function()return W.active end,
            GetDiplomacy=function()return dip end}
          local op={GetID=function()return W.otherID end}
          Deal={AddItemOfType=forbidden,Validate=forbidden,RemoveItemByID=forbidden}
          E={ContextPtr={IsHidden=function()return W.hidden end,SetHide=forbidden},
            Game={GetLocalPlayer=function()return W.pid end,GetCurrentGameTurn=function()return W.turn end},
            GameConfiguration={IsAnyMultiplayer=function()return W.multi end},
            UI={IsGameCoreBusy=function()return W.busy end,IsProcessingMessages=function()return W.processing end,
              RequestAction=forbidden},Players={[0]=lp,[1]=op},
            PlayerConfigurations={[0]={IsHuman=function()return W.human end,GetLeaderTypeName=function()return W.leader end}},
            GameInfo={Resources={RESOURCE_COAL={Index=7,ResourceType='RESOURCE_COAL',ResourceClassType='RESOURCECLASS_STRATEGIC'}}},
            DealDirection={OUTGOING=4},DealItemTypes={RESOURCES=9},localPlayer=lp,otherPlayer=op,
            isDemand=false,isGift=false,initiatedByPlayerID=0,
            Network={RequestSession=forbidden}}
          E.DealManager={GetWorkingDeal=function(dir,a,b)
            W.workingCalls=W.workingCalls+1
            if dir~=4 or a~=0 or b~=1 then W.badArgs=W.badArgs+1 end
            if W.onWorking then W.onWorking(W.workingCalls)end
            if W.workingError then error(string.rep('private',1000))end
            if W.noDeal then return nil end
            return Deal
          end,GetPossibleDealItems=function(a,b,kind,deal)
            W.possibleCalls=W.possibleCalls+1
            if a~=1 or b~=0 or kind~=9 or deal~=Deal then W.badArgs=W.badArgs+1 end
            if W.change then W.change()end
            if W.itemsError then error('possible items unavailable')end
            return W.items
          end,ClearWorkingDeal=forbidden,CopyIncomingToOutgoingWorkingDeal=forbidden,
            SendWorkingDeal=forbidden,RequestSession=forbidden}
          function CheckNoWrites()assert(W.forbidden==0 and W.badArgs==0)end
        ''')
        return l

    def test_current_other_to_local_metadata_uses_exact_four_arguments(self):
        l = self.world()
        l.execute('''local r=M.Read(E);assert(r.status=='KNOWN' and r.turn==308)
          assert(r.localPlayerID==0 and r.otherPlayerID==1)
          assert(r.coal.index==7 and r.coal.maxAmount==10 and r.coal.valid and r.coal.present)
          assert(W.workingCalls==2 and W.possibleCalls==1);CheckNoWrites()''')

    def test_empty_and_invalid_row_metadata_keep_index_and_validity(self):
        l = self.world()
        l.execute('''W.items={};local r=M.Read(E);assert(r.status=='KNOWN')
          assert(r.coal.index==7 and r.coal.maxAmount==0 and not r.coal.valid and not r.coal.present)
          W.items={{ForType=7,MaxAmount=10,IsValid=false,Duration=0}}
          r=M.Read(E);assert(r.status=='KNOWN' and r.coal.present and not r.coal.valid and r.coal.maxAmount==10)
          CheckNoWrites()''')

    def test_environment_rejection_never_touches_deal_or_mutators(self):
        cases = ['W.hidden=true', 'W.multi=true', 'W.busy=true', 'W.processing=true',
                 'W.active=false', 'W.human=false', 'W.leader="OTHER"', 'W.met=false',
                 'E.isDemand=true', 'E.isGift=nil', 'E.initiatedByPlayerID=1',
                 'E.localPlayer={}', 'E.otherPlayer={GetID=function()return 2 end}',
                 'E.GameInfo.Resources.RESOURCE_COAL.Index=0/0', 'setmetatable(E,{})']
        for case in cases:
            with self.subTest(case=case):
                l = self.world()
                l.execute(case + ''';local r=M.Read(E);assert(r.status=='UNKNOWN')
                  assert(W.workingCalls==0 and W.possibleCalls==0);CheckNoWrites()''')

    def test_missing_or_throwing_read_ports_are_unknown_without_zero_fallback(self):
        for case in ['W.noDeal=true', 'W.items=nil', 'W.items=false', 'W.workingError=true',
                     'W.itemsError=true', 'E.DealManager.GetPossibleDealItems=nil',
                     'E.ContextPtr.IsHidden=nil']:
            with self.subTest(case=case):
                l = self.world()
                l.execute(case + ';local r=M.Read(E);assert(r.status=="UNKNOWN" and r.coal==nil);CheckNoWrites()')

    def test_dense_key_limits_holes_metadata_keys_and_duplicate_coal_are_rejected(self):
        for case in ['W.items={[3]=W.items[1]}', 'W.items[0]=W.items[1]',
                     'W.items.note=true', 'W.items[257]=W.items[1]',
                     'W.items[2]=W.items[1]', 'setmetatable(W.items,{})',
                     'W.items[1]=false']:
            with self.subTest(case=case):
                l = self.world()
                l.execute(case + ';assert(M.Read(E).status=="UNKNOWN");CheckNoWrites()')

    def test_all_rows_require_finite_integer_quantities_and_strict_booleans(self):
        for change in ['r.MaxAmount=1.5', 'r.MaxAmount=-1', 'r.MaxAmount=math.huge',
                       'r.MaxAmount=1000001', 'r.ForType=0/0', 'r.ForType=1.5',
                       'r.IsValid=1', 'r.IsValid=nil']:
            with self.subTest(change=change):
                l = self.world()
                l.execute('W.items[2]={ForType=8,MaxAmount=3,IsValid=true};local r=W.items[2];'
                          + change + ';assert(M.Read(E).status=="UNKNOWN");CheckNoWrites()')

    def test_final_current_view_and_player_drift_are_unknown(self):
        for change in ['W.turn=309', 'W.hidden=true', 'W.active=false', 'W.multi=true',
                       'W.busy=true', 'W.processing=true', 'W.met=false', 'W.otherID=2',
                       'E.isGift=true', 'E.initiatedByPlayerID=1',
                       'E.Players[1]={GetID=function()return 1 end}']:
            with self.subTest(change=change):
                l = self.world()
                l.execute('W.change=function()' + change + ' end;assert(M.Read(E).status=="UNKNOWN");CheckNoWrites()')

    def test_rebound_api_and_changed_working_deal_never_return_known(self):
        for change in ['E.DealManager.GetWorkingDeal=function()return Deal end',
                       'E.DealManager.GetPossibleDealItems=function()return W.items end',
                       'E.Game.GetCurrentGameTurn=function()return 308 end', 'Deal={}']:
            with self.subTest(change=change):
                l = self.world()
                l.execute('W.change=function()' + change + ' end;assert(M.Read(E).status=="UNKNOWN");CheckNoWrites()')

    def test_final_working_getter_side_effect_is_rechecked(self):
        l = self.world()
        l.execute('''W.onWorking=function(n)if n==2 then W.hidden=true end end
          assert(M.Read(E).status=='UNKNOWN');CheckNoWrites()''')

    def test_repeated_reads_are_stateless_and_results_do_not_alias_input(self):
        l = self.world()
        l.execute('''local original=W.items[1];local a=M.Read(E);assert(a.status=='KNOWN')
          a.coal.maxAmount=0;assert(original.MaxAmount==10)
          local b=M.Read(E);assert(b.status=='KNOWN' and b.coal.maxAmount==10)
          assert(E.otherPlayerID==nil and W.items[1]==original and W.workingCalls==4)
          CheckNoWrites()''')

    def test_fresh_metadata_wrappers_and_unused_mirror_do_not_replace_actual_other_id(self):
        l = self.world()
        l.execute('''local resources=E.GameInfo.Resources
          resources.RESOURCE_COAL=nil
          setmetatable(resources,{__index=function(_,k)if k=='RESOURCE_COAL'then return {
            Index=7,ResourceType='RESOURCE_COAL',ResourceClassType='RESOURCECLASS_STRATEGIC'}end end})
          E.otherPlayerID=55
          local r=M.Read(E);assert(r.status=='KNOWN' and r.otherPlayerID==1 and r.coal.index==7)
          CheckNoWrites()''')

    def test_nonplain_or_absent_environment_and_error_output_are_bounded(self):
        l = self.world()
        l.execute('''assert(M.Read(nil).status=='UNKNOWN');assert(M.Read(false).status=='UNKNOWN')
          W.workingError=true;local r=M.Read(E)
          assert(r.status=='UNKNOWN' and #r.reason<64 and not r.reason:find('private'))
          CheckNoWrites()''')


if __name__ == '__main__':
    unittest.main()
