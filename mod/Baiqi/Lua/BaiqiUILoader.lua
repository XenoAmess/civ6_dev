-- Most replacements include their parents. GreatPeoplePopup instead owns the
-- base handlers and loads installed extensions with its own wildcard include.
BaiqiUILoader={}
local xp1={WorldInput=true,UnitPanel=true,CityPanel=true,CityPanelOverview=true,TechTree=true,GovernmentScreen=true,CityStates=true,GreatPeoplePopup=true,ResearchChooser=true,DiplomacyActionView=true}
local xp2={WorldInput=true,UnitPanel=true,CityPanel=true,CityPanelOverview=true,TechTree=true,CivicsTree=true,GovernmentScreen=true,CityStates=true,GreatPeoplePopup=true,DiplomacyActionView=true}
function BaiqiUILoader.Load(name)
  local ruleset=GameConfiguration.GetValue("RULESET")
  if name=="GreatPeoplePopup" then
    include(name)
  elseif ruleset=="RULESET_EXPANSION_2" and xp2[name] then
    include(name.."_Expansion2")
  elseif (ruleset=="RULESET_EXPANSION_1" or ruleset=="RULESET_EXPANSION_2") and xp1[name] then
    include(name.."_Expansion1")
  else
    include(name)
  end
end
function BaiqiUILoader.ReadOnly()
  if type(IsReadOnly)=="function" then
    local native=IsReadOnly
    IsReadOnly=function(...) return BaiqiUIGuard.PlayerID()~=nil or native(...) end
  end
end
