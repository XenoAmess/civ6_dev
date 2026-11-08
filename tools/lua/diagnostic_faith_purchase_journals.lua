local M={}
local names={"naturalist","missionary","spread"}
local function Object(v)return type(v)=="table"or type(v)=="userdata"end
local function Unknown()return{status="UNKNOWN"}end
local function Empty()
  return{status="UNKNOWN",naturalist=Unknown(),missionary=Unknown(),spread=Unknown()}
end
local function Key(k)return type(k)=="string"and #k>0 and #k<=128 end
function M.Read(E,player,pid)
  local result=Empty()
  local ok,keys,journals=pcall(function()
    assert(type(pid)=="number"and pid>=0 and pid<=2147483647 and pid%1==0
      and Object(E)and Object(E.Config)and Object(player)and type(player.GetProperty)=="function")
    local keys={E.Config.naturalistPurchaseIntentKey,E.Config.missionaryPurchaseIntentKey,E.Config.religiousIntentKey}
    assert(Key(keys[1])and Key(keys[2])and Key(keys[3])
      and keys[1]~=keys[2]and keys[1]~=keys[3]and keys[2]~=keys[3])
    local js={E.NaturalistJournal,E.MissionaryJournal,E.ReligiousJournal}
    for i=1,3 do
      local j=js[i]
      assert(Object(j)and type(j.Validate)=="function"and type(j.Clone)=="function"and type(j.Equal)=="function")
    end
    return keys,js
  end)
  if not ok then return result end
  local function Snapshot(j,key)
    local ok,value=pcall(function()
      local raw=player:GetProperty(key)
      if raw==nil then return{absent=true}end
      assert(j.Validate(raw,pid)==true)
      local copy=j.Clone(raw,pid);assert(copy~=nil and j.Validate(copy,pid)==true)
      return{state=copy,absent=false}
    end)
    return ok and value or false
  end
  local before,after={},{}
  for i=1,3 do before[i]=Snapshot(journals[i],keys[i])end
  for i=1,3 do after[i]=Snapshot(journals[i],keys[i])end
  local same=pcall(function()
    assert(E.Config.naturalistPurchaseIntentKey==keys[1]and E.Config.missionaryPurchaseIntentKey==keys[2]
      and E.Config.religiousIntentKey==keys[3])
    assert(E.NaturalistJournal==journals[1]and E.MissionaryJournal==journals[2]and E.ReligiousJournal==journals[3])
  end)
  if not same then return result end
  local overall=true
  for i=1,3 do
    local valid,value=pcall(function()
      local a,b=before[i],after[i];assert(a and b and a.absent==b.absent)
      local count={status=b.absent and"ABSENT"or"KNOWN",armed=0,observed=0,legacy=0}
      if b.absent then return count end
      assert(journals[i].Equal(a.state,b.state,pid)==true)
      local n=0
      for _,op in pairs(b.state.operations)do
        n=n+1;assert(n<=256)
        if op.stage=="ARMED"then count.armed=count.armed+1
        elseif op.stage=="OBSERVED"then count.observed=count.observed+1
        elseif i==3 and op.stage=="LEGACY_UNKNOWN"then count.legacy=count.legacy+1
        else error("invalid stage")end
      end
      return count
    end)
    if valid then result[names[i]]=value else overall=false end
  end
  result.status=overall and"KNOWN"or"UNKNOWN"
  return result
end
return M
