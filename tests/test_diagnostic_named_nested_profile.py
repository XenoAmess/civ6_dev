"""Actual named-root helper, with the canonical nested contracts inherited."""
from pathlib import Path
import unittest
import test_diagnostic_nested_profile as baseline

ROOT=Path(__file__).resolve().parents[1]


class NamedNestedProfileTests(baseline.NestedProfileTests):
    candidate_source=None

    def setUp(self):
        raw=self.candidate_source
        if raw is None:raw=(ROOT/'tools/lua/diagnostic_named_nested_profile.lua').read_text(encoding='utf-8')
        self.candidate_source='local New=(function()\n'+raw+"\nend)()\nreturn function(a,b,c,d)return New(a,b,c,d,'Admin.Run')end"
        super().setUp()
        self.lua.globals().NewNamed=self.lua.execute(raw)

    def test_child_outside_root_and_reserved_label(self):
        self.lua.execute('''
local child=h.WrapChild('ReadBack',function()T.bodies=T.bodies+1;return false,nil end)
h.SetEnabled(true);child();assert(T.bodies==1 and #h.profile.samples==0)
assert(not pcall(h.WrapChild,'Admin.Run',function()end))
h.errors=1;h.SetEnabled(false);assert(not h.SetEnabled(true)and not h.enabled)
''')

    def test_invalid_label_rejected_before_profile_factory(self):
        self.lua.execute('''
local calls=0;local factory=function(...)calls=calls+1;return NewProfile(...)end
local function reject(label)assert(not pcall(NewNamed,factory,WrapChild,Now,Qualify,label)and calls==0)end
reject(nil)
for _,label in ipairs({false,true,0,141,'','admin.Run','Admin.Run ','Unknown'})do reject(label)end
''')

    def test_admin_and_controller_labels_are_bound_at_measurement(self):
        self.lua.execute('''
for _,label in ipairs({'Admin.Run','Controller.RunNow'})do
 local a=NewNamed(NewProfile,WrapChild,Now,Qualify,label);assert(a.SetEnabled(true))
 local child=a.WrapChild('Research',function()return false,nil end)
 local root=a.WrapRoot(function()return child()end);local x,y=root()
 assert(x==false and y==nil and #a.profile.samples==2)
 assert(a.profile.samples[1].name=='Research'and a.profile.samples[2].name==label)
 assert(a.profile.samples[1].rootId==a.profile.samples[2].rootId)
 assert(not pcall(a.WrapChild,label,function()end))
 assert(a.SetEnabled(false));a.retired=true;assert(not a.SetEnabled(true))
 root();assert(#a.profile.samples==2)
end
''')


if __name__=='__main__':unittest.main()
