from pathlib import Path
import os
from missionary_purchase_core_harness import make_missionary_core

FIXTURE='''
B={id=0,index=0,owner=0,type=0,x=15,y=13,complete=true,pillaged=false,cityID=65536,cityOwner=0,plotID=0,plotOwner=0,plotType=0,cityReads=0}
local holy={Index=0,DistrictType='DISTRICT_HOLY_SITE'}
GameInfo.Districts={DISTRICT_HOLY_SITE=holy,[0]=holy}
local dc={GetID=function()return B.cityID end,GetOwner=function()return B.cityOwner end,GetX=function()return S.x end,GetY=function()return S.y end}
local district={GetID=function()return B.id end,GetOwner=function()return B.owner end,GetType=function()return B.type end,GetX=function()return B.x end,GetY=function()return B.y end,IsComplete=function()return B.complete end,IsPillaged=function()return B.pillaged end,GetCity=function()B.cityReads=B.cityReads+1;if B.onCity then B.onCity()end;return dc end}
local ds={GetDistrict=function(self,index)assert(index==0);if B.throw then error('native unavailable')end;if B.absent then return nil end;return district end}
City.GetDistricts=function()return ds end
Map={GetPlot=function(x,y)assert(x==B.x and y==B.y);return {GetOwner=function()return B.plotOwner end,GetDistrictType=function()return B.plotType end,GetDistrictID=function()return B.plotID end}end}
function HolyEffect()H.Add(6000000);H.newUnit.x=15;H.newUnit.y=13;S.faith=100 end
'''


def make():
    override=os.environ.get('BAIQI_BIRTH_INTENT')
    source=Path(override).read_text(encoding='utf-8') if override else None
    lua=make_missionary_core(source=source)
    lua.execute(FIXTURE)
    return lua
