-- Private QA storage only: no native calls, command permission or live references.
local events,total,dropped={},0,0
local function Record(unitID,requestID,armedTurn,actualTurn,kind,reason,entered,qualifyOK,writerOK)
  total=total+1
  if #events==32 then table.remove(events,1);dropped=dropped+1 end
  events[#events+1]={unitID=unitID,requestID=requestID,armedTurn=armedTurn,actualTurn=actualTurn,
    kind=kind,reason=reason,entered=entered,qualifyOK=qualifyOK,writerOK=writerOK}
end
local function Snapshot()
  local copy={marker='baiqi152-found-dispatch-v1',events={},total=total,dropped=dropped}
  for i,e in ipairs(events)do
    local row={}
    for k,v in pairs(e)do row[k]=v end
    copy.events[i]=row
  end
  return copy
end
return Record,Snapshot
