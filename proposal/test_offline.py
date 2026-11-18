import ast
import copy
import hashlib
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import urllib.request
import regression as reg
from results import validate

class Offline(unittest.TestCase):
    def test_real_python_origin_health_and_independent_release(self):
        with reg.Origin() as origin:
            urllib.request.urlopen(urllib.request.Request(origin.endpoint+'/fixture/health', data=b'probe', method='PUT'), timeout=2).read()
            self.assertEqual(urllib.request.urlopen(origin.endpoint+'/fixture/health', timeout=2).read(), b'probe')
            result = []
            t = threading.Thread(target=lambda:result.append(urllib.request.urlopen(urllib.request.Request(origin.endpoint+'/fixture/artifacts/a/files/0', data=reg.payload(),method='PUT'),timeout=2).status))
            t.start(); self.assertTrue(origin.entered.wait(1))
            timer=threading.Timer(.01,origin.unblock);timer.start();t.join(2);timer.join(1)
            self.assertFalse(t.is_alive());self.assertFalse(timer.is_alive());self.assertEqual(result,[200])
            self.assertEqual(origin.objects['/fixture/artifacts/a/files/0'],reg.payload())

    def test_payload_header(self):
        data=reg.payload();header=reg.json.loads(data[8:128]);self.assertEqual(header['w']['data_offsets'],[0,len(data)-128])

    def test_initial_budget_keys(self):
        values={k:0 for k in ('budget_used_gets','origin_bytes','budget_used_gets_day','budget_used_gets_month','budget_used_bytes_day','budget_used_bytes_month')}
        self.assertEqual(reg.budget(values),values)
        with self.assertRaises(KeyError):reg.budget({})

    def test_collector_rejects_missing_or_control_failure(self):
        for r in ({},{'complete':False},{'complete':True,'error':'setup'},{'complete':True,'exits':[0,1]}):
            with self.subTest(record=r),self.assertRaises((KeyError,AssertionError)):validate(r,'candidate')

    def test_no_native_process_in_import(self):
        with patch.object(reg.subprocess,'Popen',side_effect=AssertionError('native not allowed')):
            with tempfile.TemporaryDirectory() as td:
                h=reg.Helper(Path('/unused'),Path(td),Path(td));self.assertEqual(h.exits,[])

if __name__=='__main__':unittest.main(verbosity=2)

class CollectorControls(unittest.TestCase):
    def record(self,phase):
        return {'complete':True,'exits':[0,0],'origin_handlers_alive':0,'same_key_retry':True,'duplicate_replay':True,'upload_retry':True,
                'restart_preserves_configuration_and_budget':True,'upload_bytes':len(reg.payload()),'upload_sha256':hashlib.sha256(reg.payload()).hexdigest(),
                'before_budget':{'budget_used_gets':1,'origin_bytes':15},'final_budget':{'budget_used_gets':2,'origin_bytes':30},
                'gate':{'entered':1,'released':3,'resumed':3.1},'origin_requests':[{'status':200}],
                'paused_hello':{'sent':1.1,'finished':3.2 if phase=='baseline'else 1.2},
                'verdict':'REPRODUCED'if phase=='baseline'else'PASS','violations':['hello waited for upload release','busy controls not reached before release']if phase=='baseline'else[],
                'busy_controls':True,'paused_info':{'helper_ready':True,'cloud_storage_busy':True}}
    def test_valid_phase_records(self):
        for phase in ('baseline','candidate'):self.assertTrue(validate(self.record(phase),phase))
    def test_real_contract_or_setup_failures_rejected(self):
        mutations=[lambda r:r.update(complete=False),lambda r:r.update(exits=[0,1]),lambda r:r.update(origin_handlers_alive=1),
                   lambda r:r.update(upload_sha256='wrong'),lambda r:r['final_budget'].update(budget_used_gets=0),
                   lambda r:r.update(same_key_retry=False),lambda r:r.update(restart_preserves_configuration_and_budget=False),
                   lambda r:r.update(violations=['hello waited for upload release']),lambda r:r['paused_hello'].update(finished=3.2)]
        for i,mutate in enumerate(mutations):
            with self.subTest(case=i):
                r=self.record('candidate');mutate(r)
                with self.assertRaises(AssertionError):validate(r,'candidate')
