-- Passive, bounded observer of an existing per-context request function.
-- Installation never issues a city request. Every observed invocation is
-- forwarded once with untouched arguments and exact return arity.
return function(manager,keys)
  assert(type(manager)=='table'and type(manager.RequestCommand)=='function')
  assert(type(keys)=='table'and keys.x~=nil and keys.y~=nil and keys.manage~=nil)
  local native=manager.RequestCommand
  local unpackValues=table.unpack or unpack
  local function pack(...)return {n=select('#',...),...}end
  local rows,count,dropped,retired={},0,0,false
  local wrapper
  wrapper=function(...)
    local args=pack(...);count=count+1
    local row
    if #rows<16 then
      row={sequence=count,metadataKnown=false,returned=false}
      rows[#rows+1]=row
      local ok=pcall(function()
        local city,command,p=args[1],args[2],args[3]
        assert(city~=nil and type(city.GetID)=='function'and type(city.GetOwner)=='function'and type(p)=='table')
        local id,owner,x,y,manage=city:GetID(),city:GetOwner(),p[keys.x],p[keys.y],p[keys.manage]
        assert(type(id)=='number'and type(owner)=='number'and type(command)=='number'and type(x)=='number'and type(y)=='number'and type(manage)=='number')
        row.cityID,row.owner,row.command,row.x,row.y,row.manage=id,owner,command,x,y,manage
      end)
      row.metadataKnown=ok
    else dropped=dropped+1 end
    local result=pack(native(unpackValues(args,1,args.n)))
    if row then
      row.returned=true;row.returnCount=result.n
      row.firstType=type(result[1])
      if row.firstType=='boolean'or row.firstType=='number'or row.firstType=='string'then row.first=result[1]end
    end
    return unpackValues(result,1,result.n)
  end
  manager.RequestCommand=wrapper
  local api={}
  function api.Read()
    local copy={count=count,dropped=dropped,retired=retired,rows={}}
    for i,row in ipairs(rows)do local r={};for k,v in pairs(row)do r[k]=v end;copy.rows[i]=r end
    return copy
  end
  function api.Retire()
    if retired then return false,'already_retired'end
    if manager.RequestCommand~=wrapper then return false,'function_replaced'end
    manager.RequestCommand=native;retired=true;return true,'original_restored'
  end
  return api
end
