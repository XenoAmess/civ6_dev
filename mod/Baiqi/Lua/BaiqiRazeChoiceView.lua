-- Observe only the player's qualified original RAZE request. Always forward
-- that native request once with its complete arguments and return tuple.
BaiqiRazeChoiceView={}
-- Identity only: this popup must never import the administration lock layer.
function BaiqiRazeChoiceView.PlayerID(C,E)
  if type(C)~='table'or type(C.leader)~='string'or type(E)~='table'then return nil end
  local pid=E.Game.GetLocalPlayer()
  if type(pid)~='number'or pid<0 or pid%1~=0 or E.GameConfiguration.IsAnyMultiplayer()~=false then return nil end
  local hotseat=E.GameConfiguration.IsHotseat
  if hotseat~=nil and(type(hotseat)~='function'or hotseat()~=false)then return nil end
  local p,c=E.Players[pid],E.PlayerConfigurations[pid]
  if not p or not c or type(c.GetLeaderTypeName)~='function'or c:GetLeaderTypeName()~=C.leader then return nil end
  local human
  if type(c.IsHuman)=='function'then human=c:IsHuman()
  elseif c.IsHuman==nil and type(p.IsHuman)=='function'then human=p:IsHuman()end
  if human~=true then return nil end
  return pid
end
function BaiqiRazeChoiceView.Wrap(native,manager,E)
  local reported={}
  return function(city,command,params,...)
    if command==E.CityCommandTypes.DESTROY and type(params)=='table'
      and params[E.UnitOperationTypes.PARAM_FLAGS]==E.CityDestroyDirectives.RAZE then
      local ok,recorded,pid,id=pcall(function()
        local owner=E.PlayerID()
        if owner==nil then return true end
        if not city or city:GetOwner()~=owner or city:CanRaze()~=true
          or manager.CanStartCommand(city,command,params)~=true then return false,owner end
        local cityID,x,y=city:GetID(),city:GetX(),city:GetY()
        local t=E.Map.GetPlot(x,y)
        local b=E.ExposedMembers and E.ExposedMembers.BaiqiRazeChoiceBridge
        if not t or type(b)~='table'or b.version~=1 or b.marker~='baiqi-raze-choice-v1'
          or type(b.Remember)~='function'then return false,owner,cityID end
        local s,v=b.Remember(owner,cityID,t:GetIndex(),x,y)
        return s=='READY'and type(v)=='table'and v.owner==owner and v.plot==t:GetIndex(),owner,cityID
      end)
      if not ok or recorded~=true then
        local key=tostring(pid)..':'..tostring(id)
        if not reported[key]then
          reported[key]=true
          E.Print('BAIQI|raze_choice_unavailable|original_player_request_forwarded=true')
        end
      end
    end
    return native(city,command,params,...)
  end
end
return BaiqiRazeChoiceView
