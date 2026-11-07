-- Movement proposals only. No command authorization or founding receipts.
BaiqiSettlerGoals={}
local M=BaiqiSettlerGoals
local function Integer(n)return type(n)=='number'and n==n and n>=0 and n<=2147483647 and n%1==0 end
local function Parameters(owner,width,height)
  return Integer(owner)and Integer(width)and Integer(height)and width>=1 and height>=1 and width*height<=2147483647
end
local function Fields(t,allowed,count)
  if type(t)~='table'or getmetatable(t)~=nil then return false end
  local n=0
  for k in pairs(t)do n=n+1;if n>count or not allowed[k]then return false end end
  return n==count
end
local bankFields={version=true,owner=true,width=true,height=true,goals=true}
local goalFields={unitID=true,unitType=true,plot=true,x=true,y=true}
function M.New(owner,width,height)
  if not Parameters(owner,width,height)then return nil end
  return {version=1,owner=owner,width=width,height=height,goals={}}
end
function M.Clone(value,owner,width,height)
  if not Parameters(owner,width,height)or not Fields(value,bankFields,5)
    or value.version~=1 or value.owner~=owner or value.width~=width or value.height~=height
    or type(value.goals)~='table'or getmetatable(value.goals)~=nil then return nil end
  local copy=M.New(owner,width,height);local count,plots=0,{}
  for key,g in pairs(value.goals)do
    count=count+1
    if count>32 or type(key)~='string'or not Fields(g,goalFields,5)or not Integer(g.unitID)
      or key~=string.format('%.0f',g.unitID)or g.unitType~='UNIT_SETTLER'
      or not Integer(g.x)or not Integer(g.y)or g.x>=width or g.y>=height
      or not Integer(g.plot)or g.plot~=g.y*width+g.x or plots[g.plot]then return nil end
    plots[g.plot]=true
    copy.goals[key]={unitID=g.unitID,unitType=g.unitType,plot=g.plot,x=g.x,y=g.y}
  end
  return copy
end
return M
