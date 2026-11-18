
local city={GetID=function()return 196610 end,GetOwner=function()return 0 end}
local keys={x='x',y='y',manage='manage'}
local params={x=10,y=12,manage=0};local calls=0;local seen
local function pack(...)return {n=select('#',...),...}end
local m={RequestCommand=function(...)calls=calls+1;seen=pack(...);return false,nil,'tail',nil end};local old=m.RequestCommand
local a=New(m,keys);assert(calls==0 and a.Read().count==0)
local r=pack(m.RequestCommand(city,7,params,nil,9,nil));assert(calls==1 and r.n==4 and r[1]==false and r[2]==nil and r[3]=='tail'and r[4]==nil)
assert(seen.n==6 and seen[1]==city and seen[3]==params and seen[4]==nil and seen[5]==9 and seen[6]==nil)
local s=a.Read();assert(s.count==1 and s.dropped==0 and s.rows[1].metadataKnown and s.rows[1].cityID==196610 and s.rows[1].x==10 and s.rows[1].manage==0 and s.rows[1].first==false and s.rows[1].returnCount==4)
s.rows[1].cityID=0;s.rows[1]=nil;assert(a.Read().rows[1].cityID==196610)
local before=calls;local bad={GetID=function()error('bad metadata')end,GetOwner=city.GetOwner};r=pack(m.RequestCommand(bad,7,params));assert(calls==before+1 and r.n==4 and not a.Read().rows[2].metadataKnown)
r=pack(m.RequestCommand(nil,nil,nil));assert(calls==before+2 and r.n==4 and not a.Read().rows[3].metadataKnown)
for i=1,20 do m.RequestCommand(city,7,params)end;s=a.Read();assert(s.count==23 and #s.rows==16 and s.dropped==7 and calls==23)
local ok,why=a.Retire();assert(ok and why=='original_restored'and m.RequestCommand==old and a.Read().retired)
assert(a.Retire()==false);m.RequestCommand(city,7,params);assert(calls==24 and a.Read().count==23)
local e={RequestCommand=function()error('native_failure_marker')end};local b=New(e,keys);local good,err=pcall(e.RequestCommand,city,7,params);assert(not good and string.find(err,'native_failure_marker',1,true)and b.Read().count==1 and not b.Read().rows[1].returned);assert(b.Retire())
local f={RequestCommand=function()return end};local z=New(f,keys);assert(pack(f.RequestCommand(city,7,params)).n==0 and z.Read().rows[1].returnCount==0);assert(z.Retire())
local g={RequestCommand=function()return true end};local h=New(g,keys);local foreign=function()return 5 end;g.RequestCommand=foreign;local done,reason=h.Retire();assert(not done and reason=='function_replaced'and g.RequestCommand==foreign and not h.Read().retired)
return true
