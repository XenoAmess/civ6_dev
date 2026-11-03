-- Software-only prototype; not registered by the playable mod.
local function PrepareBuilderPathPacket(ctx, player, state, unit, target)
  if not ctx or not player or not unit or not target then return nil end
  local currentCtx,currentPlayer,currentState=PlayerContext()
  if not currentCtx or currentCtx.player~=ctx.player then return nil end
  ctx,player,state=currentCtx,currentPlayer,currentState
  if not CoreIdle() then return nil end
  if not BaiqiPolicy.Context(ctx) then return nil end
  if turn ~= Game.GetCurrentGameTurn() then return nil end
  local unitID = unit:GetID()
  if pendingUnits[unitID] then return nil end
  local def = GameInfo.Units[unit:GetUnitType()]
  if not def or def.UnitType ~= 'UNIT_BUILDER' then return nil end
  local snapshot = UnitSnapshot(unit, state)
  if not BaiqiPolicy.CanCivilian(ctx, snapshot) then return nil end
  local initialKey,expectedTurn=UnitKey(unit),turn
  if not Revealed(target) then return nil end
  if not Safe(target, player) then return nil end
  local targetIndex = target:GetIndex()
  if not BaiqiPolicy.Number(targetIndex) or targetIndex < 0 or targetIndex % 1 ~= 0 then return nil end
  local start = UnitIndex(unit)
  if start == nil then return nil end
  local latest,latestPlayer,latestState=PlayerContext()
  local currentDef=GameInfo.Units[unit:GetUnitType()]
  if not latest or latest.player~=ctx.player or not BaiqiPolicy.Context(latest)
    or not currentDef or currentDef.UnitType~='UNIT_BUILDER'
    or not BaiqiPolicy.CanCivilian(latest,UnitSnapshot(unit,latestState))
    or UnitKey(unit)~=initialKey or pendingUnits[unitID]
    or Game.GetCurrentGameTurn()~=expectedTurn or not CoreIdle() then return nil end
  local ok, path = pcall(UnitManager.GetMoveToPathEx, unit, targetIndex)
  if not ok or type(path) ~= 'table' or type(path.plots) ~= 'table' then return nil end
  local plots = path.plots
  local count = 0
  for _ in pairs(plots) do count = count + 1 end
  if count < 2 or count > C.pathLimit then return nil end
  local copied = {}
  for i = 1, count do
    local index = plots[i]
    if not BaiqiPolicy.Number(index) or index < 0 or index % 1 ~= 0 then return nil end
    copied[i] = index
  end
  if copied[1] ~= start or copied[count] ~= targetIndex then return nil end
  if UnitIndex(unit) ~= start then return nil end
  local freshCtx, freshPlayer, freshState = PlayerContext()
  if not freshCtx or freshCtx.player ~= ctx.player then return nil end
  if not BaiqiPolicy.Context(freshCtx) then return nil end
  local freshUnit = freshPlayer:GetUnits():FindID(unitID)
  if not BaiqiPolicy.MatchesID(freshUnit, unitID) or freshUnit:GetOwner() ~= ctx.player then return nil end
  local freshDef = GameInfo.Units[freshUnit:GetUnitType()]
  if not freshDef or freshDef.UnitType ~= 'UNIT_BUILDER' then return nil end
  local freshSnapshot = UnitSnapshot(freshUnit, freshState)
  if not BaiqiPolicy.CanCivilian(freshCtx, freshSnapshot) then return nil end
  if freshSnapshot.formationCount ~= 1 then return nil end
  if not BaiqiPolicy.Number(freshSnapshot.moves) or freshSnapshot.moves <= 0 then return nil end
  if UnitIndex(freshUnit) ~= start then return nil end
  if UnitKey(unit)~=initialKey or UnitKey(freshUnit)~=initialKey
    or pendingUnits[unitID] or Game.GetCurrentGameTurn()~=expectedTurn
    or turn~=expectedTurn or not CoreIdle() then return nil end
  return {
    version = 1,
    player = ctx.player,
    turn = turn,
    unitID = unitID,
    unitType = 'UNIT_BUILDER',
    key = initialKey,
    targetIndex = targetIndex,
    path = copied
  }
end

local function ValidateBuilderPathPacket(ctx, player, state, unit, packet)
  if not ctx or not player or not unit or type(packet)~='table' then return nil end
  local currentCtx,currentPlayer,currentState=PlayerContext()
  if not currentCtx or currentCtx.player~=ctx.player then return nil end
  ctx,player,state=currentCtx,currentPlayer,currentState
  if not CoreIdle() then return nil end
  if not BaiqiPolicy.Context(ctx) then return nil end
  if turn ~= Game.GetCurrentGameTurn() then return nil end
  if packet.version ~= 1 then return nil end
  if packet.player ~= ctx.player then return nil end
  if packet.turn ~= turn then return nil end
  local unitID = unit:GetID()
  if packet.unitID ~= unitID then return nil end
  if packet.unitType ~= 'UNIT_BUILDER' then return nil end
  if packet.key ~= UnitKey(unit) then return nil end
  if pendingUnits[unitID] then return nil end
  local def = GameInfo.Units[unit:GetUnitType()]
  if not def or def.UnitType ~= 'UNIT_BUILDER' then return nil end
  local snapshot = UnitSnapshot(unit, state)
  if not BaiqiPolicy.CanCivilian(ctx, snapshot) then return nil end
  if snapshot.formationCount ~= 1 then return nil end
  if not BaiqiPolicy.Number(snapshot.moves) or snapshot.moves <= 0 then return nil end
  local start = UnitIndex(unit)
  if start == nil then return nil end
  local path = packet.path
  if type(path) ~= 'table' then return nil end
  local count = 0
  for _ in pairs(path) do count = count + 1 end
  if count < 2 or count > C.pathLimit then return nil end
  local targetIndex = packet.targetIndex
  if not BaiqiPolicy.Number(targetIndex) or targetIndex < 0 or targetIndex % 1 ~= 0 then return nil end
  if path[1] ~= start or path[count] ~= targetIndex then return nil end
  local cache = {}
  for i = 1, count do
    local index = path[i]
    if not BaiqiPolicy.Number(index) or index < 0 or index % 1 ~= 0 then return nil end
    local ok, plot = pcall(Map.GetPlotByIndex, index)
    if not ok or not plot then return nil end
    if not Revealed(plot) then return nil end
    if not Safe(plot, player, cache) then return nil end
    if plot:GetOwner() ~= -1 and plot:GetOwner() ~= ctx.player then return nil end
  end
  local ok,nextPlot=pcall(Map.GetPlotByIndex,path[2])
  if not ok or not nextPlot or nextPlot:GetIndex()~=path[2] then return nil end
  local freshCtx, freshPlayer, freshState = PlayerContext()
  if not freshCtx or freshCtx.player ~= ctx.player then return nil end
  if not BaiqiPolicy.Context(freshCtx) then return nil end
  local freshUnit = freshPlayer:GetUnits():FindID(unitID)
  if not BaiqiPolicy.MatchesID(freshUnit, unitID) or freshUnit:GetOwner() ~= ctx.player then return nil end
  local freshDef = GameInfo.Units[freshUnit:GetUnitType()]
  if not freshDef or freshDef.UnitType ~= 'UNIT_BUILDER' then return nil end
  local freshSnapshot = UnitSnapshot(freshUnit, freshState)
  if not BaiqiPolicy.CanCivilian(freshCtx, freshSnapshot) then return nil end
  if freshSnapshot.formationCount ~= 1 then return nil end
  if not BaiqiPolicy.Number(freshSnapshot.moves) or freshSnapshot.moves <= 0 then return nil end
  if UnitIndex(freshUnit) ~= start then return nil end
  if UnitKey(unit)~=packet.key or UnitKey(freshUnit)~=packet.key
    or pendingUnits[unitID] or Game.GetCurrentGameTurn()~=packet.turn
    or turn~=packet.turn or not CoreIdle() then return nil end
  return nextPlot
end
