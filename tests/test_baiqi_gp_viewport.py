from pathlib import Path
from lupa.lua51 import LuaRuntime
import unittest
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'mod/Baiqi/Lua/BaiqiGPViewport.lua').read_text(encoding='utf-8')
FIXTURE='''
W={height=689,writes=0,own=true,failOriginal=false}
function node(id,height,offset,children)
 local c={id=id,h=height,oy=offset or 0,children=children or {}}
 function c:GetID()return self.id end
 function c:GetChildren()return self.children end
 function c:GetSizeY()return self.h end
 function c:GetOffsetY()return self.oy end
 function c:SetSizeY(y)self.h=y;W.writes=W.writes+1;if self.throwOnce then self.throwOnce=false;error('setter failure')end end
 function c:SetOffsetY(y)self.oy=y;W.writes=W.writes+1 end
 function c:CalculateSize()end
 function c:ReprocessAnchoring()end
 return c
end
function card()
 local c=node('Content',670)
 c.name=node('IndividualName',14,-295)
 c.effect=node('EffectStackScroller',240,224)
 c.points=node('RecruitProgressBox',152,30)
 c.main=node('MainInfo',654,0,{c.effect,c.points})
 c.bioScroll=node('BiographyScroll',391)
 c.bio=node('BiographyArea',391,58,{c.bioScroll})
 c.detailScroll=node('RecruitInfoScroll',391)
 c.detail=node('RecruitInfoArea',391,54,{c.detailScroll})
 c.children={c.name,c.main,c.bio,c.detail}
 return c
end
Controls={PopupContainer=node('PopupContainer',768),PeopleScroller=node('PeopleScroller',768),RecruitedScroller=node('RecruitedScroller',586),PeopleStack=node('PeopleStack',670)}
Controls.PeopleStack.children={card(),card()}
UIManager={GetScreenSizeVal=function()return 1008,W.height end}
BaiqiUIGuard={PlayerID=function()if W.own then return 0 end end}
function ViewCurrent(a,b)if W.failOriginal then error('native renderer failed')end;W.current=(W.current or 0)+1;return a,nil,b end
function ViewPast(a)W.past=(W.past or 0)+1;return a end
function geometry()
 local popup=Controls.PopupContainer.h
 assert(popup<=W.height)
 local top=(W.height-popup)/2
 for _,c in ipairs(Controls.PeopleStack.children)do
  assert(top+78+c.h<=W.height-20)
  assert(math.abs((c.h/2+c.name.oy)-40)<=0.5,'Name must keep native top40 within one pixel')
  assert(c.points.h==152,'All public recruitment point rows keep their space')
  assert(224+c.effect.h+8==c.main.h-30-c.points.h,'Effect viewport must not overlap points')
  assert(c.effect.h>=72)
  assert(top+78+c.main.h+10<=W.height-26,'Patronage row stays visible')
  assert(c.bio.h==c.bioScroll.h and c.detail.h==c.detailScroll.h)
  assert(c.h-58-c.bio.h==221 and c.h-54-c.detail.h==225)
 end
 assert(Controls.RecruitedScroller.h==popup-182)
end
'''
class GreatPeopleViewportTests(unittest.TestCase):
 def setUp(self):
  self.lua=LuaRuntime();self.lua.compile(SOURCE);self.lua.execute(FIXTURE);self.lua.execute(SOURCE)
 def test_actual_689_fits_title_effect_points_and_costs_without_data_writes(self):
  self.lua.execute("assert(BaiqiGPViewport.Apply());geometry();assert(Controls.PopupContainer.h==689 and Controls.PeopleStack.children[1].main.h==575)")
 def test_repeat_resize_both_directions_and_native_pool_reuse(self):
  self.lua.execute("assert(BaiqiGPViewport.Apply());assert(BaiqiGPViewport.Apply());geometry();W.height=1080;assert(BaiqiGPViewport.Apply());geometry();assert(Controls.PopupContainer.h==768 and Controls.PeopleStack.children[1].h==670 and Controls.PeopleStack.children[1].name.oy==-295);W.height=600;assert(BaiqiGPViewport.Apply());geometry();Controls.PeopleStack.children[2]=card();W.height=689;assert(BaiqiGPViewport.Apply());geometry()")
 def test_later_bad_card_and_cycle_preflight_causes_no_partial_layout(self):
  self.lua.execute("local good=Controls.PeopleStack.children[1];local bad=Controls.PeopleStack.children[2];bad.main.children={bad.points};assert(BaiqiGPViewport.Apply()==false and W.writes==0 and good.h==670);bad.main.children={bad.effect,bad.points,bad};assert(BaiqiGPViewport.Apply()==false and W.writes==0)")
 def test_normal_leader_unknown_height_and_external_layout_are_untouched(self):
  self.lua.execute("W.own=false;assert(BaiqiGPViewport.Apply()==false and W.writes==0);W.own=true;W.height=0/0;assert(BaiqiGPViewport.Apply()==false and W.writes==0);W.height=599;assert(BaiqiGPViewport.Apply()==false and W.writes==0);W.height=689;Controls.PeopleStack.children[2].main.h=999;assert(BaiqiGPViewport.Apply()==false and W.writes==0)")
 def test_native_callbacks_results_errors_and_setter_rollback(self):
  self.lua.execute("assert(BaiqiGPViewport.Install()and not BaiqiGPViewport.Install());local a,b,c=ViewCurrent('one','two');assert(a=='one'and b==nil and c=='two'and W.current==1);geometry();assert(ViewPast('history')=='history'and W.past==1);local writes=W.writes;W.failOriginal=true;local ok,e=pcall(ViewCurrent);assert(not ok and string.find(e,'native renderer failed',1,true)and W.writes==writes);W.failOriginal=false;W.height=700;Controls.PeopleStack.children[2].main.throwOnce=true;assert(BaiqiGPViewport.Apply()==false);W.height=689;geometry();assert(BaiqiGPViewport.Apply());geometry()")
 def test_actual_wrapper_keeps_data_helper_and_installs_viewport(self):
  self.lua.execute("BaiqiUILoader={Load=function(name)assert(name=='GreatPeoplePopup');W.loads=(W.loads or 0)+1 end,ReadOnly=function()W.readonly=true end};BaiqiGPViewData={Install=function()W.dataInstalls=(W.dataInstalls or 0)+1 end}")
  self.lua.globals().include=lambda name: self.lua.execute(SOURCE) if name=='BaiqiGPViewport' else None
  self.lua.execute((ROOT/'mod/Baiqi/UI/BaiqiGreatPeoplePopup.lua').read_text(encoding='utf-8'))
  self.lua.execute("assert(W.loads==1 and W.readonly and W.dataInstalls==1);ViewCurrent('data','tail');geometry();assert(W.current==1)")
 def test_native_equal_handles_are_fresh_table_keys_on_each_children_read(self):
  self.lua.execute('''
  local meta={}
  local function alias(c)return setmetatable({target=c},meta)end
  local function children(c)
   local result={};for i,v in ipairs(c.children)do result[i]=alias(v)end;return result
  end
  meta.__eq=function(a,b)return a.target==b.target end
  meta.__index=function(p,key)
   if key=='GetChildren'then return function()return children(p.target)end end
   local value=p.target[key]
   if type(value)=='function'then return function(_,...)return value(p.target,...)end end
   return value
  end
  Controls.PeopleStack.GetChildren=function(self)return children(self)end
  local a,b=Controls.PeopleStack:GetChildren(),Controls.PeopleStack:GetChildren()
  assert(a[1]==b[1]);local keyed={[a[1]]=true};assert(keyed[b[1]]==nil)
  assert(BaiqiGPViewport.Apply());geometry()
  assert(BaiqiGPViewport.Apply(),'Fresh native aliases must preserve repeat adaptation');geometry()
  W.height=1080;assert(BaiqiGPViewport.Apply());geometry()
  W.height=689;assert(BaiqiGPViewport.Apply());geometry()
  ''')
 def test_native_pool_can_reset_cards_to_xml_with_header_still_adapted(self):
  self.lua.execute('''
  assert(BaiqiGPViewport.Apply());geometry()
  assert(Controls.PopupContainer.h==689)
  for _,c in ipairs(Controls.PeopleStack.children)do
   c.h=670;c.name.oy=-295;c.main.h=654;c.effect.h=240;c.points.h=152
   c.bio.h=391;c.bioScroll.h=391;c.detail.h=391;c.detailScroll.h=391
  end
  assert(Controls.PopupContainer.h==689)
  assert(BaiqiGPViewport.Apply(),'Native XML card reset must be qualified again');geometry()
  Controls.PeopleStack.children[2].main.h=999
  local before=W.writes
  assert(BaiqiGPViewport.Apply()==false and W.writes==before)
  ''')
if __name__=='__main__':unittest.main()
