-- Keep native crisis data, diplomacy choices, animation and scroll callbacks.
if BaiqiCrisisViewport then return end
BaiqiCrisisViewport={}
local V=BaiqiCrisisViewport
local lastHeight,installed
local unpackValues=unpack or table.unpack
local specs={{"SlideOnShow",760},{"DropShadow",760},{"Window",768},
  {"TitleContainer",768},{"CrisisBG",523},{"CrisisDetailScrollPanel",220}}
local function finite(n)return type(n)=="number" and n==n and math.abs(n)<math.huge end
local function Player()
  local pid=Game.GetLocalPlayer()
  if not finite(pid) or pid<0 or pid%1~=0 or pid>2147483647
    or GameConfiguration.IsAnyMultiplayer()~=false
    or (GameConfiguration.IsHotseat and GameConfiguration.IsHotseat()~=false) then return false end
  local p,c=Players[pid],PlayerConfigurations[pid]
  return p~=nil and c~=nil and type(c.IsHuman)=="function" and c:IsHuman()==true
    and c:GetLeaderTypeName()==BaiqiConfig.leader
end
local function Reflow()
  Controls.BaseStack:CalculateSize()
  Controls.CrisisDetailScrollPanel:CalculateSize()
  Controls.EmergencyDetailScrollPanel:CalculateSize()
  Controls.LeaderBarScrollPanel:CalculateSize()
  Controls.Window:ReprocessAnchoring()
  Controls.SlideOnShow:ReprocessAnchoring()
end
local function Plan()
  if not Player() then return nil end
  local width,height=UIManager:GetScreenSizeVal()
  if not finite(width) or width<595 or not finite(height) or height<600 or height>16384 or height%1~=0 then return nil end
  height=math.min(768,height)
  local changes={}
  for _,spec in ipairs(specs) do
    local name,base=spec[1],spec[2];local c=assert(Controls[name])
    assert(type(c.GetSizeY)=="function" and type(c.SetSizeY)=="function")
    local old=c:GetSizeY();assert(finite(old) and (old==base or (lastHeight and old==base+lastHeight-768)))
    changes[#changes+1]={c=c,set=c.SetSizeY,old=old,value=base+height-768}
  end
  for _,name in ipairs({"BaseStack","CrisisDetailScrollPanel","EmergencyDetailScrollPanel","LeaderBarScrollPanel"}) do
    assert(Controls[name] and type(Controls[name].CalculateSize)=="function")
  end
  assert(type(Controls.Window.ReprocessAnchoring)=="function" and type(Controls.SlideOnShow.ReprocessAnchoring)=="function")
  return changes,height
end
function V.Apply()
  local valid,changes,height=pcall(Plan)
  if not valid or not changes then return false end
  local attempted=0
  local ok=pcall(function()
    for _,r in ipairs(changes) do attempted=attempted+1;r.set(r.c,r.value) end
    Reflow()
    for _,r in ipairs(changes) do assert(r.c:GetSizeY()==r.value) end
  end)
  if not ok then
    for i=attempted,1,-1 do local r=changes[i];pcall(r.set,r.c,r.old) end
    pcall(Reflow)
    return false
  end
  lastHeight=height
  return true
end
local function pack(...)return {n=select("#",...),...}end
function V.Install()
  if installed or type(ShowEmergency)~="function" or type(unpackValues)~="function" then return false end
  local native=ShowEmergency
  ShowEmergency=function(...)
    local result=pack(native(...))
    -- Registered native event handlers resolve this global after populating
    -- their actual data; DelayShow/OnShow still own the original animation.
    pcall(V.Apply)
    return unpackValues(result,1,result.n)
  end
  installed=true
  return true
end
return V
