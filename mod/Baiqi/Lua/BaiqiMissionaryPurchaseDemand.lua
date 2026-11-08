local M={}
local MAX=2147483647
local function Object(v)return type(v)=="table"or type(v)=="userdata"end
local function Int(v,lo,hi)return type(v)=="number"and v>=lo and v<=hi and v%1==0 end
local function Call(o,k,...)
  assert(Object(o)and type(o[k])=="function")
  return o[k](o,...)
end
function M.Read(E,player,pid)
  local ok,result=pcall(function()
    assert(Int(pid,0,MAX)and Object(E)and Object(E.GameInfo)and Object(E.GameInfo.Units)
      and type(E.SafeCity)=="function")
    local created=Call(Call(player,"GetReligion"),"GetReligionTypeCreated")
    assert(Int(created,0,MAX))
    local available,seen,count=false,{},0
    local units=Call(player,"GetUnits")
    for _,unit in Call(units,"Members")do
      count=count+1;assert(count<=4096)
      local owner=Call(unit,"GetOwner");assert(Int(owner,0,MAX))
      if owner==pid then
        local id=Call(unit,"GetID");assert(Int(id,0,MAX)and not seen[id]);seen[id]=true
        local index=Call(unit,"GetUnitType");assert(Int(index,0,MAX))
        local row=E.GameInfo.Units[index];assert(Object(row)and type(row.UnitType)=="string")
        if row.UnitType=="UNIT_MISSIONARY"then
          local dead=Call(unit,"IsDelayedDeath");assert(type(dead)=="boolean")
          if not dead then
            local religion=Call(unit,"GetReligionType");local charges=Call(unit,"GetSpreadCharges")
            assert(Int(religion,0,MAX)and Int(charges,0,1000000))
            if religion==created and charges>0 then available=true end
          end
        end
      end
    end
    if available then return false end
    local target=false;seen={};count=0
    local cities=Call(player,"GetCities")
    for _,city in Call(cities,"Members")do
      count=count+1;assert(count<=256)
      local owner=Call(city,"GetOwner");assert(Int(owner,0,MAX))
      if owner==pid then
        local id=Call(city,"GetID");assert(Int(id,0,MAX)and not seen[id]);seen[id]=true
        local majority=Call(Call(city,"GetReligion"),"GetMajorityReligion")
        assert(Int(majority,-1,MAX))
        if majority~=created then
          local safe=E.SafeCity(pid,city);assert(type(safe)=="boolean")
          if safe then target=true end
        end
      end
    end
    return target and Call(Call(player,"GetReligion"),"GetReligionTypeCreated")==created
  end)
  return ok and result==true
end
BaiqiMissionaryPurchaseDemand=M
return M
