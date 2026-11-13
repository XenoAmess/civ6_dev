-- Read-only fixture qualification, never installed in the release controller.
-- Counts the returned recommendation domain, not legal sites or the whole map.
return function(player, limit)
  local out = {status="UNKNOWN", complete=false, inspected=0, unique=0,
    duplicates=0, invalidEntries=0, invalidIndices=0, nonnumericRanks=0,
    fieldErrors=0, rows={}}
  if type(limit)~="number" or limit~=limit or limit<1 or limit>4096 or limit%1~=0 then
    out.status="UNKNOWN_LIMIT"; return out
  end
  local ok, ai = pcall(function() return player:GetGrandStrategicAI() end)
  if not ok or ai==nil then out.status="UNKNOWN_AI"; return out end
  local raw
  ok, raw = pcall(function() return ai:GetSettlementRecommendations(12) end)
  if not ok then out.status="UNKNOWN_READER"; return out end
  out.returnType=type(raw)
  if type(raw)~="table" then out.status="UNKNOWN_RETURN"; return out end
  local seen, capped = {}, false
  ok = pcall(function()
    for rank, entry in pairs(raw) do
      if out.inspected==limit then capped=true; break end
      out.inspected=out.inspected+1
      local row={rankType=type(rank), entryType=type(entry)}
      local numericRank=tonumber(rank)
      row.numericRankKnown=type(numericRank)=="number" and numericRank==numericRank
        and numericRank>-math.huge and numericRank<math.huge
      if row.numericRankKnown then row.rank=numericRank
      else out.nonnumericRanks=out.nonnumericRanks+1 end
      if type(entry)~="table" and type(entry)~="userdata" then
        out.invalidEntries=out.invalidEntries+1
        row.indexStatus="INVALID_ENTRY"
      else
        local readable, index=pcall(function() return entry.SettlingLocation end)
        if not readable then
          out.fieldErrors=out.fieldErrors+1
          row.indexStatus="UNKNOWN_FIELD"
        elseif type(index)~="number" or index~=index or index<0
          or index==math.huge or index%1~=0 then
          out.invalidIndices=out.invalidIndices+1
          row.indexStatus="INVALID_INDEX"
        else
          row.indexStatus="KNOWN"; row.index=index
          if seen[index] then out.duplicates=out.duplicates+1
          else seen[index]=true; out.unique=out.unique+1 end
        end
      end
      out.rows[#out.rows+1]=row
    end
  end)
  if not ok then out.status="PARTIAL_ITERATION_ERROR"
  elseif capped then out.status="PARTIAL_LIMIT"
  elseif out.fieldErrors>0 then out.status="PARTIAL_FIELD_ERROR"
  else out.status="COMPLETE"; out.complete=true end
  return out
end
