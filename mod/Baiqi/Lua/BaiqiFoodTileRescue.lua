-- Pure policy. Food here is a prediction; only native growth is an effect receipt.
BaiqiFoodTileRescue={}
local function Plain(v)return type(v)=="table" and getmetatable(v)==nil end
local function Number(v,lo,hi)return type(v)=="number" and v==v and v>=lo and v<=hi end
local function Int(v,lo,hi)return Number(v,lo,hi) and v%1==0 end
local function ID(v)return Int(v,0,2147483647) end
function BaiqiFoodTileRescue.Plan(s)
  if not Plain(s) or not ID(s.player) or s.owner~=s.player or not ID(s.cityID)
    or not Number(s.surplus,-1000000,1000000) or s.surplus>=0
    or not Int(s.population,1,1000) or not Int(s.starvation,1,10000)
    or not Int(s.zeroFoodSpecialists,1,s.population)
    or s.favored~=true or s.disfavored~=false or s.complete~=true
    or not Int(s.mapWidth,1,512) or not Int(s.mapHeight,1,512) or not Plain(s.targets) then return nil end
  local count=0
  for k in pairs(s.targets) do
    if not Int(k,1,128) then return nil end
    count=count+1
  end
  local best,seen=nil,{}
  for i=1,count do
    local d=s.targets[i]
    if not Plain(d) or not ID(d.plotID) or seen[d.plotID] or not ID(d.owner)
      or not Int(d.x,0,s.mapWidth-1) or not Int(d.y,0,s.mapHeight-1)
      or not ID(d.sourceCityID) or not Int(d.sourcePopulation,1,1000)
      or not Number(d.food,0,1000000) or not Number(d.sourceSurplus,-1000000,1000000)
      or not Int(d.district,-1,65535) or not Int(d.improvement,-1,65535)
      or not Int(d.sourceDistance,0,1024) or not Int(d.targetDistance,0,1024)
      or type(d.sourceManageHasPlot)~="boolean" or type(d.sourceManageComplete)~="boolean"
      or type(d.visible)~="boolean" or type(d.revealed)~="boolean" or type(d.nativeAllowed)~="boolean"
      or (d.sourceWorked~=nil and not Int(d.sourceWorked,-1,256))
      or (d.sourceLocked~=nil and not Int(d.sourceLocked,-1,256)) then return nil end
    seen[d.plotID]=true
    if d.owner==s.player and d.sourceCityID~=s.cityID and d.nativeAllowed
      and d.visible and d.revealed and d.district==-1 and d.food>0
      and d.targetDistance<=3 and d.sourceDistance>3 and d.sourceManageComplete
      and not d.sourceManageHasPlot and d.sourceWorked==nil and d.sourceLocked==nil
      and s.surplus+d.food>=0
      and (not best or d.food<best.food or (d.food==best.food and d.plotID<best.plotID)) then best=d end
  end
  if best then return {cityID=s.cityID,sourceCityID=best.sourceCityID,plotID=best.plotID,
    x=best.x,y=best.y,expectedFood=best.food,expectedSurplus=s.surplus+best.food} end
end
return BaiqiFoodTileRescue
