-- Read-only placement evidence for research planning; no operation permission.
BaiqiPowerSitesCore={}
local M=BaiqiPowerSitesCore
local allowed={IMPROVEMENT_SOLAR_FARM=true,IMPROVEMENT_WIND_FARM=true,
  IMPROVEMENT_GEOTHERMAL_PLANT=true,IMPROVEMENT_OFFSHORE_WIND_FARM=true}
local function Integer(v,lo,hi)
  return type(v)=='number'and v==v and v%1==0 and v>=lo and v<=hi
end
function M.Create(config,E)
  if type(config)~='table'or type(config.leader)~='string'or config.leader==''or type(E)~='table'then return nil end
  local function CanHave(pid,turn,plotID,cityID,kind)
    local ok,result=pcall(function()
      assert(Integer(pid,0,2147483647)and Integer(turn,0,2147483647)
        and Integer(plotID,0,262143)and Integer(cityID,0,2147483647)and allowed[kind]==true)
      local function Snapshot()
        assert(E.Game.GetLocalPlayer()==pid and E.Game.GetCurrentGameTurn()==turn)
        local player=assert(E.Players[pid]);local cfg=assert(E.PlayerConfigurations[pid])
        assert(player:IsHuman()==true and cfg:GetLeaderTypeName()==config.leader and player:IsTurnActive()==true)
        assert(E.GameConfiguration.IsAnyMultiplayer()==false
          and(not E.GameConfiguration.IsHotseat or E.GameConfiguration.IsHotseat()==false))
        local team=player:GetTeam();assert(Integer(team,0,2147483647))
        local plot=assert(E.Map.GetPlotByIndex(plotID));local x,y=plot:GetX(),plot:GetY()
        assert(plot:GetIndex()==plotID and plot:GetOwner()==pid and Integer(x,0,511)and Integer(y,0,511))
        local vis=assert(E.PlayersVisibility[pid])
        assert(vis:IsVisible(x,y)==true and vis:IsRevealed(x,y)==true)
        local city=assert(E.Cities.GetPlotPurchaseCity(plot));local cx,cy=city:GetX(),city:GetY()
        assert(city:GetID()==cityID and city:GetOwner()==pid and Integer(cx,0,511)and Integer(cy,0,511))
        assert(vis:IsVisible(cx,cy)==true and vis:IsRevealed(cx,cy)==true)
        local imp=assert(E.GameInfo.Improvements[kind])
        assert(imp.ImprovementType==kind and Integer(imp.Index,0,4095)
          and Integer(imp.Hash,-2147483648,2147483647)and type(imp.PrereqTech)=='string'and imp.PrereqTech~='')
        local engine=E.ImprovementBuilder.CanHaveImprovement;assert(type(engine)=='function')
        return {player=player,team=team,plot=plot,city=city,x=x,y=y,cx=cx,cy=cy,
          index=imp.Index,hash=imp.Hash,prereq=imp.PrereqTech,engine=engine}
      end
      local before=Snapshot()
      local value=before.engine(before.plot,before.index,before.team)
      if type(value)~='boolean'then return nil end
      local after=Snapshot()
      for _,key in ipairs({'player','team','plot','city','x','y','cx','cy','index','hash','prereq','engine'})do
        if before[key]~=after[key]then return nil end
      end
      return value
    end)
    if ok then return result end
  end
  return {marker='baiqi-power-sites-v1',version=1,CanHave=CanHave}
end
return M
