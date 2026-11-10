from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class CrisisViewportTests(unittest.TestCase):
    def world(self):
        l = LuaRuntime(unpack_returned_tuples=True)
        l.execute('''
          W={width=1008,height=689,sets=0,human=true,multi=false,leader='LEADER_BAIQI'}
          BaiqiConfig={leader='LEADER_BAIQI'};Players={[0]={}}
          Game={GetLocalPlayer=function()return 0 end}
          GameConfiguration={IsAnyMultiplayer=function()return W.multi end,IsHotseat=function()return false end}
          PlayerConfigurations={[0]={IsHuman=function()return W.human end,GetLeaderTypeName=function()return W.leader end}}
          UIManager={GetScreenSizeVal=function()return W.width,W.height end}
          Controls={};local bases={SlideOnShow=760,DropShadow=760,Window=768,TitleContainer=768,
            CrisisBG=523,CrisisDetailScrollPanel=220,BaseStack=660,EmergencyDetailScrollPanel=96,LeaderBarScrollPanel=155}
          function NewControls()
            for name,h in pairs(bases)do
              local c={h=h,name=name}
              c.GetSizeY=function(self)return self.h end
              c.SetSizeY=function(self,n)
                W.sets=W.sets+1;self.h=n
                if name=='DropShadow'then Controls.Window.h=n+8;Controls.TitleContainer.h=n+8 end
                if W.setterFailure==name then W.setterFailure=nil;error('mutated before throw')end
              end
              c.CalculateSize=function(self)
                if name=='BaseStack'then self.h=Controls.CrisisBG.h+137 end
                if W.reflowFailure then W.reflowFailure=false;error('reflow failure')end
              end
              c.ReprocessAnchoring=function()end
              Controls[name]=c
            end
          end
          NewControls()
          function CheckFit()
            local window=Controls.Window.h;local top=(W.height-window)/2
            local buttonTop=top+window-18-41
            assert(top>=0 and buttonTop>=0 and buttonTop+41<=W.height)
            assert(Controls.DropShadow.h+8==window and Controls.TitleContainer.h==window)
            assert(Controls.CrisisDetailScrollPanel.h>=52)
            assert(Controls.EmergencyDetailScrollPanel.h==96 and Controls.LeaderBarScrollPanel.h==155)
          end
          W.nativeCalls=0
          ShowEmergency=function(...)
            W.nativeCalls=W.nativeCalls+1;W.nativeArgs={n=select('#',...),...}
            if W.nativeError then error('native error')end
            return false,nil,'native result'
          end
          NativeEventHandler=function(data)return ShowEmergency(data)end
        ''')
        l.execute((ROOT / 'mod/Baiqi/Lua/BaiqiCrisisViewport.lua').read_text(encoding='utf-8'))
        return l

    def test_native_parent_plus_eight_fits_small_and_wide_viewports(self):
        for height in (600, 689, 768, 1080, 2160):
            with self.subTest(height=height):
                l = self.world()
                l.execute(f'W.height={height};assert(BaiqiCrisisViewport.Apply());CheckFit()')

    def test_repeated_resize_and_recreated_native_handles(self):
        l = self.world()
        l.execute('''for _,height in ipairs({689,689,600,1080,689})do
            W.height=height;assert(BaiqiCrisisViewport.Apply());CheckFit()end
          NewControls();assert(BaiqiCrisisViewport.Apply());CheckFit()''')

    def test_all_preflight_checks_finish_before_any_setter(self):
        for change in ['Controls.CrisisDetailScrollPanel.h=999',
                       'Controls.CrisisDetailScrollPanel.SetSizeY=nil',
                       'Controls.LeaderBarScrollPanel.CalculateSize=nil',
                       'Controls.SlideOnShow.ReprocessAnchoring=nil']:
            with self.subTest(change=change):
                l = self.world()
                l.execute(change + ';assert(not BaiqiCrisisViewport.Apply() and W.sets==0)')

    def test_mutating_setter_and_reflow_failure_restore_old_sizes(self):
        for change in ['W.setterFailure="Window"', 'W.reflowFailure=true']:
            with self.subTest(change=change):
                l = self.world()
                l.execute(change + ''';assert(not BaiqiCrisisViewport.Apply())
                  assert(Controls.Window.h==768 and Controls.DropShadow.h==760)
                  assert(Controls.CrisisBG.h==523 and Controls.CrisisDetailScrollPanel.h==220)
                  assert(BaiqiCrisisViewport.Apply());CheckFit()''')

    def test_unknown_geometry_wrong_owner_or_multiplayer_do_not_write(self):
        for change in ['W.height=599', 'W.height=0/0', 'W.height=math.huge',
                       'W.height=689.5', 'W.width=594', 'W.human=false',
                       'W.multi=true', 'W.leader="OTHER"']:
            with self.subTest(change=change):
                l = self.world()
                l.execute(change + ';assert(not BaiqiCrisisViewport.Apply() and W.sets==0)')

    def test_registered_native_consumer_calls_wrapped_global_after_original_data(self):
        l = self.world()
        l.execute('''assert(BaiqiCrisisViewport.Install())
          local a,b,c=NativeEventHandler('real data')
          assert(W.nativeCalls==1 and W.nativeArgs[1]=='real data')
          assert(a==false and b==nil and c=='native result');CheckFit()
          local installed=ShowEmergency;assert(not BaiqiCrisisViewport.Install() and ShowEmergency==installed)''')

    def test_forwarding_preserves_nils_arity_and_native_errors(self):
        l = self.world()
        l.execute('''assert(BaiqiCrisisViewport.Install())
          local a,b,c=ShowEmergency(nil,'second',nil)
          assert(W.nativeArgs.n==3 and W.nativeArgs[2]=='second' and a==false and b==nil and c=='native result')
          local n=W.sets;W.nativeError=true
          local ok,why=pcall(ShowEmergency,'error')
          assert(not ok and string.find(why,'native error') and W.sets==n)''')

    def test_failed_layout_does_not_swallow_original_result_or_restrict_choices(self):
        l = self.world()
        l.execute('''local join=function()return 'native join' end
          OnJoinClicked=join;assert(BaiqiCrisisViewport.Install())
          W.setterFailure='Window';local a,b,c=ShowEmergency('data')
          assert(a==false and b==nil and c=='native result' and W.nativeCalls==1)
          assert(OnJoinClicked==join and OnJoinClicked()=='native join')''')


if __name__ == '__main__':
    unittest.main()
