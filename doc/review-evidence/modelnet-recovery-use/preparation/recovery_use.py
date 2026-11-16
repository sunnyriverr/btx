"""Bounded supported recovery to real local generation; disposable framework only."""
import hashlib
import json
import os
import shutil
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

from minio_upload import UploadControl, ACCESS_SENTINEL, SECRET_SENTINEL


def manifest(root):
    return {str(p.relative_to(root)): hashlib.sha384(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


def create_model(root):
    import torch
    from tokenizers import Tokenizer, models, pre_tokenizers
    from transformers import GPT2Config, GPT2LMHeadModel, PreTrainedTokenizerFast
    torch.manual_seed(43)
    vocab = {'[UNK]': 0, '[PAD]': 1, 'hello': 2, 'world': 3}
    vocab.update({f'word{i}': i for i in range(4, 32)})
    raw = Tokenizer(models.WordLevel(vocab, unk_token='[UNK]'))
    raw.pre_tokenizer = pre_tokenizers.Whitespace()
    tok = PreTrainedTokenizerFast(tokenizer_object=raw, unk_token='[UNK]', pad_token='[PAD]')
    cfg = GPT2Config(vocab_size=32, n_positions=32, n_embd=24, n_layer=1,
                     n_head=2, bos_token_id=None, eos_token_id=None, pad_token_id=1)
    GPT2LMHeadModel(cfg).eval().save_pretrained(root, safe_serialization=True)
    tok.save_pretrained(root)


class RecoveryUse(UploadControl):
    def set_test_params(self):
        super().set_test_params()

    def _stop_container(self):
        if not self.container:
            return
        subprocess.run([self.docker, 'rm', '-f', self.container], check=True,
                       capture_output=True, timeout=30)
        check = subprocess.run([self.docker, 'inspect', self.container], capture_output=True, timeout=10)
        assert check.returncode != 0, 'owned MinIO container still exists'
        self.container = None

    def run_test(self):
        receipt = Path(os.environ['BTX_UPLOAD_RECEIPT'])
        out = {'status': 'INCOMPLETE', 'provider': 'MINIO', 'fake': False, 'cases': {}}
        def save():
            receipt.write_text(json.dumps(out, indent=2)+'\n')
        node = self.nodes[0]
        root = Path(self.options.tmpdir)
        original, backup = root/'original', root/'backup'
        self.creds = root/'cloud-creds.ini'
        self.creds.write_text(f'access_key_id={ACCESS_SENTINEL}\nsecret_access_key={SECRET_SENTINEL}\n')
        self.creds.chmod(0o600)
        save()
        try:
            self.endpoint = self._start_container()
            assert self.endpoint and self._s3('PUT')[0] in (200, 409)
            self._zero_spend(node.setcloudstorage(self._cloud_cfg('SOURCE_FILES', False)), 'configure')
            out['stage'] = 'prepare real CPU model and tokenizer'; save()
            create_model(original)
            expected = manifest(original)
            shutil.copytree(original, backup, copy_function=shutil.copyfile)
            assert manifest(backup) == expected
            for name in expected:
                assert (original/name).stat().st_ino != (backup/name).stat().st_ino
            entry = self._zero_spend(node.importmodel(str(original)), 'initial import')
            assert entry.get('cloud_uploaded') is True, entry
            uri, artifact = entry['uri'], entry['artifact_id']
            out.update(model_id=entry['model_id'], artifact_id=artifact, files=expected)
            checkout = Path(self.modeldir)/'checkout'/artifact
            assert checkout.parent.parent == self.modeldir

            def generate(label):
                r = self._zero_spend(node.generatemodel(uri, {'prompt': 'hello world', 'max_new_tokens': 4}), label)
                assert r['generated'] and r['local_generate'] and not r['remote_inference']
                assert r['model_id'] == entry['model_id'] and r['artifact_id'] == artifact
                assert r['backend'] == 'transformers' and r['adapter']['device'] == 'cpu'
                assert r['adapter']['remote_inference'] is False
                assert Path(r['path']) == checkout and manifest(checkout) == expected
                assert isinstance(r['text'], str) and r['text'].strip()
                return {'text': r['text'], 'backend': r['backend'], 'device': r['adapter']['device'],
                        'model_id': r['model_id'], 'artifact_id': r['artifact_id']}

            control = generate('healthy control')
            out['control'] = control
            out['stage'] = 'recover missing pieces from cloud'; save()
            # Preserve originals off the saved source path; drop only owned cache payload.
            self._stop_helper()
            original.rename(root/'original-retained')
            if checkout.exists(): shutil.rmtree(checkout)
            artdir = Path(self.modeldir)/'store'/'artifacts'/artifact
            catalog = Path(self.modeldir)/'catalog.json'
            before = catalog.read_bytes()
            pieces = list(artdir.rglob('*.piece'))
            assert pieces
            for piece in pieces: piece.unlink()
            assert catalog.read_bytes() == before and not original.exists()
            self._start_helper(); self._wait_helper_ready()
            recovered = self._zero_spend(node.getmodel(uri, 'FREE_ONLY'), 'cloud recovery')
            assert recovered.get('cloud_hydrated') and self._origin_get_ops(recovered) > 0, recovered
            assert recovered.get('artifact_id') == artifact and recovered.get('model_id') == entry['model_id']
            out['cloud_recovery'] = recovered
            assert generate('cloud recovered use') == control
            self._stop_container()
            try:
                urllib.request.urlopen(self.endpoint+'/minio/health/live', timeout=3)
            except urllib.error.HTTPError:
                raise AssertionError('cloud endpoint still responds')
            except urllib.error.URLError:
                out['cloud_endpoint_unavailable'] = True
            else:
                raise AssertionError('cloud endpoint still responds')
            self._restart_helper()
            if checkout.exists(): shutil.rmtree(checkout)
            assert generate('cloud offline restart use') == control
            out['cases']['cloud'] = {'status': 'PASS', 'origin_used': True, 'original_absent': True,
                                     'restart_offline': True, 'generation': control}
            save()
            # A fresh catalog imports a complete independent backup, not old state.
            out['stage'] = 'recover independent backup in fresh catalog'; save()
            self._stop_helper()
            Path(self.modeldir).rename(root/'prior-modeldir-retained')
            self._start_helper(); self._wait_helper_ready()
            restored = self._zero_spend(node.importmodel(str(backup)), 'independent import')
            assert restored['model_id'] == entry['model_id'] and restored['artifact_id'] == artifact
            backup.rename(root/'backup-retained')
            assert not original.exists() and not backup.exists() and not checkout.exists()
            assert generate('independent recovered use') == control
            self._restart_helper()
            shutil.rmtree(checkout)
            assert generate('independent offline restart use') == control
            out['cases']['independent_export'] = {'status': 'PASS', 'fresh_catalog': True,
                'source_absent': True, 'restart_offline': True, 'generation': control}
            assert manifest(root/'backup-retained') == expected
            assert manifest(root/'original-retained') == expected
            out.update(originals_preserved=True, preservation_scope='disposable originals verified before normal framework cleanup', status='PASS')
            save()
        except Exception as exc:
            out.update(status='FAIL_OR_BLOCKED', failure=repr(exc)); save(); raise
        finally:
            self._stop_container()


if __name__ == '__main__':
    RecoveryUse(__file__).main()
