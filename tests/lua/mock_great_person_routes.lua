-- Consumer fixture only; native path results follow a small visible grid.
local w=TestWorld
w.routeQueries={};w.routeBlocked={};w.routeOwners={}
local originalCity=w.objects.city
local originalByIndex=Map.GetPlotByIndex
local originalGetPlot=Map.GetPlot
function w.SetRouteSites(specs)
 local targets={};local byIndex,byXY={},{}
 local function key(x,y)return x..':'..y end
 for _,s in ipairs(specs)do targets[key(s[2],s[3])]=s[1]end
 for x=0,12 do for y=0,12 do
  local index=(x==2 and y==3)and 42 or targets[key(x,y)]or 600+x+y*20
  local px,py,pi=x,y,index
  local p={GetIndex=function()return pi end,GetX=function()return px end,GetY=function()return py end,
   GetOwner=function()return w.routeOwners[pi]or 7 end}
  byIndex[index]=p;byXY[key(x,y)]=p
 end end
 Map.GetPlotByIndex=function(i)return byIndex[i]or originalByIndex(i)end
 Map.GetPlot=function(x,y)return byXY[key(x,y)]or originalGetPlot(x,y)end
 Map.GetPlotDistance=function(x,y,a,b)return math.max(math.abs(x-a),math.abs(y-b),math.abs((x-a)+(y-b)))end
 local cities={}
 for i,s in ipairs(specs)do
  local id,index,x,y=65+i,s[1],s[2],s[3]
  local district={GetType=function()return 7 end,GetX=function()return x end,GetY=function()return y end,
   IsComplete=function()return w.completed end,IsPillaged=function()return w.pillaged or false end}
  cities[#cities+1]=setmetatable({GetID=function()return id end,GetX=function()return x end,GetY=function()return y end,
   GetDistricts=function()return{HasDistrict=function(_,kind,complete)assert(kind==7 and complete==true);return w.completed end,
    Members=function()return ipairs({district})end}end},{__index=originalCity})
 end
 w.objects.player.GetCities=function()return{Members=function()return ipairs(cities)end,GetCount=function()return #cities end,
  FindID=function(_,id)for _,c in ipairs(cities)do if c:GetID()==id then return c end end end}end
 UnitManager.GetMoveToPathEx=function(unit,index)
  w.routeQueries[#w.routeQueries+1]=index
  if w.routeBlocked[index]then return nil end
  local start=Map.GetPlot(unit:GetX(),unit:GetY()):GetIndex()
  local queue,head,previous={start},1,{[start]=false}
  while queue[head]do
   local here=queue[head];head=head+1
   if here==index then break end
   local p=byIndex[here]
   for _,delta in ipairs({{1,0},{0,1},{-1,0},{0,-1}})do
    local n=byXY[key(p:GetX()+delta[1],p:GetY()+delta[2])]
    local k=n and n:GetIndex()
    if k and previous[k]==nil and not w.routeBlocked[k]then previous[k]=here;queue[#queue+1]=k end
   end
  end
  if previous[index]==nil then return nil end
  local route={index};while route[1]~=start do table.insert(route,1,previous[route[1]])end
  return{plots=route}
 end
end
w.SetRouteSites({{45,8,3},{44,2,7},{43,3,3}})
