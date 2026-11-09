-- Repair only an explicitly empty public standings list in Baiqi's native view.
BaiqiGPViewData={}
local function finite(v)return type(v)=="number"and v==v and v~=math.huge and v~=-math.huge end
local function integer(v)return finite(v)and v>=0 and v<=2147483647 and v%1==0 end
local function dense(list,limit)
  assert(type(list)=="table"and getmetatable(list)==nil)
  local n,high=0,0
  for k in pairs(list)do
    n=n+1;assert(n<=limit and integer(k)and k>=1 and k<=limit)
    high=math.max(high,k)
  end
  assert(n==high);return n
end
function BaiqiGPViewData.Fill(data)
  local ok,result=pcall(function()
    local id=BaiqiUIGuard.PlayerID()
    if id==nil then return false end
    assert(integer(id)and Game.GetLocalPlayer()==id and GetDisplayPlayerID()==id)
    local turn=Game.GetCurrentGameTurn();assert(integer(turn))
    assert(type(data)=="table"and getmetatable(data)==nil)
    local points=data.PointsByClass
    assert(type(points)=="table"and getmetatable(points)==nil)
    local needed,seen={},{}
    local count=0
    for row in GameInfo.GreatPersonClasses()do
      count=count+1;assert(count<=64 and integer(row.Index)and not seen[row.Index])
      seen[row.Index]=true
      local old=points[row.Index]
      if type(old)=="table"and getmetatable(old)==nil and next(old)==nil then
        local maximum=row.MaxPlayerInstances
        assert(maximum==nil or(finite(maximum)and maximum>=-1 and maximum%1==0))
        needed[#needed+1]={index=row.Index,maximum=maximum,old=old}
      end
    end
    if #needed==0 then return false end
    local majors=PlayerManager.GetAliveMajors();local n=dense(majors,64)
    assert(n>0)
    local own=assert(Players[id]);local diplomacy=assert(own:GetDiplomacy())
    local people=assert(Game.GetGreatPeople())
    local players,ids={},{};local hasOwn=false
    for i=1,n do
      local p=majors[i];local pid=p:GetID()
      assert(integer(pid)and pid<=63 and not ids[pid]);ids[pid]=true
      local localPlayer=pid==id;hasOwn=hasOwn or localPlayer
      local known=localPlayer
      if not known then known=diplomacy:HasMet(pid);assert(type(known)=="boolean")end
      local name
      if known then name=assert(PlayerConfigurations[pid]):GetCivilizationShortDescription()
      else name="LOC_DIPLOPANEL_UNMET_PLAYER"end
      assert(type(name)=="string")
      name=Locale.Lookup(name);assert(type(name)=="string")
      players[i]={id=pid,own=localPlayer,name=name,points=assert(p:GetGreatPeoplePoints())}
    end
    assert(hasOwn)
    local staged={}
    for _,cls in ipairs(needed)do
      local rows={}
      for i,p in ipairs(players)do
        local total=p.points:GetPointsTotal(cls.index)
        local rate=p.points:GetPointsPerTurn(cls.index)
        local earned=people:CountPeopleReceivedByPlayer(cls.index,p.id)
        assert(finite(total)and total>=0 and finite(rate)and rate>=0 and integer(earned))
        rows[i]={IsPlayer=p.own,MaxPlayerInstances=cls.maximum,NumInstancesEarned=earned,
          PlayerName=p.name,PointsTotal=total,PointsPerTurn=rate,PlayerID=p.id}
      end
      table.sort(rows,function(a,b)
        if a.IsPlayer~=b.IsPlayer then return a.IsPlayer end
        if a.PointsTotal~=b.PointsTotal then return a.PointsTotal>b.PointsTotal end
        return a.PlayerID<b.PlayerID
      end)
      staged[#staged+1]={class=cls,rows=rows}
    end
    assert(BaiqiUIGuard.PlayerID()==id and Game.GetLocalPlayer()==id and
      GetDisplayPlayerID()==id and Game.GetCurrentGameTurn()==turn and data.PointsByClass==points)
    for _,v in ipairs(staged)do assert(points[v.class.index]==v.class.old and next(v.class.old)==nil)end
    for _,v in ipairs(staged)do points[v.class.index]=v.rows end
    return true
  end)
  return ok and result==true
end
function BaiqiGPViewData.Install()
  if type(PopulateData)~="function"or type(GetDisplayPlayerID)~="function"then return false end
  local native=PopulateData
  PopulateData=function(data,isPast)
    native(data,isPast)
    if isPast==false then BaiqiGPViewData.Fill(data)end
  end
  return true
end
