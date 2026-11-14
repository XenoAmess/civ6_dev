-- Bounded geometry only: graph distance is not a movement or visibility promise.
return function(map,visibility,x,y)
  local out={status='UNKNOWN',complete=false,inspected_nodes=0,rows={}}
  local coords,indices,queue={},{},{}
  local function Integer(v)
    assert(type(v)=='number' and v==v and v>=0 and v<math.huge and v%1==0,'Unknown geometry')
    return v
  end
  local function Scan()
    Integer(x);Integer(y)
    assert(type(map.GetAdjacentPlot)=='function' and type(visibility.IsRevealed)=='function','Missing geometry ports')
    local center={x=x,y=y,distance=0};coords[x..':'..y]=center;queue[1]=center;out.inspected_nodes=1
    local head=1
    while head<=#queue do
      local parent=queue[head];head=head+1
      if parent.distance<3 then
        for direction=0,5 do
          local plot=map.GetAdjacentPlot(parent.x,parent.y,direction)
          if plot~=nil then
            local index=Integer(plot:GetIndex());local px=Integer(plot:GetX());local py=Integer(plot:GetY())
            local key=px..':'..py;local old=coords[key];local prior=indices[index]
            assert(not prior or(prior.x==px and prior.y==py),'Index/coordinate conflict')
            if old then
              assert(old.index==nil or old.index==index,'Coordinate/index conflict')
              old.index=index;indices[index]=old
            else
              if out.inspected_nodes==64 then return 'PARTIAL_LIMIT' end
              local node={index=index,x=px,y=py,distance=parent.distance+1}
              coords[key]=node;indices[index]=node;queue[#queue+1]=node
              out.inspected_nodes=out.inspected_nodes+1
              local revealed=visibility:IsRevealed(px,py)
              assert(type(revealed)=='boolean','Unknown visibility')
              if not revealed then
                out.rows[#out.rows+1]={plot_index=index,x=px,y=py,distance=node.distance}
              end
            end
          end
        end
      end
    end
    return 'COMPLETE'
  end
  local ok,status=pcall(Scan)
  if ok then out.status=status;out.complete=status=='COMPLETE' end
  table.sort(out.rows,function(a,b)
    if a.distance~=b.distance then return a.distance<b.distance end
    return a.plot_index<b.plot_index
  end)
  return out
end
