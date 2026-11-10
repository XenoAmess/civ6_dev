from pathlib import Path
import unittest
from lupa.lua51 import LuaRuntime

SOURCE = (Path(__file__).resolve().parents[1] / 'tools/lua/diagnostic_move_queue.lua').read_text(encoding='utf-8')
FIXTURE = '''
W={calls=0,order={},snapshot={id=1,owner=0,unitType='UNIT_BUILDER',moves=1},result={n=3,[1]=false,[3]=7}}
actor={};W.manager={GetQueuedDestination=function(...)
 W.calls=W.calls+1;W.args={n=select('#',...),...};W.order[#W.order+1]='original'
 if W.failOriginal then error('native-error',0)end
 return unpack(W.result,1,W.result.n)
end};W.original=W.manager.GetQueuedDestination
o={getManager=function()return W.manager end,getPublished=function()return W.published end,
 publish=function(v)W.published=v end,unpack=unpack,
 scope=function()W.order[#W.order+1]='scope';if W.failScope then error('scope-error')end;return 206 end,
 snapshot=function()W.order[#W.order+1]='snapshot';if W.failSnapshot then error('snapshot-error')end;return W.snapshot end}
'''


class MoveQueueDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime()
        self.lua.execute(FIXTURE)
        self.lua.globals().M = self.lua.execute(SOURCE)

    def test_forwarding_arity_order_and_snapshot_copy(self):
        self.lua.execute('''
        h=M.Install(o);assert(W.calls==0)
        local a,b,c=W.manager.GetQueuedDestination(actor,nil,'tail')
        assert(a==false and b==nil and c==7 and W.calls==1 and W.args.n==3)
        assert(W.args[1]==actor and W.args[2]==nil and W.args[3]=='tail')
        assert(table.concat(W.order,',')=='original,scope,snapshot')
        W.snapshot.moves=9
        assert(h.samples[1].snapshot.moves==1 and h.samples[1].returnCount==3)
        assert(h.samples[1].values[1]==false and h.samples[1].valueTypes[2]=='nil')
        assert(h.Restore()and W.manager.GetQueuedDestination==W.original and W.published==nil)
        ''')

    def test_original_and_diagnostic_exceptions_preserve_original_behavior(self):
        self.lua.execute('''
        h=M.Install(o);W.failOriginal=true
        local ok,e=pcall(W.manager.GetQueuedDestination,actor)
        assert(not ok and e=='native-error'and h.calls==1 and h.errors==0 and #h.samples==0)
        W.failOriginal=false;W.result={n=0}
        assert(select('#',W.manager.GetQueuedDestination(actor))==0 and #h.samples==1)
        W.result={n=3,[1]=false,[3]=7};W.failScope=true
        local a,b,c=W.manager.GetQueuedDestination(actor)
        assert(a==false and b==nil and c==7 and h.errors==1)
        W.failScope=false;W.failSnapshot=true
        assert(W.manager.GetQueuedDestination(actor)==false and h.errors==2)
        W.failSnapshot=false;W.manager.GetQueuedDestination(actor)
        assert(#h.samples==2 and h.calls==5 and W.calls==5)
        ''')

    def test_reentrant_scope_and_snapshot_do_not_recurse_diagnostics(self):
        self.lua.execute('''
        o.snapshot=function()W.manager.GetQueuedDestination(actor);return W.snapshot end
        h=M.Install(o);assert(W.manager.GetQueuedDestination(actor)==false)
        assert(W.calls==2 and h.calls==2 and h.reentrant==1 and #h.samples==1)
        o.scope=function()W.manager.GetQueuedDestination(actor);return 206 end
        o.snapshot=function()return W.snapshot end
        W.manager.GetQueuedDestination(actor)
        assert(W.calls==4 and h.reentrant==2 and #h.samples==2 and h.errors==0)
        ''')

    def test_invalid_snapshot_and_scope_never_change_return_values(self):
        self.lua.execute('''
        h=M.Install(o)
        local bad={
         {id=1,owner=0,unitType='UNIT_BUILDER',nested={}},
         {id=1,owner=0,unitType='UNIT_BUILDER',moves=0/0},
         {id=1,owner=0,unitType='UNIT_BUILDER',callback=function()end},
         {id=1.5,owner=0,unitType='UNIT_BUILDER'},
         {id=1,owner=1,unitType='UNIT_BUILDER'},
         setmetatable({id=1,owner=0,unitType='UNIT_BUILDER'},{})}
        bad[#bad+1]={id=1,owner=0,unitType='UNIT_BUILDER',[string.rep('x',65)]=1}
        local many={id=1,owner=0,unitType='UNIT_BUILDER'}
        for i=1,30 do many['x'..i]=i end;bad[#bad+1]=many
        for _,s in ipairs(bad)do W.snapshot=s;local a,b,c=W.manager.GetQueuedDestination(actor);assert(a==false and b==nil and c==7)end
        assert(h.errors==#bad and #h.samples==0 and W.calls==#bad)
        o.scope=function()return 'bad-turn'end
        W.manager.GetQueuedDestination(actor);assert(h.errors==#bad+1)
        o.scope=function()return nil end
        W.manager.GetQueuedDestination(actor);assert(h.ignored==1)
        o.scope=function()return 206 end;o.snapshot=function()return nil end
        W.manager.GetQueuedDestination(actor);assert(h.ignored==2)
        ''')

    def test_capacity_and_unknown_results_keep_original_shapes(self):
        self.lua.execute('''
        o.maxRecords=2;h=M.Install(o)
        for i=1,5 do assert(W.manager.GetQueuedDestination(actor)==false)end
        assert(#h.samples==2 and h.drops==3 and W.calls==5);h.Restore()
        o.maxRecords=nil;h=M.Install(o);local unknown={}
        W.result={n=6,[1]=false,[3]=unknown,[4]=math.huge,[5]=7,[6]='tail'}
        local a,b,c,d,e,f=W.manager.GetQueuedDestination(actor)
        assert(a==false and b==nil and c==unknown and d==math.huge and e==7 and f=='tail')
        local r=h.samples[1]
        assert(r.returnCount==6 and r.truncated and r.nonScalarReturn)
        assert(r.valueTypes[2]=='nil'and r.valueTypes[3]=='table'and r.valueTypes[4]=='number')
        assert(r.values[3]==nil and r.values[4]==nil and r.values[5]==nil and h.errors==0)
        ''')

    def test_install_preflight_and_partial_publication_rollback(self):
        self.lua.execute('''
        for _,v in ipairs({0,1.5,false,0/0,math.huge,4097})do
         o.maxRecords=v;assert(not pcall(M.Install,o));assert(W.manager.GetQueuedDestination==W.original and W.published==nil)
        end
        o.maxRecords=nil;W.published={};assert(not pcall(M.Install,o));W.published=nil
        local publish=o.publish
        o.publish=function(v)if v~=nil then W.published=v;error('publish-error')else W.published=nil end end
        assert(not pcall(M.Install,o));assert(W.manager.GetQueuedDestination==W.original and W.published==nil)
        local foreign=function()return 'foreign'end;local ns={}
        o.publish=function(v)W.manager.GetQueuedDestination=foreign;W.published=ns;error('foreign-publication')end
        assert(not pcall(M.Install,o));assert(W.manager.GetQueuedDestination==foreign and W.published==ns and W.calls==0)
        ''')

    def test_restore_rejects_foreign_table_namespace_and_binding(self):
        self.lua.execute('''
        h=M.Install(o);local wrapper=W.manager.GetQueuedDestination;local manager=W.manager
        o.getManager=function()return{}end
        assert(not pcall(h.Restore)and manager.GetQueuedDestination==wrapper)
        o.getManager=function()return manager end
        local foreign={};W.published=foreign
        assert(not pcall(h.Restore)and W.published==foreign and manager.GetQueuedDestination==wrapper)
        W.published=h;local other=function()return 'other'end;manager.GetQueuedDestination=other
        assert(not pcall(h.Restore)and manager.GetQueuedDestination==other and W.published==h)
        manager.GetQueuedDestination=wrapper;assert(h.Restore()and h.restored and W.calls==0)
        ''')

    def test_restore_publication_failure_allows_owned_retry(self):
        self.lua.execute('''
        h=M.Install(o);local wrapper=W.manager.GetQueuedDestination;local publish=o.publish
        o.publish=function(v)if v==nil then error('remove-error')else publish(v)end end
        assert(not pcall(h.Restore)and W.manager.GetQueuedDestination==wrapper and W.published==h)
        o.publish=publish;assert(h.Restore()and W.manager.GetQueuedDestination==W.original and W.published==nil)
        ''')


if __name__ == '__main__':
    unittest.main()
