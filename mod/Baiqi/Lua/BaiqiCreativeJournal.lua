-- Creative people have zero action charges; never infer receipts from charges.
include("BaiqiGPJournal")
BaiqiCreativeJournal={}
local J,N=BaiqiCreativeJournal,BaiqiGPJournal
local MAX=2147483647
local top={version=true,owner=true,serial=true,operations=true}
local fields={token=true,sequence=true,unitID=true,unitType=true,class=true,
 individual=true,turn=true,stage=true,works=true,lastWork=true}
local types={UNIT_GREAT_WRITER=true,UNIT_GREAT_ARTIST=true,UNIT_GREAT_MUSICIAN=true}
function J.Token(owner,seq) return "creative:"..N.UnitKey(owner)..":"..N.UnitKey(seq) end
function J.New(owner) return {version=1,owner=owner,serial=0,operations={}} end
function J.Validate(state,owner)
 if not N.Integer(owner,MAX) or type(state)~="table" or state.version~=1 or state.owner~=owner
  or not N.Integer(state.serial,MAX) or type(state.operations)~="table" then return false end
 for key in pairs(state) do if not top[key] then return false end end
 local count,sequences,allWorks=0,{},{}
 for key,op in pairs(state.operations) do
  count=count+1
  if count>256 or type(op)~="table" then return false end
  for field in pairs(op) do if not fields[field] then return false end end
  if type(key)~="string" or key~=N.UnitKey(op.unitID) or not types[op.unitType]
   or not N.Integer(op.sequence,state.serial) or op.sequence<1 or sequences[op.sequence]
   or op.token~=J.Token(owner,op.sequence) or not N.Integer(op.class,MAX)
   or not N.Integer(op.individual,MAX) or not N.Integer(op.turn,MAX) or type(op.works)~="table"
   or (op.stage~="ARMED" and op.stage~="OBSERVED" and op.stage~="LEGACY_UNKNOWN") then return false end
  sequences[op.sequence]=true
  local works=0
  for index,value in pairs(op.works) do
   local numeric=type(index)=="string" and tonumber(index)
   works=works+1
   if works>64 or not N.Integer(numeric,MAX) or index~=N.UnitKey(numeric)
    or value~=true or allWorks[index] then return false end
   allWorks[index]=true
  end
  if op.lastWork~=nil and (not N.Integer(op.lastWork,MAX) or not op.works[N.UnitKey(op.lastWork)]) then return false end
  if (works>0 and op.lastWork==nil) or (works==0 and op.lastWork~=nil)
   or (op.stage=="OBSERVED" and works==0)
   or (op.stage=="LEGACY_UNKNOWN" and works~=0) then return false end
 end
 return true
end
function J.Clone(state,owner)
 if not J.Validate(state,owner) then return nil end
 local result=J.New(owner);result.serial=state.serial
 for key,op in pairs(state.operations) do
  local copy={};for field,value in pairs(op) do if field~="works" then copy[field]=value end end
  copy.works={};for index,value in pairs(op.works) do copy.works[index]=value end
  result.operations[key]=copy
 end
 return result
end
function J.Equal(a,b,owner)
 if not J.Validate(a,owner) or not J.Validate(b,owner) or a.serial~=b.serial then return false end
 for key,op in pairs(a.operations) do
  local other=b.operations[key];if not other then return false end
  for field,value in pairs(op) do if field~="works" and other[field]~=value then return false end end
  if op.lastWork~=other.lastWork then return false end
  for index in pairs(op.works) do if not other.works[index] then return false end end
  for index in pairs(other.works) do if not op.works[index] then return false end end
 end
 for key in pairs(b.operations) do if not a.operations[key] then return false end end
 return true
end
