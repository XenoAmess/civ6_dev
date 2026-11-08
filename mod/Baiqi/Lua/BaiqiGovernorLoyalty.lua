-- Pure, bounded choice. Native pressure values are supplied by the original
-- governor chooser APIs; this does not predict future empire-wide pressure.
BaiqiGovernorLoyalty={}
local function Number(v,low,high)
  return type(v)=="number" and v==v and v>=low and v<=high
end
local function Integer(v,low,high)
  return Number(v,low,high) and v%1==0
end
local function Plain(v)return type(v)=="table" and getmetatable(v)==nil end
local function Array(v,limit)
  if not Plain(v) then return false end
  local count=0
  for k in pairs(v) do
    if not Integer(k,1,limit) then return false end
    count=count+1
  end
  for i=1,count do if v[i]==nil then return false end end
  return count<=limit
end
local function Plan(s)
  if not Plain(s) or not Array(s.cities,128) or not Array(s.governors,32) then return nil end
  local cities,governors={},{}
  for _,c in ipairs(s.cities) do
    if not Plain(c) or not Integer(c.id,0,2147483647) or cities[c.id]
      or not Integer(c.population,0,9999) or not Number(c.loyalty,0,100)
      or not Number(c.rate,-1000,1000) or not Number(c.removalPressure,0,1000)
      or (c.assigned~=nil and not Integer(c.assigned,0,2147483647)) then return nil end
    if c.assigned==nil and c.removalPressure~=0 then return nil end
    cities[c.id]=c
  end
  for _,g in ipairs(s.governors) do
    if not Plain(g) or not Integer(g.type,0,2147483647) or governors[g.type]
      or not Integer(g.neutralized,0,9999) or not Number(g.pressure,0,1000) or g.pressure==0
      or (g.city~=nil and not Integer(g.city,0,2147483647)) or not Plain(g.assignable) then return nil end
    local n=0
    for id,can in pairs(g.assignable) do
      n=n+1
      if n>128 or not Integer(id,0,2147483647) or not cities[id] or type(can)~="boolean" then return nil end
    end
    governors[g.type]=g
  end
  local targets={}
  for _,c in ipairs(s.cities) do
    if c.assigned~=nil then
      local g=governors[c.assigned]
      if not g or g.city~=c.id then return nil end
    elseif c.rate<0 and c.loyalty<=75 then targets[#targets+1]=c end
  end
  for _,g in ipairs(s.governors) do
    if g.city~=nil and (not cities[g.city] or cities[g.city].assigned~=g.type) then return nil end
  end
  table.sort(targets,function(a,b)
    local x,y=a.loyalty/-a.rate,b.loyalty/-b.rate
    if x~=y then return x<y end
    if a.loyalty~=b.loyalty then return a.loyalty<b.loyalty end
    return a.id<b.id
  end)
  for _,target in ipairs(targets) do
    local choices={}
    for _,g in ipairs(s.governors) do
      if g.neutralized==0 and g.assignable[target.id]==true and target.rate+g.pressure>0 then
        local donor=g.city and cities[g.city]
        if not donor or (donor.loyalty>=80 and donor.rate-donor.removalPressure>=1) then
          choices[#choices+1]={governor=g.type,source=g.city,target=target.id,
            after=donor and donor.rate-donor.removalPressure or 0}
        end
      end
    end
    table.sort(choices,function(a,b)
      if (a.source==nil)~=(b.source==nil) then return a.source==nil end
      if a.after~=b.after then return a.after>b.after end
      return a.governor<b.governor
    end)
    local first=choices[1]
    if first then return {governor=first.governor,source=first.source,target=first.target} end
  end
end
function BaiqiGovernorLoyalty.Plan(snapshot)
  local ok,result=pcall(Plan,snapshot)
  if ok then return result end
end
return BaiqiGovernorLoyalty
