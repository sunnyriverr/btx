def before_deadline(selector,log,xml,code,budget,label):
 name=selector.rsplit('/',1)[1]
 sentinel=label+' did not return within 10 seconds; exiting the test binary'
 good=(code==1 and budget is None and sentinel in log and ('Entering test case "'+name+'"')in log and 'Running 1 test case' in log and log.count('has passed')>=3)
 return {'state':'expected_deadline_reproduced'if good else'inconclusive_baseline','oracle':'specific maintained deadline+exit1+case entry; REQUIRE setup dominates deadline call','partial_xml_allowed_only_for_this_failure':good}
