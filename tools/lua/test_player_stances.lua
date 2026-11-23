-- TEST_PLAYER only. Never install this helper in the mod or bind it to BACKGROUND.
-- FORTIFY/SLEEP are fresh player stance choices, never a disguised SKIP_TURN replay.
return function(turn,limit,state,action)
  assert(type(turn)=='number'and turn%1==0 and type(limit)=='number'and limit%1==0 and limit>0 and limit<=64)
  assert(type(state)=='table'and type(state.attempts)=='table')
  local function allowed()
    local rows=GameInfo and GameInfo.UnitOperations
    local fortify=rows and rows.UNITOPERATION_FORTIFY
    local sleep=rows and rows.UNITOPERATION_SLEEP
    return type(action)=='number'and action==action and action>-math.huge and action<math.huge and action%1==0
      and((fortify and fortify.Hash==action)or(sleep and sleep.Hash==action))
  end
  assert(allowed(),'Only original FORTIFY/SLEEP operations are accepted')
  local report={submitted=0,scanned=0,phaseStopped=false,nativeError=false}
  local function phase()
    return Game.GetCurrentGameTurn()==turn and Game.GetLocalPlayer()==0
      and PlayerConfigurations[0]:IsHuman()==true and PlayerConfigurations[0]:GetLeaderTypeName()=='LEADER_BAIQI'
      and GameConfiguration.IsAnyMultiplayer()==false
      and(not GameConfiguration.IsHotseat or GameConfiguration.IsHotseat()==false)
      and Players[0]:IsTurnActive()and Game.IsAllowStrategicCommands(0)==true
      and not UI.IsGameCoreBusy()and not UI.IsProcessingMessages()and not UI.HasSentTurnComplete()
  end
  local function military(u)
    local d=u and GameInfo.Units[u:GetUnitType()];local k=d and d.UnitType
    return d and((d.Combat or 0)>0 or(d.RangedCombat or 0)>0 or d.FormationClass=='FORMATION_CLASS_SUPPORT'
      or k=='UNIT_GREAT_GENERAL'or k=='UNIT_GREAT_ADMIRAL'or k=='UNIT_APOSTLE'or k=='UNIT_INQUISITOR'or k=='UNIT_GURU')
  end
  local function eligible(u)
    return u and u:GetOwner()==0 and military(u)and not u:IsDead()and not u:IsDelayedDeath()
      and u:GetFormationUnitCount()==1 and u:GetMovesRemaining()>0
      and u:IsReadyToMove()==true and u:IsReadyToSelect()==true
      and not u:HasPendingOperations()and UnitManager.GetQueuedDestination(u)==nil
  end
  assert(phase(),'Normal player phase unavailable; zero commands')
  for _,candidate in Players[0]:GetUnits():Members()do
    report.scanned=report.scanned+1;assert(report.scanned<=256,'Actual unit census exceeded bound')
    if report.submitted>=limit then break end
    if not phase()or not allowed()then report.phaseStopped=true;break end
    local id,kind=candidate:GetID(),candidate:GetUnitType()
    if state.attempts[id]==nil and eligible(candidate)then
      UI.SelectUnit(candidate)
      local u=Players[0]:GetUnits():FindID(id);local selected=UI.GetHeadSelectedUnit()
      if phase()and allowed()and eligible(u)and u:GetID()==id and u:GetUnitType()==kind
        and selected and selected:GetID()==id and selected:GetOwner()==0
        and UnitManager.CanStartOperation(u,action,nil,{})==true then
        u=Players[0]:GetUnits():FindID(id);selected=UI.GetHeadSelectedUnit()
        if phase()and allowed()and state.attempts[id]==nil and eligible(u)and u:GetID()==id and u:GetUnitType()==kind
          and selected and selected:GetID()==id and selected:GetOwner()==0 then
          local attempt={id=id,kind=GameInfo.Units[kind].UnitType,x=u:GetX(),y=u:GetY(),turn=turn,
            operation=action,nativeReturned=false,effect='UNKNOWN'}
          state.attempts[id]=attempt
          report.submitted=report.submitted+1
          local ok,value=pcall(UnitManager.RequestOperation,u,action,{})
          attempt.nativeReturned=ok -- Protected-call return, not proof of native effect.
          attempt.firstResultType=type(value)
          if not ok then report.nativeError=true;attempt.nativeError=tostring(value);break end
        end
      end
    end
  end
  return report
end
