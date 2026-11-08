local M={}
local function finite(n)return type(n)=='number'and n==n and n>-math.huge and n<math.huge end
local function integer(n,lo,hi)return finite(n)and n%1==0 and n>=lo and n<=hi end
function M.Queue(E,city)
 local function Read()
  assert(type(E)=='table'and city~=nil and type(city.GetOwner)=='function')
  assert(city:GetOwner()==0)
  local q=assert(city:GetBuildQueue())
  local size,hash=q:GetSize(),q:GetCurrentProductionTypeHash()
  assert(integer(size,0,7)and integer(hash,-2147483648,2147483647))
  if size==0 and hash==0 then return{status='EMPTY',kind='EMPTY',size=size,hash=hash}end
  assert(size>0 and hash~=0)
  local gi=assert(E.GameInfo);local found
  for _,entry in ipairs({{'BUILDING','Buildings','BuildingType','Building'},{'DISTRICT','Districts','DistrictType','District'},{'UNIT','Units','UnitType','Unit'},{'PROJECT','Projects','ProjectType','Project'}})do
   local db=assert(gi[entry[2]]);local row=db[hash]
   if row~=nil then
    assert(not found and row.Hash==hash and integer(row.Index,0,2147483647)and type(row[entry[3]])=='string'and row[entry[3]]~='')
    found={kind=entry[1],type=row[entry[3]],index=row.Index,prefix=entry[4]}
   end
  end
  assert(found)
  local progressFn=assert(q['Get'..found.prefix..'Progress'])
  assert(type(progressFn)=='function')
  local progress=progressFn(q,found.index)
  local modifier,cost,turns
  if found.kind=='UNIT'then
   modifier=q:GetCurrentProductionTypeModifier()
   local f=assert(E.MilitaryFormationTypes)
   assert(integer(f.STANDARD_FORMATION,0,2147483647)and integer(f.CORPS_FORMATION,0,2147483647)and integer(f.ARMY_FORMATION,0,2147483647))
   assert(f.STANDARD_FORMATION~=f.CORPS_FORMATION and f.STANDARD_FORMATION~=f.ARMY_FORMATION and f.CORPS_FORMATION~=f.ARMY_FORMATION)
   local costName
   if modifier==f.STANDARD_FORMATION then costName='GetUnitCost'
   elseif modifier==f.CORPS_FORMATION then costName='GetUnitCorpsCost'
   elseif modifier==f.ARMY_FORMATION then costName='GetUnitArmyCost'end
   assert(costName and type(q[costName])=='function')
   cost=q[costName](q,found.index);turns=q:GetTurnsLeft(found.type,modifier)
  else
   local costFn=assert(q['Get'..found.prefix..'Cost']);assert(type(costFn)=='function')
   cost=costFn(q,found.index);turns=q:GetTurnsLeft(found.type)
  end
  assert(finite(progress)and progress>=0 and finite(cost)and cost>=0 and finite(turns)and turns>=-1)
  return{status='KNOWN',size=size,hash=hash,kind=found.kind,type=found.type,index=found.index,progress=progress,cost=cost,turns=turns,modifier=modifier}
 end
 local ok,value=pcall(Read)
 if ok then return value end
 return{status='UNKNOWN',reason=tostring(value)}
end
return M
