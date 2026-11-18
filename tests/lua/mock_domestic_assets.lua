-- Isolated ports; no game connection. Actual reader and queue module are loaded separately.
local S={turn=114,gold=100.25,faith=200.5,reads=0,writes=0,leader='LEADER_BAIQI',queueSize=2,hash=110}
local function forbidden()S.writes=S.writes+1;error('NO_NATIVE_WRITE')end
local B={Index=10,Hash=110,BuildingType='BUILDING_MONUMENT'}
local U={Index=5,Hash=205,UnitType='UNIT_BUILDER'}
local Mission={Index=6,Hash=206,UnitType='UNIT_MISSIONARY'}
local Apostle={Index=7,Hash=207,UnitType='UNIT_APOSTLE'}
local entries={[0]={Directive=2,BuildingType=10},[1]={Directive=1,UnitType=5,MilitaryFormationType=0}}
local q={GetSize=function()return S.queueSize end,GetCurrentProductionTypeHash=function()return S.hash end,
 GetAt=function(_,i)return entries[i]end,GetBuildingProgress=function(_,i)assert(i==10);return 7 end,
 GetBuildingCost=function(_,i)assert(i==10);return 20 end,GetTurnsLeft=function()return 2 end,
 GetUnitProgress=function()return 3 end,GetUnitCost=function()return 30 end,GetUnitCorpsCost=function()return 40 end,
 GetCurrentProductionTypeModifier=function()return 1 end,Remove=forbidden,Push=forbidden}
local citizen={IsFavoredYield=function(_,id)return id==0 end,IsDisfavoredYield=function(_,id)return id==5 end}
local city={GetID=function()return 77 end,GetOwner=function()return 0 end,GetX=function()return 10 end,GetY=function()return 19 end,
 GetPopulation=function()return 3 end,GetBuildQueue=function()return q end,GetCitizens=function()return citizen end,SetProperty=forbidden}
local function unit(id,index)
 return{GetID=function()return id end,GetOwner=function()return 0 end,GetUnitType=function()return index end,
 GetType=function()return index end,GetX=function()return 10 end,GetY=function()return 19 end,GetMovesRemaining=function()return 2 end,
 GetDamage=function()return 0 end,GetFormationUnitCount=function()return 1 end,GetBuildCharges=function()return index==5 and 3 or 0 end,
 GetReligion=function()return{GetReligionType=function()return 4 end,GetSpreadCharges=function()return 2 end}end,
 GetProperty=function()end,SetProperty=forbidden,FinishMoves=forbidden}
end
local unitMap={[111]=unit(111,5),[222]=unit(222,6),[333]=unit(333,7)}
local function collection(map)
 return{GetCount=function()local n=0;for _ in pairs(map)do n=n+1 end;return n end,
 FindID=function(_,id)return map[id]end,Members=function()return next,map,nil end}
end
local cities=collection({[77]=city});local units=collection(unitMap)
local treasury={GetGoldBalance=function()return S.gold end,ChangeGoldBalance=forbidden}
local religion={GetFaithBalance=function()return S.faith end}
local p={GetCities=function()return cities end,GetUnits=function()return units end,GetTreasury=function()return treasury end,
 GetReligion=function()return religion end,IsTurnActive=function()return true end,IsHuman=function()return true end,SetProperty=forbidden}
local config={GetLeaderTypeName=function()return S.leader end,IsHuman=function()return true end}
local target={[3]={[4]=901,[12]=902},[4]={[4]=1,[12]=2},[5]={[4]=1,[12]=0}}
local purchased={[3]=901,[8]=902}
local plot={GetIndex=function()return 903 end,GetOwner=function()return -1 end,GetX=function()return 17 end,GetY=function()return 19 end,
 GetImprovementType=function()return -1 end,GetDistrictType=function()return -1 end,SetOwner=forbidden}
local E={Game={GetLocalPlayer=function()return 0 end,GetCurrentGameTurn=function()S.reads=S.reads+1;return S.turn end,SetProperty=forbidden},
 GameConfiguration={IsAnyMultiplayer=function()return false end,IsHotseat=function()return false end},Players={[0]=p},PlayerConfigurations={[0]=config},
 GameInfo={Buildings={[10]=B,[110]=B},Units={[5]=U,[205]=U,[6]=Mission,[206]=Mission,[7]=Apostle,[207]=Apostle},Districts={},Projects={}},
 MilitaryFormationTypes={STANDARD_FORMATION=0,CORPS_FORMATION=1,ARMY_FORMATION=2},CityProductionDirectives={TRAIN=1,CONSTRUCT=2,ZONE=3,PROJECT=4},
 YieldTypes={FOOD=0,PRODUCTION=1,GOLD=2,SCIENCE=3,CULTURE=4,FAITH=5},
 CityCommandTypes={MANAGE=10,PARAM_MANAGE_CITIZEN=2},CityCommandResults={PLOTS=3,CITIZENS=4,LOCKED_CITIZENS=5},
 UI={GetInterfaceModeParameter=function(id)assert(id==2);return true end,RequestPlayerOperation=forbidden},
 CityManager={GetCommandTargets=function(c,command,params)assert(c==city and command==10 and params[2]==true);return target end,RequestCommand=forbidden,RequestOperation=forbidden},
 Map={GetCityPlots=function()return{GetPurchasedPlots=function(_,c)assert(c==city);return purchased end}end,GetPlotByIndex=function(id)assert(id==903);return plot end},
 UnitManager={RequestOperation=forbidden,RequestCommand=forbidden}}
local request={playerID=0,turn=114,expectedLeader='LEADER_BAIQI',cityIDs={77},unitIDs={111,222,333},plotIDs={903}}
return{E=E,request=request,S=S,q=q,entries=entries,city=city,cities=cities,units=units,unitMap=unitMap,treasury=treasury,religion=religion,config=config,p=p,target=target,purchased=purchased,citizen=citizen,plot=plot}
