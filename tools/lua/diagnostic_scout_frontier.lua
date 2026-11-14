-- Read-only fixture discovery, never a move or settlement authorization.
return function(E)
  local out={status='UNKNOWN',complete=false,inspected_units=0,rows={}}
  local seen={}
  local function Finite(v) return type(v)=='number' and v==v and v>-math.huge and v<math.huge end
  local function Integer(v) assert(Finite(v) and v>=0 and v%1==0,'Unknown geometry/identity');return v end
  local function Boolean(v) assert(type(v)=='boolean','Unknown flag');return v end
  local function Pack(...) return {n=select('#',...),...} end
  local function Scan()
    assert(E.Game.GetLocalPlayer()==0 and E.GameConfiguration.IsAnyMultiplayer()==false
      and E.GameConfiguration.IsHotseat()==false,'Unknown context')
    local player=E.Players[0];local config=E.PlayerConfigurations[0]
    assert(player:IsTurnActive()==true and config:IsHuman()==true
      and config:GetLeaderTypeName()=='LEADER_BAIQI','Wrong active player')
    local visibility=assert(E.PlayersVisibility[0])
    for _,unit in player:GetUnits():Members() do
      if out.inspected_units==256 then return 'PARTIAL_LIMIT' end
      out.inspected_units=out.inspected_units+1
      local owner=Integer(unit:GetOwner())
      if owner==0 then
        local kind=Integer(unit:GetUnitType());local def=assert(E.GameInfo.Units[kind],'Unknown unit definition')
        assert(type(def.UnitType)=='string','Unknown unit kind')
        if def.UnitType=='UNIT_SCOUT' or def.UnitType=='UNIT_RANGER' then
          local dead=Boolean(unit:IsDead());local delayed=Boolean(unit:IsDelayedDeath())
          local formation=Integer(unit:GetFormationUnitCount())
          local moves=unit:GetMovesRemaining();assert(Finite(moves),'Unknown moves')
          local readyM=Boolean(unit:IsReadyToMove());local readyS=Boolean(unit:IsReadyToSelect())
          local pending=Boolean(unit:HasPendingOperations())
          local queued=Pack(E.UnitManager.GetQueuedDestination(unit))
          assert(queued.n==1,'Unknown queue arity')
          if queued[1]~=nil then Integer(queued[1]) end
          if not dead and not delayed and formation==1 and moves>0 and readyM and readyS
            and not pending and queued[1]==nil then
            local id=Integer(unit:GetID());local ux=Integer(unit:GetX());local uy=Integer(unit:GetY())
            for direction=0,5 do
              local plot=E.Map.GetAdjacentPlot(ux,uy,direction)
              if plot~=nil then
                local index=Integer(plot:GetIndex());local x=Integer(plot:GetX());local y=Integer(plot:GetY())
                local revealed=Boolean(visibility:IsRevealed(x,y))
                local key=id..':'..index
                if not revealed and not seen[key] then
                  if #out.rows==64 then return 'PARTIAL_LIMIT' end
                  seen[key]=true
                  out.rows[#out.rows+1]={unit_id=id,unit_type=kind,unit_x=ux,unit_y=uy,
                    plot_index=index,x=x,y=y,direction=direction}
                end
              end
            end
          end
        end
      end
    end
    return 'COMPLETE'
  end
  local ok,status=pcall(Scan)
  if ok then out.status=status;out.complete=status=='COMPLETE' end
  table.sort(out.rows,function(a,b)
    if a.unit_id~=b.unit_id then return a.unit_id<b.unit_id end
    return a.plot_index<b.plot_index
  end)
  return out
end
