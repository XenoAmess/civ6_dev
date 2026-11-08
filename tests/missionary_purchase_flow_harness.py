from pathlib import Path
import sys
from lupa.lua53 import LuaRuntime
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'tests'),str(R)]
from religious_intent_harness import install_religious_bridge
K='BAIQI_MISSIONARY_PURCHASE_INTENTS_V1'
def make():
 l=LuaRuntime(unpack_returned_tuples=True)
 for name in ('mock_world','mock_missionary'):
  l.execute((R/f'tests/lua/{name}.lua').read_text(encoding='utf-8'))
 l.execute('''
 local w=TestWorld
 w.cityMajority=1;w.secondCity=true;w.withMissionary=false;w.faith=175;w.purchaseCost=75
 w.purchases={};w.purchaseQualifies=0;w.purchaseLegal=true
 GameInfo.Units.UNIT_MISSIONARY=GameInfo.Units[60]
 GameInfo.Units[60].MustPurchase=true;GameInfo.Units[60].PurchaseYield='YIELD_FAITH'
 GameInfo.Yields={YIELD_FAITH={Index=5}}
 MilitaryFormationTypes={STANDARD_MILITARY_FORMATION=0}
 CityCommandTypes={PURCHASE=77,PARAM_UNIT_TYPE=11,PARAM_YIELD_TYPE=12,PARAM_MILITARY_FORMATION_TYPE=13}
 local old=w.objects.player.GetReligion
 w.objects.player.GetReligion=function(self)
  local religion=old(self);religion.GetFaithBalance=function()return w.faith end;return religion
 end
 w.objects.city.GetGold=function()return{GetPurchaseCost=function(_,yield,hash,formation)
  assert(yield==5 and hash==600 and formation==0);return w.purchaseCost end}end
 w.objects.missionary.IsDelayedDeath=function()return w.missionaryDead==true end
 CityManager.CanStartCommand=function(city,op,visible,params,result)
  assert(op==77 and visible==false and result==true)
  assert(params[11]==600 and params[12]==5 and params[13]==0)
  w.purchaseQualifies=w.purchaseQualifies+1
  if w.qualificationHook then w.qualificationHook(w.purchaseQualifies)end
  return w.purchaseLegal
 end
 CityManager.RequestCommand=function(city,op,params)
  local saved=TestRelBridge.store.BAIQI_MISSIONARY_PURCHASE_INTENTS_V1
  assert(saved.operations['1'].stage=='ARMED'and saved.operations['1'].cityID==city:GetID())
  assert(TestRelBridge.store.BAIQI_RELIGIOUS_INTENTS_V1~=nil)
  assert(op==77 and params[11]==600 and params[12]==5 and params[13]==0)
  w.purchases[#w.purchases+1]={city=city:GetID(),op=op}
  if w.autoPurchase then
   w.faith=w.faith-75;w.withMissionary=true;w.missionaryID=900
   w.missionaryPlot=42;w.missionaryMoves=0;w.unitReligion=1;w.spreadCharges=3
  end
  if w.throwPurchase then error('unknown command result')end
 end
 ''')
 logs=[];l.globals().print=lambda *args:logs.append(' '.join(map(str,args)))
 install_religious_bridge(l)
 # Add real required native members to the binding fixture; Core/UI stay separate.
 l.execute('''
 local core=TestRelBridge.core;core.getmetatable=getmetatable;core.assert=assert
 local p=core.Players[7];local old=p.GetUnits
 p.GetUnits=function(self)
  local units=old(self);local members=units.Members
  units.Members=function(self)
   local iterator=members(self)
   return function(...)local i,u=iterator(...)
    if u then u.IsDelayedDeath=function()return TestWorld.missionaryDead==true end end
    return i,u
   end
  end
  return units
 end
 ''')
 load=l.eval('function(source,name,env)local fn,e=load(source,name,"t",env);assert(fn,e);return fn()end')
 core=l.globals().TestRelBridge.core
 for name in ('BaiqiNaturalistPurchaseJournal','BaiqiMissionaryPurchaseJournal','BaiqiFaithPurchaseGuard',
              'BaiqiMissionaryPurchaseSnapshot','BaiqiMissionaryPurchaseIntentGameplay'):
  load((R/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'),name,core)
 for name in ('BaiqiConfig','BaiqiPolicy','BaiqiPlanner','BaiqiHeritageCandidates','BaiqiHeritageActions',
              'BaiqiMissionaryPurchase'):
  l.execute((R/f'mod/Baiqi/Lua/{name}.lua').read_text(encoding='utf-8'))
 l.execute((R/'mod/Baiqi/Lua/BaiqiMissionaryPurchaseDemand.lua').read_text(encoding='utf-8'))
 l.execute((R/'mod/Baiqi/Lua/BaiqiMissionaryPurchaseSubmit.lua').read_text(encoding='utf-8'))
 l.execute((R/'mod/Baiqi/Lua/BaiqiController.lua').read_text(encoding='utf-8'))
 return l,logs
