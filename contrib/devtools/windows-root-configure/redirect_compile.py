def redirect(args, source, probe, output, pdb):
    result=list(args);changes=[];i=1
    while i<len(result):
        arg=result[i]
        if arg.replace('\\','/').lower()==source.replace('\\','/').lower():
            result[i]=probe;changes.append(('source',i))
        elif arg in ['/Fo','-Fo']:
            i+=1;result[i]=output;changes.append(('object',i))
        elif arg.startswith(('/Fo','-Fo')):
            result[i]=arg[:3]+output;changes.append(('object',i))
        elif arg in ['/Fd','-Fd']:
            i+=1;result[i]=pdb;changes.append(('pdb',i))
        elif arg.startswith(('/Fd','-Fd')):
            result[i]=arg[:3]+pdb;changes.append(('pdb',i))
        assert not arg.startswith(('/Yc','-Yc','/sourceDependencies'))
        i+=1
    assert sum(k=='source'for k,_ in changes)==1
    assert sum(k=='object'for k,_ in changes)==1
    assert sum(k=='pdb'for k,_ in changes)<=1
    assert all(before==after or index in {i for _,i in changes}for index,(before,after)in enumerate(zip(args,result)))
    return result,changes
