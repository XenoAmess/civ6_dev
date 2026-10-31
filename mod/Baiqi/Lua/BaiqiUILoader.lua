-- Include only the most derived installed ruleset script. Its own includes load
-- its parents; including them again would duplicate Initialize and event handlers.
BaiqiUILoader={}
local xp1={WorldInput=true,UnitPanel=true,CityPanel=true,CityPanelOverview=true,TechTree=true,GovernmentScreen=true,CityStates=true,GreatPeoplePopup=true}
local xp2={WorldInput=true,UnitPanel=true,CityPanel=true,CityPanelOverview=true,TechTree=true,CivicsTree=true,GovernmentScreen=true,CityStates=true,GreatPeoplePopup=true}
function BaiqiUILoader.Load(name)
  local ruleset=GameConfiguration.GetValue("RULESET")
  if ruleset=="RULESET_EXPANSION_2" and xp2[name] then include(name.."_Expansion2")
  elseif ruleset=="RULESET_EXPANSION_1" and xp1[name] then include(name.."_Expansion1")
  else include(name) end
end
function BaiqiUILoader.ReadOnly()
  if type(IsReadOnly)=="function" then
    local native=IsReadOnly
    IsReadOnly=function(...) return BaiqiUIGuard.PlayerID()~=nil or native(...) end
  end
end
