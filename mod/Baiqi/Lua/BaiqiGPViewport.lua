-- Adapt only the inspected native GP layout; keep native rendering and data.
if BaiqiGPViewport then return end
BaiqiGPViewport={}
local V=BaiqiGPViewport
local last=setmetatable({},{__mode="k"})
local installed=false
local unpackValues=unpack or table.unpack
local function finite(v)return type(v)=="number"and v==v and math.abs(v)<math.huge end
local function list(t,limit)
  if type(t)~="table"then return false end
  local n=0
  for k in pairs(t)do
    if not finite(k)or k%1~=0 or k<1 or k>limit then return false end
    n=n+1
  end
  if n>#t or n>limit then return false end
  for i=1,n do if t[i]==nil then return false end end
  return true
end
local function plan()
  if type(BaiqiUIGuard)~="table"or type(BaiqiUIGuard.PlayerID)~="function"
    or BaiqiUIGuard.PlayerID()==nil then return nil end
  local _,screenY=UIManager:GetScreenSizeVal()
  if not finite(screenY)or screenY<600 or screenY>16384 then return nil end
  local height=math.min(768,screenY)
  local changes={}
  local function add(c,get,set,base,value)
    assert(c and type(c[get])=="function"and type(c[set])=="function")
    local old=c[get](c)
    local prior=last[c]
    assert(finite(old)and old==(prior and prior[get]or base))
    changes[#changes+1]={c=c,get=get,set=c[set],old=old,value=value}
  end
  local function size(c,base,value)add(c,"GetSizeY","SetSizeY",base,value)end
  local popup,people,stack,past=Controls.PopupContainer,Controls.PeopleScroller,Controls.PeopleStack,Controls.RecruitedScroller
  assert(popup and people and stack and past)
  assert(type(popup.ReprocessAnchoring)=="function"and type(stack.CalculateSize)=="function"
    and type(people.CalculateSize)=="function"and type(past.CalculateSize)=="function")
  size(popup,768,height);size(people,768,height);size(past,586,height-182)
  assert(type(stack.GetChildren)=="function")
  local cards=stack:GetChildren();assert(list(cards,32))
  for _,card in ipairs(cards)do
    local found,seen,n={},{},0
    local function visit(c,depth)
      assert(c and not seen[c]and type(c.GetID)=="function"and type(c.GetChildren)=="function")
      seen[c]=true;n=n+1;assert(n<=128)
      local id=c:GetID();assert(type(id)=="string")
      if id~=""then assert(found[id]==nil);found[id]=c end
      if depth<2 then
        local children=c:GetChildren();assert(list(children,64))
        for _,child in ipairs(children)do visit(child,depth+1)end
      end
    end
    visit(card,0);assert(found.Content==card)
    size(card,670,height-98)
    size(found.MainInfo,654,height-114)
    size(found.EffectStackScroller,240,height-528)
    add(found.IndividualName,"GetOffsetY","SetOffsetY",-295,40-math.floor((height-98)/2))
    size(found.BiographyArea,391,height-377)
    size(found.BiographyScroll,391,height-377)
    size(found.RecruitInfoArea,391,height-377)
    size(found.RecruitInfoScroll,391,height-377)
    -- RecruitProgressBox remains152px; reserve the full public points area.
    assert(found.RecruitProgressBox and found.RecruitProgressBox:GetSizeY()==152)
  end
  return changes,{popup,stack,people,past}
end
function V.Apply()
  local ok,changes,reflow=pcall(plan)
  if not ok or not changes then return false end
  local applied=0
  for _,entry in ipairs(changes)do
    local wrote=pcall(entry.set,entry.c,entry.value)
    if not wrote then
      pcall(entry.set,entry.c,entry.old)
      for i=applied,1,-1 do local old=changes[i];pcall(old.set,old.c,old.old)end
      return false
    end
    applied=applied+1
  end
  for _,entry in ipairs(changes)do
    last[entry.c]=last[entry.c]or{};last[entry.c][entry.get]=entry.value
  end
  reflow[2]:CalculateSize();reflow[3]:CalculateSize();reflow[4]:CalculateSize()
  reflow[1]:ReprocessAnchoring()
  return true
end
local function pack(...)return {n=select("#",...),...}end
function V.Install()
  if installed or type(ViewCurrent)~="function"or type(ViewPast)~="function"then return false end
  local current,past=ViewCurrent,ViewPast
  ViewCurrent=function(...)
    local result=pack(current(...));V.Apply();return unpackValues(result,1,result.n)
  end
  ViewPast=function(...)
    local result=pack(past(...));V.Apply();return unpackValues(result,1,result.n)
  end
  installed=true;return true
end
