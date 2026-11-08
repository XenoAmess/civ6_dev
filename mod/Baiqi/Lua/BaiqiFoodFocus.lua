BaiqiFoodFocus={}
function BaiqiFoodFocus.Plan(s)
  if type(s)~="table" then return nil end
  if getmetatable(s)~=nil then return nil end
  local p=s.player
  local o=s.owner
  local c=s.cityID
  local sur=s.surplus
  local fav=s.favored
  local dis=s.disfavored
  if type(p)~="number" or type(o)~="number" or type(c)~="number" then return nil end
  if p~=o then return nil end
  if p<0 or p>2147483647 or c<0 or c>2147483647 then return nil end
  if math.floor(p)~=p or math.floor(o)~=o or math.floor(c)~=c then return nil end
  if type(sur)~="number" or sur~=sur or sur==math.huge or sur==-math.huge then return nil end
  if sur<-1000000 or sur>1000000 then return nil end
  if type(fav)~="boolean" or type(dis)~="boolean" then return nil end
  if fav and dis then return nil end
  if sur>=0 or fav then return nil end
  if dis then
    return {cityID=c,mode="UNIGNORE",flags=1,data0=0}
  end
  return {cityID=c,mode="FAVOR",flags=0,data0=1}
end
return BaiqiFoodFocus
