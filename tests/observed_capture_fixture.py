"""Small complete exporter-schema fixture with overlapping context intervals."""


def make_capture(ui_calls=50,core_calls=20):
    keys=['Core','UI']
    rows=[]
    for key,n,calls in [('Core',1,core_calls),('UI',2,ui_calls)]:
        values=[n,0,0,0,0,0,0,0,1,0,0,0,0,calls]
        rows.append(['META',key,*map(str,values),'true','false'])
    rows.extend([
        ['SAMPLE','Core','1','CoreWork','110.001','110.003','0.002','false'],
        ['SAMPLE','UI','1','UIWork','10','10.002','0.002','false'],
        ['SAMPLE','UI','2','ZeroDuration','13','13','0','false'],
        ['WRITE','Core','86','Property.Call',str(core_calls)],
        ['WRITE','UI','86','Request.Call',str(ui_calls)],
    ])
    brackets=[]
    for key,offset in [('Core',100),('UI',0)]:
        for i,turn in enumerate(range(86,92),1):
            rows.append(['ANCHOR',key,str(i),'0',str(turn),str(10+(turn-86)*20+offset)])
        for phase,at in [('before',0),('after',120)]:
            for _ in range(3):brackets.append({'key':key,'phase':phase,'triple':[at,at+offset,at]})
    return {'rows':rows,'brackets':brackets,'expected_keys':keys,'capture_bounds':[0,120]}


def make_bounded_capture(ui_calls=50,core_calls=20):
    data=make_capture(ui_calls,core_calls)
    data['rows']=[r for r in data['rows'] if not (r[0]=='SAMPLE' and r[1]=='UI' and r[2]=='2')]
    data['rows']+=[['ZERO','Core','0','1'],['ZERO','UI','1','1']]
    data['sample_budget']=2
    return data
