SHA='1'*64


def records(durations):
    result=[];start=100
    for i,seconds in enumerate(durations):
        end=start+seconds
        result.append({'from_turn':85+i,'to_turn':86+i,'pid':0,'started':start,'ended':end,'seconds':seconds})
        start=end+12
    return result


def make_pairs(enabled=5.25,control=5):
    result=[]
    for i in range(1,6):
        row={'pair':i,'order':['enabled','control'] if i%2 else ['control','enabled']}
        for variant,seconds in [('enabled',enabled),('control',control)]:
            row[variant]={'variant':variant,'run_id':f'pair{i}-{variant}','fixture_sha256':SHA,'source_version':67,'errors':0,'refused':0,'records':records([seconds]*5)}
        result.append(row)
    return result
