local M={}
function M.Install(E)
  if type(E)~='table' or type(E.CityManager)~='table' or type(E.CityManager.RequestOperation)~='function' or type(E.guard)~='function' then return nil,'environment' end
  local api,original=E.CityManager,E.CityManager.RequestOperation
  local h={marker='district523-owner-v1',records={},errors=0,unknown=0,drops=0,noPlacement=0,active=true}
  local function Unknown()h.unknown=h.unknown+1 end
  local function Integer(n)return type(n)=='number'and n==n and n%1==0 and n>=0 and n<=2147483647 end
  local function Record(city,operation,params)
    if E.guard()~=true or operation~=E.CityOperationTypes.BUILD or type(params)~='table' then return end
    local hash=params[E.CityOperationTypes.PARAM_DISTRICT_TYPE]
    if hash==nil then return end
    if city==nil or type(city.GetOwner)~='function' or type(city.GetID)~='function' then Unknown();return end
    local owner,id
    local ok1,owner=pcall(city.GetOwner,city)
    if not ok1 then h.errors=h.errors+1;return end
    if owner~=0 then return end
    local ok2,id=pcall(city.GetID,city)
    if not ok2 or not Integer(id) then Unknown();return end
    local x,y=params[E.CityOperationTypes.PARAM_X],params[E.CityOperationTypes.PARAM_Y]
    if x==nil and y==nil then h.noPlacement=h.noPlacement+1;return end
    if #h.records>=16 then h.drops=h.drops+1;return end
    if not Integer(x)or not Integer(y)or type(hash)~='number'or hash%1~=0 or hash<-2147483648 or hash>2147483647 then Unknown();return end
    local row=E.GameInfo.Districts[hash]
    if not row or row.Hash~=hash or type(row.DistrictType)~='string' then Unknown();return end
    local vis=E.PlayersVisibility[0]
    if vis:IsVisible(x,y)~=true or vis:IsRevealed(x,y)~=true then Unknown();return end
    local plot=E.Map.GetPlot(x,y)
    if not plot or plot:GetX()~=x or plot:GetY()~=y or plot:GetOwner()~=0 then Unknown();return end
    local index,imp,district=plot:GetIndex(),plot:GetImprovementType(),plot:GetDistrictType()
    local turn=E.Game.GetCurrentGameTurn()
    if not Integer(index)or not Integer(turn)or turn<40 or turn>160 or(type(imp)~='number'or(imp~=-1 and not Integer(imp)))or(type(district)~='number'or(district~=-1 and not Integer(district)))then Unknown();return end
    local improvement='NONE'
    if imp~=-1 then
      local def=E.GameInfo.Improvements and E.GameInfo.Improvements[imp]
      if not def or type(def.ImprovementType)~='string' then Unknown();return end
      improvement=def.ImprovementType
    end
    h.records[#h.records+1]={status='BEFORE_REQUEST_NOT_ACK',turn=turn,city=id,hash=hash,districtType=row.DistrictType,x=x,y=y,plotIndex=index,improvementIndex=imp,improvementType=improvement,existingDistrictIndex=district}
  end
  local wrapper
  wrapper=function(city,operation,params,...)
    if h.active then local ok=pcall(Record,city,operation,params);if not ok then h.errors=h.errors+1 end end
    return original(city,operation,params,...)
  end
  function h.Restore()
    if not h.active then return true end
    if api.RequestOperation~=wrapper then return false end
    api.RequestOperation=original;h.active=false;return true
  end
  api.RequestOperation=wrapper
  return h
end
return M
