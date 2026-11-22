"""Apply checked substitutions to the pinned upstream MinIO recovery case."""
import hashlib
import sys
from pathlib import Path

path = Path(sys.argv[1])
raw = path.read_bytes()
assert hashlib.sha256(raw).hexdigest() == "2a6446b24fb3e1fcfb2d5fcf6f9e75b90b9804367eddaee5f122463c16392363"
source = raw.decode()
start = source.index("    def _run_partial_cloud_recovery")
end = source.index("    def _run_corrected_origin_recovery")
partial = source[start:end]


def replace(old, new):
    global partial
    assert partial.count(old) == 1, old
    partial = partial.replace(old, new)


replace("            self._zero_spend(node.getmodel(uri), 'healthy getmodel')", """            self._zero_spend(node.getmodel(uri), 'healthy getmodel')
            healthy = self._zero_spend(node.exportmodelpath(uri), 'healthy export')
            assert (Path(healthy['path']) / source.name).read_bytes() == original
            result.update(real_minio=True, trusted_tls=True, healthy_bytes_match=True)""")
replace("            assert self._s3('DELETE', key=key)[0] in [200, 204]", """            piece1 = f'/{BUCKET}/{key}'
            piece0 = piece1.removesuffix('1.piece') + '0.piece'""")
replace("            failed = self._zero_spend(node.getmodel(uri), 'partial origin failure')", """            window_begin = len(self.relay.events)
            self.relay.delayed_path = piece1
            failed = self._zero_spend(node.getmodel(uri), 'partial HTTPS read timeout')
            returned = time.monotonic()
            attempt_events = self.relay.events[window_begin:]
            result.update(attempt_events=attempt_events, cloud_error=failed.get('cloud_hydrate_error', ''))
            save()
            [first_served] = [t for method, path, status, t in attempt_events
                              if (method, path, status) == ('GET', piece0, 200)]
            [second_wait] = [t for method, path, status, t in attempt_events
                             if (method, path, status) == ('GET', piece1, 'delay')]
            result['timeout_window'] = dict(piece_0_served=first_served,
                                            piece_1_wait_started=second_wait, rpc_returned=returned)""")
replace("            assert (quarantine / '0.piece').read_bytes() == first", """            assert (quarantine / '0.piece').read_bytes() == first
            result['first_piece_match'] = True""")
replace("                result['partial_export_error'] = str(e)", """                result['partial_export_error'] = str(e)
                result['partial_export_refused'] = True""")
replace("""            assert self._s3('PUT', key=key, body=remote_piece)[0] in [200, 204]
            assert self._reconstruct_object(self._bucket_keys(), artifact) == original
            result['origin_restored_byte_identical'] = True""", """            self.relay.delayed_path = None
            retry_begin = len(self.relay.events)""")
replace("            result['retry_responses'] = retry()", """            result['retry_responses'] = retry()
            retry_gets = [(path, status) for method, path, status, _ in self.relay.events[retry_begin:]
                          if method == 'GET']
            result['retry_gets'] = retry_gets
            result['saved_prefix_reused'] = (
                all(path != piece0 for path, _ in retry_gets)
                and (piece1, 200) in retry_gets
                and (piece1.removesuffix('1.piece') + '2.piece', 200) in retry_gets
            )""")

main = source.index('    def run_test(self):')
source = source[:start] + partial + source[end:main] + """
    def run_test(self):
        from https_fixture import MinioRelay

        self.creds = Path(self.options.tmpdir) / "cloud-creds.ini"
        self.creds.write_text(f"access_key_id={ACCESS_SENTINEL}\\nsecret_access_key={SECRET_SENTINEL}\\n")
        self.creds.chmod(0o600)
        origin = self._start_container()
        assert origin is not None, self.not_run
        with MinioRelay(origin, os.environ["MODELNET_TEST_CERT"], os.environ["MODELNET_TEST_KEY"]) as relay:
            self.relay = relay
            self.endpoint = relay.endpoint
            status, _ = self._s3("PUT")
            assert status == 200, status
            self._run_partial_cloud_recovery()
            self._assert_no_sentinel_in_logs("after HTTPS recovery")


if __name__ == "__main__":
    ModelNetMinioLayoutsTest(__file__).main()
"""
compile(source, str(path), "exec")
path.write_text(source)
