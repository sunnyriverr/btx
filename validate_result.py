def qualifies(r):
 expected={(v,c) for v in ('baseline','candidate') for c in ('valid','shared','exhausted')}
 rows=r.get('cases',[])
 return r.get('complete') is True and not r.get('error') and len(rows)==6 and {(x.get('variant'),x.get('case')) for x in rows}==expected and all(x.get('completed') is True and x.get('contract_pass') is (x['variant']=='candidate' or x['case']=='valid') and x.get('relay_after',{}).get('active_forwarded')==0 for x in rows)
