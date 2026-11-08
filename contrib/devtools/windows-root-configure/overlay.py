import re
CHECKS={'external_signer_matches_p2mr_bip32_fingerprint': ['returned 1: mock signer failed'], 'external_signer_enumerate_rejects_invalid_fingerprint': ['received invalid signer fingerprint'], 'external_signer_enumerate_rejects_non_string_fingerprint': ['received invalid signer fingerprint']}
def strengthen(source):
 for name,needles in CHECKS.items():
  start=source.index('BOOST_AUTO_TEST_CASE('+name+')');end=source.find('BOOST_AUTO_TEST_CASE',start+1);end=len(source) if end<0 else end
  body=source[start:end]
  assert body.count('BOOST_CHECK_THROW(')==1
  body=body.replace('BOOST_CHECK_THROW(', 'BOOST_CHECK_EXCEPTION(',1)
  predicate=' && '.join('std::string{e.what()}.find('+repr(x).replace("'",'"')+') != std::string::npos' for x in needles)
  body=body.replace(', std::runtime_error);', ', std::runtime_error, [](const std::runtime_error& e) { return '+predicate+'; });',1)
  assert 'BOOST_CHECK_EXCEPTION(' in body and all(x in body for x in needles)
  source=source[:start]+body+source[end:]
 return source
