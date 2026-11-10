def before_deadline(selector,log,xml,code,budget,label):
 name=selector.rsplit('/',1)[1]
 sentinel=label+' did not return within 10 seconds; exiting the test binary'
 good=(code==1 and budget is None and sentinel in log and ('Entering test case "'+name+'"')in log and 'Running 1 test case' in log and log.count('has passed')>=3)
 return {'state':'expected_deadline_reproduced'if good else'inconclusive_baseline','oracle':'specific maintained deadline+exit1+case entry; REQUIRE setup dominates deadline call','partial_xml_allowed_only_for_this_failure':good}


def baseline_failure(selector,log,xml,code,budget,label,checkpoint):
 import re,xml.etree.ElementTree as ET
 r=before_deadline(selector,log,xml,code,budget,label)
 if r['state']=='expected_deadline_reproduced':return r
 leaf=selector.rsplit('/',1)[1];minimum=3 if checkpoint==3978 else 6
 try:
  root=ET.fromstring(xml);suites=root.findall('TestSuite');suite=suites[0].find('TestSuite');cases=suite.findall('TestCase')
  valid=(len(suites)==1 and suite.get('name')=='matmul_trusted_mirror_tests' and len(cases)==1 and cases[0].get('name')==leaf and cases[0].get('result')=='aborted' and int(cases[0].get('assertions_passed','0'))==minimum and cases[0].get('assertions_failed')=='1' and suites[0].get('test_cases_aborted')=='1')
 except (ET.ParseError,AttributeError,TypeError,ValueError,IndexError):valid=False
 setup_lines=[179,3971,3972] if checkpoint==3978 else [179,179,4020,4032,4033,4037]
 setup_ok=all(len(re.findall(r'matmul_trusted_mirror_tests\.cpp\('+str(line)+r'\): info:.*has passed',log))>=setup_lines.count(line) for line in set(setup_lines))
 marker='fatal error: in "'+selector+'": class std::system_error: resource deadlock would occur: resource deadlock would occur'
 good=(valid and setup_ok and code==201 and budget is None and marker in log and ('Entering test case "'+leaf+'"')in log and 'Running 1 test case' in log and re.search(r'matmul_trusted_mirror_tests\.cpp\('+str(checkpoint)+r'\): last checkpoint',log) is not None and log.count('has passed')==minimum)
 return {'state':'expected_recursive_mutex_failure'if good else'inconclusive_baseline','oracle':'exact Windows deadlock exception at maintained call checkpoint; all prerequisite assertions pass; complete single-case aborted XML','partial_xml_allowed_only_for_this_failure':False}
