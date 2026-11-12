-- Read only the current original trade view. Metadata is not a deal or a quote.
local M={}
local function Plain(v)return type(v)=="table" and getmetatable(v)==nil end
local function Object(v)return type(v)=="table" or type(v)=="userdata" end
local function Int(v,lo,hi)return type(v)=="number" and v==v and v>=lo and v<=hi and v%1==0 end
local function Token(v)return Int(v,-2147483648,4294967295) or (type(v)=="string" and #v>0 and #v<=128)end
local function Method(o,k)assert(Object(o) and type(o[k])=="function");return o[k]end
local function State(E)
  assert(Plain(E))
  local s={context=E.ContextPtr,game=E.Game,ui=E.UI,configuration=E.GameConfiguration,
    players=E.Players,configs=E.PlayerConfigurations,info=E.GameInfo,manager=E.DealManager,
    directions=E.DealDirection,itemTypes=E.DealItemTypes,localPlayer=E.localPlayer,otherPlayer=E.otherPlayer}
  s.hidden=Method(s.context,"IsHidden");assert(s.hidden(s.context)==false)
  s.multi=Method(s.configuration,"IsAnyMultiplayer");assert(s.multi()==false)
  s.localID=Method(s.game,"GetLocalPlayer");s.pid=s.localID();assert(Int(s.pid,0,63))
  s.getTurn=Method(s.game,"GetCurrentGameTurn");s.turn=s.getTurn();assert(Int(s.turn,0,2147483647))
  s.busy=Method(s.ui,"IsGameCoreBusy");s.processing=Method(s.ui,"IsProcessingMessages")
  assert(s.busy()==false and s.processing()==false)
  s.getLocalID=Method(s.localPlayer,"GetID");assert(s.getLocalID(s.localPlayer)==s.pid)
  assert(Object(s.players) and s.players[s.pid]==s.localPlayer)
  s.active=Method(s.localPlayer,"IsTurnActive");assert(s.active(s.localPlayer)==true)
  assert(Object(s.configs));local config=s.configs[s.pid]
  s.human=Method(config,"IsHuman");s.leader=Method(config,"GetLeaderTypeName")
  assert(s.human(config)==true and s.leader(config)=="LEADER_BAIQI")
  s.getOtherID=Method(s.otherPlayer,"GetID");s.otherID=s.getOtherID(s.otherPlayer)
  assert(Int(s.otherID,0,63) and s.otherID~=s.pid and s.players[s.otherID]==s.otherPlayer)
  s.getDiplomacy=Method(s.localPlayer,"GetDiplomacy");local diplomacy=s.getDiplomacy(s.localPlayer)
  s.met=Method(diplomacy,"HasMet");assert(s.met(diplomacy,s.otherID)==true)
  assert(E.isDemand==false and E.isGift==false and E.initiatedByPlayerID==s.pid)
  assert(Object(s.info));s.resources=s.info.Resources;assert(Object(s.resources))
  local coal=s.resources.RESOURCE_COAL;assert(Object(coal))
  s.coalIndex=coal.Index;s.coalType=coal.ResourceType;s.coalClass=coal.ResourceClassType
  assert(Int(s.coalIndex,0,65535) and s.coalType=="RESOURCE_COAL" and s.coalClass=="RESOURCECLASS_STRATEGIC")
  assert(Object(s.directions) and Object(s.itemTypes))
  s.direction=s.directions.OUTGOING;s.resourceKind=s.itemTypes.RESOURCES
  assert(Token(s.direction) and Token(s.resourceKind))
  s.working=Method(s.manager,"GetWorkingDeal");s.possible=Method(s.manager,"GetPossibleDealItems")
  return s
end
local function Same(a,b)
  for k,v in pairs(a)do assert(b[k]==v)end
  for k,v in pairs(b)do assert(a[k]==v)end
end
function M.Read(E)
  local phase="environment"
  local ok,result=pcall(function()
    local s=State(E)
    phase="working_deal"
    local deal=s.working(s.direction,s.pid,s.otherID);assert(Object(deal))
    phase="possible_items"
    local items=s.possible(s.otherID,s.pid,s.resourceKind,deal);assert(Plain(items))
    phase="invalid_items"
    local count=0
    for key in pairs(items)do
      count=count+1;assert(count<=256 and Int(key,1,256))
    end
    local coal={index=s.coalIndex,maxAmount=0,valid=false,present=false}
    for i=1,count do
      local row=items[i];assert(Object(row))
      local kind,amount,valid=row.ForType,row.MaxAmount,row.IsValid
      assert(Int(kind,0,65535) and Int(amount,0,1000000) and type(valid)=="boolean")
      if kind==s.coalIndex then
        assert(not coal.present);coal.present=true;coal.maxAmount=amount;coal.valid=valid
      end
    end
    phase="state_changed"
    Same(s,State(E))
    assert(s.working(s.direction,s.pid,s.otherID)==deal)
    Same(s,State(E))
    return {status="KNOWN",turn=s.turn,localPlayerID=s.pid,otherPlayerID=s.otherID,coal=coal}
  end)
  if ok then return result end
  return {status="UNKNOWN",reason=phase}
end
return M
