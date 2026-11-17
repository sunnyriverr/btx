import xml.etree.ElementTree as ET
from read_suite import normalize
REQUIRED={'modelnet_first_run_tests':{'cancelmodeljob_save_failure_preserves_stop_and_retries','cancelmodeljob_reports_only_a_real_cancel'},'modelnet_file_stream_tests':{'whole_file_fallback_keeps_a_piece_and_does_not_wait_out_the_deadline','short_final_checkpoint_survives_publication_quota_failure'}}
def validate_suite(raw,code,suite):
 normalized,repairs=normalize(raw);root=ET.fromstring(normalized);assert code==0 and root.tag=='testsuite' and int(root.attrib['errors'])==0 and int(root.attrib['failures'])==0,'suite failure'
 cases=list(root.iter('testcase'));active=[x for x in cases if x.find('skipped')is None];selected=[x for x in cases if x.attrib.get('classname')==suite]
 assert active and len(active)==len(selected) and all(x.find('skipped')is None for x in selected) and all(x.attrib.get('classname')==suite for x in active),'wrong or skipped selected suite'
 assert len(active)==int(root.attrib['tests']) and len(cases)-len(active)==int(root.attrib['skipped']),'count mismatch'
 assert not list(root.iter('failure')) and not list(root.iter('error')),'case failure'
 assert REQUIRED[suite]<={x.attrib['name']for x in active},'required control missing'
 return {'executed':len(active),'filtered':len(cases)-len(active),'suite':suite,'cdata_repairs':repairs,'exit':code}
