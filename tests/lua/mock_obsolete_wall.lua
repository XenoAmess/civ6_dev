-- Adapter inputs reproduce the inactive wall shape; this is not engine evidence.
local w=TestWorld
w.blockedKnown=false;w.blockedAllowed=false;w.blockedPillaged=false
w.steelKnown=true;w.wallTechKnown=true;w.centerKnown=true;w.centerPillaged=false
w.centerComplete=true;w.centerID=808;w.centerOwner=7;w.centerType=0
local wall=GameInfo.Buildings[25]
wall.BuildingType='BUILDING_STAR_FORT';wall.PrereqDistrict='DISTRICT_CITY_CENTER'
wall.PrereqTech='TECH_SIEGE_TACTICS';wall.IsWonder=false;wall.MustPurchase=false
wall.RequiresPlacement=false;wall.OuterDefenseHitPoints=100;wall.OuterDefenseStrength=3
w.wallDefinition=wall
local center={Index=0,Hash=444,DistrictType='DISTRICT_CITY_CENTER'}
GameInfo.Districts[0]=center;GameInfo.Districts[444]=center
GameInfo.Districts.DISTRICT_CITY_CENTER=center;w.centerDefinition=center
local steel={Index=45,Hash=-1438095361,TechnologyType='TECH_STEEL'}
local siege={Index=40,Hash=140,TechnologyType='TECH_SIEGE_TACTICS'}
GameInfo.Technologies={TECH_STEEL=steel,[45]=steel,TECH_SIEGE_TACTICS=siege,[40]=siege}
w.steelDefinition=steel
Players[7].GetTechs=function()return {HasTech=function(_,i)
 if w.throwWallTech then error('technology unavailable')end
 if i==45 then return w.steelKnown elseif i==40 then return w.wallTechKnown end
end}end
w.steelLink={TechnologyType='TECH_STEEL',ModifierId='STEEL_UNLOCK_URBAN_DEFENSES'}
GameInfo.TechnologyModifiers=setmetatable({}, {__call=function()
 local i=0;return function()i=i+1;if i==1 then return w.steelLink end end
end})
w.steelModifier={ModifierId='STEEL_UNLOCK_URBAN_DEFENSES',ModifierType='MODIFIER_PLAYER_GRANT_CITIES_URBAN_DEFENSES'}
w.steelDynamic={ModifierType='MODIFIER_PLAYER_GRANT_CITIES_URBAN_DEFENSES',CollectionType='COLLECTION_OWNER',EffectType='EFFECT_ADJUST_CITIES_HAS_URBAN_DEFENSES'}
GameInfo.Modifiers={STEEL_UNLOCK_URBAN_DEFENSES=w.steelModifier}
GameInfo.DynamicModifiers={MODIFIER_PLAYER_GRANT_CITIES_URBAN_DEFENSES=w.steelDynamic}
local plots={};local oldPlot=Map.GetPlot
local function bind(city)
 local x,y=city:GetX(),city:GetY()
 local plot={GetX=function()return x end,GetY=function()return y end,
  GetOwner=function()return w.centerOwner end,GetDistrictType=function()return w.centerType end,
  GetDistrictID=function()return w.centerID end,IsCity=function()return true end}
 plots[#plots+1]=plot
 local gd=city.GetDistricts
 city.GetDistricts=function()
  local ds=gd();local has,pill=ds.HasDistrict,ds.IsPillaged
  ds.HasDistrict=function(self,i,...)if i==0 then return w.centerKnown end;return has(self,i,...)end
  ds.IsPillaged=function(self,i)if i==0 then return w.centerPillaged end;return pill(self,i)end
  local component={GetID=function()return w.centerID end,GetType=function()return w.centerType end,
   GetX=function()return x end,GetY=function()return y end,
   IsComplete=function()return w.centerComplete end,IsPillaged=function()return w.centerPillaged end}
  ds.Members=function()local a=w.duplicateCenter and {component,component}or{component};return ipairs(a)end
  return ds
 end
end
for _,city in ipairs(w.cities)do bind(city)end
Map.GetPlot=function(x,y)
 for _,p in ipairs(plots)do if p:GetX()==x and p:GetY()==y then return p end end
 return oldPlot(x,y)
end
