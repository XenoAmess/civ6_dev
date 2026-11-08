local M={}
local function finite(n)return type(n)=='number'and n==n and n>=0 and n<math.huge end
function M.Read(E)
 local function Read()
  assert(E.Game.GetLocalPlayer()==0)
  local player=assert(E.Players[0])
  local resources=assert(player:GetResources())
  local rows,indices,types,n={},{},{},0
  for row in E.GameInfo.Resources()do
   n=n+1;assert(n<=256)
   if row.ResourceClassType=='RESOURCECLASS_STRATEGIC'then
    local i,t=row.Index,row.ResourceType
    assert(finite(i)and i%1==0 and i<=2147483647 and type(t)=='string'and t~='')
    assert(not indices[i]and not types[t]);indices[i]=true;types[t]=true
    local value={index=i,type=t}
    for _,field in ipairs({{'stockpile','GetResourceAmount'},{'cap','GetResourceStockpileCap'},
     {'reserved','GetReservedResourceAmount'},{'accumulation','GetResourceAccumulationPerTurn'},
     {'imports','GetResourceImportPerTurn'},{'bonus','GetBonusResourcePerTurn'},
     {'unitDemand','GetUnitResourceDemandPerTurn'},{'powerDemand','GetPowerResourceDemandPerTurn'}})do
     local getter=resources[field[2]];assert(type(getter)=='function')
     local amount=getter(resources,t);assert(finite(amount));value[field[1]]=amount
    end
    rows[#rows+1]=value
   end
  end
  assert(#rows>0)
  return{status='KNOWN',rows=rows}
 end
 local ok,result=pcall(Read)
 if ok then return result end
 return{status='UNKNOWN',reason=tostring(result)}
end
return M
