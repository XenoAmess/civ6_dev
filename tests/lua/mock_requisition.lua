include=function() end
TestCapture={turn=8,gold=1000,moves=2,owner=3,hp=200,damage=150,outer=0,outerDamage=0,
 population=2,atWar=true,visible=true,leader='LEADER_BAIQI',transferCalls=0,charges=0,finishCalls=0,props={},unitProps={},
 failTransfer=false,throwAfterTransfer=false,failCharge=false,formation=1,active=true,localPlayer=7,
 gameProps={},sourceProps={},recipientProps={},granary=true,pillaged=false,recipientOwner=7,extraModifier=false}
local w=TestCapture
local unit={GetID=function() return w.unitID or 9 end,GetOwner=function() return 7 end,GetType=function() return 0 end,
 GetFormationUnitCount=function() return w.formation end,GetMovesRemaining=function() return w.moves end,
 GetX=function() return 2 end,GetY=function() return 2 end,
 IsDead=function() return false end,IsDelayedDeath=function() return false end,
 GetProperty=function(_,key) return w.unitProps[key] end,SetProperty=function(_,key,val) w.unitProps[key]=val end}
local buildings={HasBuilding=function() return w.granary end,IsPillaged=function() return w.pillaged end}
local city={GetOwner=function() return w.owner end,GetID=function() return w.cityID or 12 end,GetX=function() return 3 end,
 GetY=function() return 2 end,GetPopulation=function() return w.population end,
 GetBuildings=function() return buildings end,GetName=function() return 'Source' end}
local recipient={GetOwner=function() return w.recipientOwner end,GetID=function() return 20 end,
 GetX=function() return 8 end,GetY=function() return 8 end,GetName=function() return 'Recipient' end}
local district={GetID=function() return w.districtID or 13 end,GetMaxDamage=function(_,kind) return kind==0 and w.hp or w.outer end,
 GetDamage=function(_,kind) return kind==0 and w.damage or w.outerDamage end}
city.GetDistricts=function() return {GetDistrict=function() return district end} end
local treasury={GetGoldBalance=function() return w.gold end,
 ChangeGoldBalance=function(_,n) w.charges=w.charges+1;if w.failCharge then error('charge failed') end; w.gold=w.gold+n end}
local player={IsHuman=function() return true end,IsTurnActive=function() return w.active end,GetUnits=function() return {FindID=function(_,id) if id==9 then return unit end end} end,
 GetCities=function() return {Members=function() return ipairs({recipient}) end,
  FindID=function(_,id) if id==20 then return recipient end end} end,
 GetTreasury=function() return treasury end,GetDiplomacy=function() return {IsAtWarWith=function(_,id) return id==3 and w.atWar end} end,
 GetProperty=function(_,key) return w.props[key] end,SetProperty=function(_,key,val) w.props[key]=val end}
local enemy={GetCities=function() return {FindID=function(_,id) if id==12 and w.owner==3 then return city end end} end,
 GetDistricts=function() return {FindID=function(_,id) if id==13 then return district end end} end}
Players={[7]=player,[3]=enemy}
PlayerConfigurations={[7]={GetLeaderTypeName=function() return w.leader end}}
PlayersVisibility={[7]={IsVisible=function() return w.visible end}}
Game={GetCurrentGameTurn=function() return w.turn end,GetLocalPlayer=function() return w.localPlayer end,
 GetProperty=function(key) return w.gameProps[key] end,SetProperty=function(key,value) w.gameProps[key]=value end}
GameConfiguration={IsAnyMultiplayer=function() return false end}
GameInfo={Units={[0]={Domain='DOMAIN_LAND',PromotionClass='PROMOTION_CLASS_MELEE'}}}
GameInfo.Districts={DISTRICT_CITY_CENTER={Index=0}}
GameInfo.Buildings={BUILDING_GRANARY={Index=0,BuildingType='BUILDING_GRANARY',Housing=2,Maintenance=0}}
local function Rows(rows)
 local i=0
 return function() i=i+1;return rows[i] end
end
GameInfo.Building_YieldChanges=function() return Rows({{BuildingType='BUILDING_GRANARY',YieldType='YIELD_FOOD',YieldChange=1}}) end
GameInfo.BuildingModifiers=function()
 local list={{BuildingType='BUILDING_GRANARY',ModifierId='BAIQI_GRANARY_OUT_FOOD'},
 {BuildingType='BUILDING_GRANARY',ModifierId='BAIQI_GRANARY_OUT_HOUSING'}}
 if w.extraModifier then list[#list+1]={BuildingType='BUILDING_GRANARY',ModifierId='OTHER_MOD_EFFECT'} end
 return Rows(list)
end
DefenseTypes={DISTRICT_GARRISON=0,DISTRICT_OUTER=1}
Map={GetPlotDistance=function() return 1 end}
Map.GetGridSize=function() return 44,26 end
local function Plot(index,x,y,props)
 return {GetIndex=function() return index end,GetX=function() return x end,GetY=function() return y end,
 GetProperty=function(_,key) return props[key] end,SetProperty=function(_,key,val) props[key]=val end}
end
local sourcePlot,recipientPlot=Plot(100,3,2,w.sourceProps),Plot(200,8,8,w.recipientProps)
local actorPlot=Plot(99,2,2,{})
Map.GetPlot=function(x,y) if x==2 and y==2 then return actorPlot elseif x==3 and y==2 then return sourcePlot elseif x==8 and y==8 then return recipientPlot end end
Map.GetPlotByIndex=function(index) if index==99 then return actorPlot elseif index==100 then return sourcePlot elseif index==200 then return recipientPlot end end
Map.GetPlotCount=function() return 201 end
Map.GetAdjacentPlot=function(x,y,dir) if dir==0 then return sourcePlot end end
CityManager={GetCityAt=function(x,y) if x==3 and y==2 then return city elseif x==8 and y==8 then return recipient end end,
 TransferCity=function(c,pid)
  w.transferCalls=w.transferCalls+1
  if w.failTransfer then error('failed transfer') end
  w.owner=pid
  if w.throwAfterTransfer then error('transfer result unknown') end
 end}
UnitManager={FinishMoves=function(u) w.finishCalls=w.finishCalls+1;w.moves=0 end}
function TestParams()
 local q=BaiqiRequisition.Quote(7,9,3,12)
 if not q then error('fixture quote invalid') end
 q.confirmed=true;q.requestID=BaiqiRequisition.RequestID(q)
 return q
end
function TestUI()
 w.requests={}
 UI={GetHeadSelectedUnit=function() return unit end,
  RequestPlayerOperation=function(pid,op,params) w.requests[#w.requests+1]=params end}
 PlayerOperations={EXECUTE_SCRIPT=7}
 Locale={Lookup=function(text) return text end}
 PopupDialogInGame={new=function()
  local popup={AddText=function(_,text) w.popupText=text end,
   AddConfirmButton=function(_,text,cb) w.confirm=cb end,
   AddCustomButton=function(_,text,cb) w.normalAttack=cb end,
   AddCancelButton=function(_,text,cb) w.cancel=cb end,Open=function() w.opened=true end}
  return popup
 end}
end
w.objects={unit=unit,city=city,district=district,player=player,enemy=enemy}
