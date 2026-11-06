-- No bootstrap guesses load kind: the UI supplies its typed native provenance.
if BaiqiSettlementIntentGameplay then return end
include("BaiqiSettlementJournal")
include("BaiqiSettlementStateCore")
include("BaiqiSettlementUnitCore")
include("BaiqiSettlementTileCore")
include("BaiqiSettlementIntentCore")
local C,J=BaiqiConfig,BaiqiSettlementJournal
local E={Game=Game,GameConfiguration=GameConfiguration,Players=Players,
  PlayerConfigurations=PlayerConfigurations,GameInfo=GameInfo,Map=Map,
  PlayersVisibility=PlayersVisibility,CityManager=CityManager}
local S=BaiqiSettlementStateCore.Create(C,J,E)
local api=S and BaiqiSettlementIntentCore.Create(C,J,S,BaiqiSettlementUnitCore,BaiqiSettlementTileCore,E)
local MARKER="baiqi-settlement-intent-v1"
BaiqiSettlementIntentGameplay={}
if api and type(ExposedMembers)=="table" and (ExposedMembers.BaiqiSettlementIntentBridge==nil
  or (type(ExposedMembers.BaiqiSettlementIntentBridge)=="table"
    and ExposedMembers.BaiqiSettlementIntentBridge.marker==MARKER
    and ExposedMembers.BaiqiSettlementIntentBridge.version==1)) then
  api.version=1;api.marker=MARKER;ExposedMembers.BaiqiSettlementIntentBridge=api
  print("BAIQI|settlement_intent_loaded|version=1")
else
  print("BAIQI|settlement_intent_unavailable|bridge_or_dependencies=true")
end
