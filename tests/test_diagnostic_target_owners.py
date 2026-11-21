from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53
ROOT=Path(__file__).resolve().parents[1]
HARNESS=r'''
return function(M,which)
 local h={calls=0,published=nil,turn=138,localPlayer=0,owner=0,id=42};local marker={};local resultTable={x=1}
 local actor={GetID=function()if h.actorError then error(marker)end;return h.id end,GetOwner=function()return h.owner end}
 local function Native(...)
  h.calls=h.calls+1;h.args={n=select('#',...),...};if h.action then h.action()end
  if h.raise then error(marker)end;if h.void then return end;if h.falseReturn then return false end;return nil,false,resultTable,nil
 end
 local backing={UnitManager={RequestOperation=Native,RequestCommand=Native},CityManager={RequestOperation=Native,RequestCommand=Native},UI={RequestPlayerOperation=Native}}
 local managers,originals={},{};h.SDKwrites=0
 for name,t in pairs(backing)do
  t.ReadScalar=17;t.ReadObject=resultTable;t.ReadFunction=Native
  local sdk=setmetatable({},{__index=t,__newindex=function()h.SDKwrites=h.SDKwrites+1;error('Attempt to modify read-only table')end})
  managers[name]=sdk;originals[name]=sdk
 end
 local o={context='fixture',getPublished=function()return h.published end,publish=function(v)h.published=v;if h.publishError then error(marker)end end,getManager=function(n)return managers[n]end,setManager=function(n,v)managers[n]=v end,unpack=table.unpack or unpack,game={GetCurrentGameTurn=function()return h.turn end,GetLocalPlayer=function()return h.localPlayer end}}
 if which=='invalid-setter'then o.setManager=nil;assert(not pcall(M.Install,o)and managers.UnitManager==originals.UnitManager and h.SDKwrites==0);return true end
 if which=='setter-noop'then o.setManager=function()end;assert(not pcall(M.Install,o)and managers.UnitManager==originals.UnitManager and h.published==nil and h.SDKwrites==0);return true end
 if which=='setter-error'then o.setManager=function(n,v)managers[n]=v;if n=='CityManager'and v~=originals[n]then error(marker)end end;local ok,e=pcall(M.Install,o);assert(not ok and e==marker and managers.UnitManager==originals.UnitManager and managers.CityManager==originals.CityManager and h.published==nil and h.SDKwrites==0);return true end
 if which=='setter-foreign'then local foreign={};o.setManager=function(n,v)managers[n]=v;if n=='UI'and v~=originals[n]then managers[n]=foreign;error(marker)end end;local ok,e=pcall(M.Install,o);assert(not ok and e==marker and managers.UI==foreign and managers.UnitManager==originals.UnitManager and managers.CityManager==originals.CityManager and h.published==nil and h.SDKwrites==0);return true end
 if which=='namespace'then local foreign={};h.published=foreign;assert(not pcall(M.Install,o)and h.published==foreign and managers.UnitManager.RequestOperation==Native and h.calls==0);return true end
 if which=='invalid-manager'then managers.UI=nil;assert(not pcall(M.Install,o)and managers.UnitManager.RequestOperation==Native and h.published==nil and h.calls==0);return true end
 if which=='publish-error'then h.publishError=true;assert(not pcall(M.Install,o)and h.published==nil and managers.UnitManager.RequestOperation==Native and managers.CityManager.RequestCommand==Native and h.calls==0);return true end
 if which=='publish-foreign'then local f=function()end;o.publish=function(v)h.published=v;if v then managers.UnitManager.RequestOperation=f end end;local ok=pcall(M.Install,o);assert(not ok and managers.UnitManager.RequestOperation==f and h.published==nil and managers.CityManager.RequestCommand==Native);return true end
 if which=='publish-foreign-global'then local foreign={};o.publish=function(v)h.published=v;if v then managers.UnitManager=foreign end end;assert(not pcall(M.Install,o)and managers.UnitManager==foreign and managers.CityManager==originals.CityManager and h.published==nil and h.SDKwrites==0);return true end
 local s=M.Install(o);assert(h.calls==0 and s.BindingKnown())
 for name,t in pairs(managers)do assert(t~=originals[name]and t.ReadScalar==17 and t.ReadObject==resultTable and t.ReadFunction==Native)end
 local fn=managers.UnitManager.RequestOperation
 if which=='before-store-error'then setmetatable(s.rows,{__newindex=function()error(marker)end})end
 if which=='foreign-binding'then local f=function()end;managers.UnitManager.RequestOperation=f;assert(not s.BindingKnown()and not pcall(s.Restore)and managers.UnitManager.RequestOperation==f and h.published==s);return true
 elseif which=='foreign-namespace'then local f={};h.published=f;assert(not pcall(s.Restore)and h.published==f and managers.UnitManager.RequestOperation==fn);return true
 elseif which=='foreign-table'then local old=managers.UnitManager;managers.UnitManager={RequestOperation=Native,RequestCommand=Native};assert(not pcall(s.Restore)and old.RequestOperation==fn);return true
 elseif which=='actor-error'then h.actorError=true
 elseif which=='fractional-turn'then h.turn=138.5
 elseif which=='local-unknown'then h.localPlayer=-1
 elseif which=='owner-unknown'then h.owner=true
 elseif which=='foreign-owner'then h.owner=1
 elseif which=='native-error'then h.raise=true
 elseif which=='void'then h.void=true
 elseif which=='false-return'then h.falseReturn=true
 end
 local params={x=1,flag=false,nested={a='b'}}
 if which=='cycle'then params.self=params elseif which=='param-function'then params.bad=function()error('Never execute observed parameter')end elseif which=='param-bound'then for i=1,129 do params[i]=i end end
 if which=='after-error'then h.action=function()setmetatable(s.rows[1],{__newindex=function()error(marker)end})end end
 if which=='native-error'then local ok,e=pcall(fn,actor,-7,params,nil);assert(not ok and e==marker and h.calls==1 and not s.rows[1].returned)
 elseif which=='void'then assert(select('#',fn(actor,-7,params,nil))==0 and s.rows[1].returnCount==0)
 elseif which=='false-return'then assert(select('#',fn(actor,-7,params,nil))==1 and fn~=Native and s.rows[1].returnCount==1)
 else local ret={n=0};local function Capture(...)ret={n=select('#',...),...}end;Capture(fn(actor,-7,params,nil));assert(ret.n==4 and ret[1]==nil and ret[2]==false and ret[3]==resultTable and ret[4]==nil and h.args.n==4 and h.args[1]==actor and h.args[3]==params and h.calls==1)end
 if which=='before-store-error'then assert(s.metadataErrors==1 and #s.rows==0 and h.calls==1)
 elseif which=='actor-error'or which=='fractional-turn'or which=='local-unknown'or which=='owner-unknown'or which=='cycle'or which=='param-function'or which=='param-bound'then assert(s.metadataErrors==1 and not s.rows[1].metadataKnown)
 elseif which=='after-error'then assert(s.afterErrors==1)
 else assert(s.metadataErrors==0 and s.rows[1].metadataKnown);if which=='foreign-owner'then assert(s.rows[1].owner==1)end end
 if which=='copy'then params.x=2;params.nested.a='c';assert(s.rows[1].params.x==1 and s.rows[1].params.flag==false and s.rows[1].params.nested.a=='b')end
 if which=='player'then managers.UI.RequestPlayerOperation(1,123,{x=1});local r=s.rows[2];assert(r.domain=='UI'and r.owner==1 and r.id==1 and r.argumentCount==3 and r.returnCount==4)end
 if which=='all-five'then managers.UnitManager.RequestCommand(actor,1);managers.CityManager.RequestOperation(actor,2);managers.CityManager.RequestCommand(actor,3);managers.UI.RequestPlayerOperation(0,4);assert(s.writeCalls==5 and #s.rows==5)end
 if which=='cap'then for i=1,300 do fn(actor,-7,{})end;assert(s.writeCalls==301 and #s.rows==256 and s.dropped==45 and h.calls==301)end
 if which=='tick-flood'then local t={Update=Native};s.AddTick('Controller',t,'Update');for i=1,2000 do local a,b,c,d=t.Update(0.5,true);assert(a==nil and b==false and c==resultTable and d==nil)end;assert(s.tickCalls==2000 and s.writeCalls==1 and #s.rows==1 and s.dropped==0 and #s.ticks==1 and s.ticks[1].calls==2000 and s.ticks[1].returned==2000 and s.ticks[1].lastReturnCount==4)end
 if which=='freeze'then local cached=managers.UnitManager.RequestOperation;assert(s.Freeze()and s.paused and s.BindingKnown()and cached==managers.UnitManager.RequestOperation);local a,b,c,d=cached(actor,-7,{});assert(a==nil and b==false and c==resultTable and d==nil and h.calls==2 and s.writeCalls==1 and #s.rows==1 and cached==managers.UnitManager.RequestOperation);local t={Update=Native};assert(not pcall(s.AddTick,'late',t,'Update')and t.Update==Native)end
 if which=='tick-error'then local t={Update=Native};s.AddTick('Controller',t,'Update');h.raise=true;local ok,e=pcall(t.Update,0.5,true);assert(not ok and e==marker and s.tickCalls==1 and s.ticks[1].calls==1 and s.ticks[1].returned==0 and #s.rows==1);h.raise=false end
 if which=='scope'then local inner={Run=function()return fn(actor,10,{})end};local outer={RunNow=function()return inner.Run()end};s.AddTick('Admin',inner,'Run');s.AddTick('Controller',outer,'RunNow');outer.RunNow();assert(s.rows[2].planningScope=='Admin.Run'and s.rows[2].scopeDepth==2);fn(actor,11,{});assert(s.rows[3].planningScope=='UNSCOPED'and s.rows[3].scopeDepth==0)end
 if which=='scope-error'then local t={RunNow=function()fn(actor,10,{});error(marker)end};s.AddTick('Controller',t,'RunNow');local ok,e=pcall(t.RunNow);assert(not ok and e==marker and s.rows[2].planningScope=='Controller.RunNow'and s.rows[2].scopeDepth==1);fn(actor,11,{});assert(s.rows[3].planningScope=='UNSCOPED'and s.rows[3].scopeDepth==0)end
 if which=='tick'then local t={Update=Native,RunNow=Native};s.AddTick('Controller',t,'Update');s.AddTick('Controller',t,'RunNow');local captured=t.Update;local a,b,c,d=captured(0.5,true);assert(a==nil and b==false and c==resultTable and d==nil and s.tickCalls==1 and t.Update==captured and #s.rows==1 and s.ticks[1].kind=='TICK'and s.ticks[1].owners[0]==1 and s.ticks[1].firstTurn==138 and s.ticks[1].lastTurn==138);local ok=pcall(s.AddTick,'Controller',t,'Update');assert(not ok and t.Update==captured);assert(s.Restore()and t.Update==Native and t.RunNow==Native)else assert(s.Restore())end
 for name,t in pairs(managers)do assert(t==originals[name]);for k,f in pairs(backing[name])do assert(t[k]==f)end end
 assert(h.SDKwrites==0 and s.retired and not s.active and h.published==nil and s.Restore());return true
end
'''


class TargetOwnerObserverTests(unittest.TestCase):
    def test_actual_producer_transparency_metadata_bounds_and_owned_lifecycle(self):
        source=(ROOT/'tools/lua/diagnostic_target_owners.lua').read_text(encoding='utf-8')
        cases=['invalid-setter','setter-noop','setter-error','setter-foreign','publish-foreign-global','namespace','invalid-manager','publish-error','publish-foreign','foreign-binding','foreign-namespace','foreign-table','actor-error','fractional-turn','local-unknown','owner-unknown','foreign-owner','native-error','void','false-return','cycle','param-function','param-bound','before-store-error','after-error','copy','player','all-five','cap','tick','tick-flood','tick-error','scope','scope-error','freeze','normal']
        for vm in (L51,L53):
            lua=vm();run=lua.execute(HARNESS);producer=lua.execute(source)
            for case in cases:
                with self.subTest(vm=vm.__module__,case=case):
                    self.assertTrue(run(producer,case))


if __name__=='__main__':unittest.main()
