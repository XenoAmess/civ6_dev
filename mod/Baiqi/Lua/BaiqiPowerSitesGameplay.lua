if BaiqiPowerSitesGameplay then return end
include('BaiqiConfig')
include('BaiqiPowerSitesCore')
local E={Game=Game,GameConfiguration=GameConfiguration,Players=Players,
  PlayerConfigurations=PlayerConfigurations,GameInfo=GameInfo,Map=Map,Cities=Cities,
  PlayersVisibility=PlayersVisibility,ImprovementBuilder=ImprovementBuilder}
local api=BaiqiPowerSitesCore.Create(BaiqiConfig,E)
BaiqiPowerSitesGameplay={}
if api and type(ExposedMembers)=='table'and(ExposedMembers.BaiqiPowerSitesBridge==nil
  or(type(ExposedMembers.BaiqiPowerSitesBridge)=='table'
    and ExposedMembers.BaiqiPowerSitesBridge.marker==api.marker
    and ExposedMembers.BaiqiPowerSitesBridge.version==api.version))then
  ExposedMembers.BaiqiPowerSitesBridge=api
  print('BAIQI|power_sites_loaded|version=1')
else print('BAIQI|power_sites_unavailable|bridge_or_dependencies=true')end
