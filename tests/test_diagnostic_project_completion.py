from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime as L51
from lupa.lua53 import LuaRuntime as L53

SOURCE=Path(__file__).resolve().parents[1]/'tools/lua/diagnostic_project_completion.lua'
HARNESS=r'''
return function(M,which)
 local w={turn=10,owner=0,reads=0,callbacks={},removed=0,addCalls=0}
 local city={GetID=function()return 65536 end,GetOwner=function()return w.owner end}
 local event={Add=function(...)assert(select('#',...)==1);w.addCalls=w.addCalls+1;local f=...;w.callbacks[#w.callbacks+1]=f;w.own=f;if which=='add-throw'then error('after attach')end end,Remove=function(...)assert(select('#',...)==1);local f=...;w.removed=w.removed+1;assert(f==w.own);if w.removeFalse then return false end;for i,v in ipairs(w.callbacks)do if v==f then table.remove(w.callbacks,i);break end end end}
 local e={Game={GetCurrentGameTurn=function()w.reads=w.reads+1;if w.throw then error('read failed')end;return w.turn end,GetLocalPlayer=function()return 0 end},Players={[0]={GetCities=function()return{FindID=function(_,id)assert(id==65536);return city end}end}},PlayerConfigurations={[0]={IsHuman=function()return true end,GetLeaderTypeName=function()return'LEADER_BAIQI'end}},Events={CityProjectCompleted=event},cityID=65536,projectIndex=15,minTurn=10,maxTurn=18,maxRecords=1}
 local function Emit(...)local copy={};for i,f in ipairs(w.callbacks)do copy[i]=f end;for _,f in ipairs(copy)do f(...)end end
 if which=='bounds'then e.maxRecords=0;assert(not pcall(M.Install,e)and w.addCalls==0);return true end
 if which=='add-throw'then assert(not pcall(M.Install,e)and #w.callbacks==0 and w.removed==1);return true end
 local h=M.Install(e);assert(w.addCalls==1 and #w.callbacks==1 and #h.samples==0)
 if which=='foreign'then local n=0;local foreign=function()n=n+1 end;w.callbacks[#w.callbacks+1]=foreign;assert(h.Restore()and #w.callbacks==1 and w.callbacks[1]==foreign);Emit(0,65536,15);assert(n==1 and #h.samples==0);return true end
 if which=='remove-false'then w.removeFalse=true;assert(not h.Restore()and not h.active and not h.restored and h.removeErrors==1);Emit(0,65536,15);assert(#h.samples==0);w.removeFalse=false;assert(h.Restore()and h.Restore()and w.removed==2 and #w.callbacks==0);return true end
 if which=='scope-error'then w.owner=1 elseif which=='read-error'then w.throw=true end
 local before=w.reads;Emit(1,65536,15);Emit(0,99,15);Emit(0,65536,16);assert(w.reads==before and #h.samples==0)
 Emit(0,65536,15);assert(h.matches==1 and #h.samples==1);local r=h.samples[1];assert(r.playerID==0 and r.cityID==65536 and r.projectID==15 and r.arity==3)
 if which=='scope-error'or which=='read-error'then assert(r.status=='UNKNOWN'and r.turn==nil and h.errors==1)else assert(r.status=='KNOWN_EVENT_ONLY'and r.turn==10 and h.errors==0)end
 if which=='cap'then local reads=w.reads;Emit(0,65536,15);Emit(0,65536,15);assert(h.matches==3 and h.drops==2 and #h.samples==1 and w.reads==reads)end
 assert(h.Restore()and h.Restore()and h.restored and not h.active and w.removed==1 and #w.callbacks==0);Emit(0,65536,15);assert(h.matches==(which=='cap'and 3 or 1));return true
end
'''

class ProjectCompletionTests(unittest.TestCase):
    def test_actual_module_boundaries_both_lua_versions(self):
        for version,Runtime in [('Lua51',L51),('Lua53',L53)]:
            lua=Runtime();module=lua.execute(SOURCE.read_text(encoding='utf-8'));run=lua.execute(HARNESS)
            for case in ['ordinary','scope-error','read-error','cap','add-throw','remove-false','foreign','bounds']:
                with self.subTest(version=version,case=case):self.assertTrue(run(module,case))

if __name__=='__main__':unittest.main()
