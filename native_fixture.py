"""Run the documented zero-wallet model workflow on the published helper."""
import json
import os
from pathlib import Path
import socket
import tempfile
import time

from helpers import Helper, digest, require

WORK = Path.cwd()
OUT = WORK / 'evidence'
receipt = {'pass': False, 'archive_sha256': os.environ['BTX_CANDIDATE_SHA256']}


def phase(name):
    receipt['last_stage'] = name
    print(name, flush=True)
    (OUT/'result.json').write_text(json.dumps(receipt, indent=2)+'\n')


def create_model(path, wide=False):
    import torch
    from tokenizers import Tokenizer, models, pre_tokenizers
    from transformers import GPT2Config, GPT2LMHeadModel, PreTrainedTokenizerFast

    torch.manual_seed(43)
    vocab = {'[UNK]': 0, '[PAD]': 1, 'hello': 2, 'world': 3}
    vocab.update({f'word{i}': i for i in range(4, 32)})
    raw = Tokenizer(models.WordLevel(vocab, unk_token='[UNK]'))
    raw.pre_tokenizer = pre_tokenizers.Whitespace()
    tok = PreTrainedTokenizerFast(tokenizer_object=raw, unk_token='[UNK]', pad_token='[PAD]')
    config = GPT2Config(vocab_size=len(vocab), n_positions=32, n_embd=128 if wide else 24, n_layer=4 if wide else 1, n_head=2,
                        bos_token_id=None, eos_token_id=None, pad_token_id=1)
    GPT2LMHeadModel(config).eval().save_pretrained(path, safe_serialization=True)
    tok.save_pretrained(path)


def generation(helper, uri):
    result = helper.ok('generatemodel', [uri, {'prompt':'hello world', 'max_new_tokens':4}])
    require(result.get('generated') is True and result.get('local_generate') is True,
            f'local generation did not complete: {result}')
    text = result.get('text', '')
    require(isinstance(text, str) and text.strip(), f'empty generated output: {result}')
    return {'text':text, 'backend':result.get('backend'), 'device':result.get('adapter', {}).get('device')}


def checkout(helper, uri, expected):
    result = helper.ok('exportmodelpath', [uri])
    path = Path(result['usable_runtime_root'])
    require(path.is_relative_to(helper.store), 'checkout escaped disposable store')
    observed = {name: digest(path/name, 'sha384') for name in expected}
    require(observed == expected, 'downloaded bytes differ from publisher')
    return observed


def run(root):
    binary, = (WORK/'package').glob('*/bin/btx-modeld')
    real = binary.parent.parent/'libexec/btx-modeld.real'
    receipt.update(wrapper_sha256=digest(binary),helper_sha256=digest(real))
    model = root/'workflowacceptance'
    phase('generate small SafeTensors fixture')
    create_model(model)
    expected = {p.name: digest(p,'sha384') for p in sorted(model.iterdir()) if p.is_file()}
    receipt['source_file_sha384'] = expected
    address = os.environ.get('BTX_TEST_PUBLISHER', '127.0.0.1')
    receipt['publisher_address'] = address
    with socket.socket() as sock:
        sock.bind((address,0))
        port = sock.getsockname()[1]
    publisher = Helper(binary, root/'publisher',OUT,'publisher',64<<20,hostport=port)
    publisher.hostaddr = address
    receiver = Helper(binary, root/'receiver',OUT,'receiver',64<<20,peer=f'{address}:{port}')
    try:
        phase('start packaged publisher and import')
        publisher.start()
        item = publisher.ok('importmodel',[str(model),{'pin':True,'publish':True}])
        uri = item['uri']
        require(item.get('seeded') and uri.startswith('btx://'),'publisher did not seed')
        receipt.update(model_id=item['model_id'],artifact_id=item['artifact_id'],uri=uri)
        local = publisher.ok('searchmodels', [{'scope':'LOCAL','limit':20}])
        require(uri in json.dumps(local['results']), 'publisher did not index the seeded model')
        receipt['publisher_local_search'] = local
        phase('start packaged receiver with empty library')
        receiver.start()
        require(not receiver.ok('listmodels')['models'],'receiver was not empty')
        phase('discover publisher over documented network search')
        end = time.monotonic()+10
        receipt['discovery_pass'] = False
        while True:
            found = receiver.ok('searchmodels',[{'scope':'NETWORK','limit':20}])
            receipt['search'] = found
            matches = [card for card in found['results'] if card.get('model_id') == item['model_id']
                       or card.get('btx_uri') == uri or uri in json.dumps(card)]
            if matches and found.get('remote_count',0)>0:
                receipt['discovery_pass'] = True
                break
            if time.monotonic() >= end:
                break
            time.sleep(.4)
        phase('download from discovered publisher' if receipt['discovery_pass'] else 'known-share retrieval control after search failed')
        jid, initial = receiver.request(uri)
        require(jid,'download did not create a job')
        final = receiver.settled(jid,35)
        receipt['download'] = final
        require(final.get('status')=='done',f'download did not complete: {final}')
        receipt['download_file_sha384'] = checkout(receiver,uri,expected)
        phase('run local CPU generation')
        first = generation(receiver,uri)
        receipt['before_restart'] = first
        phase('restart receiver and generate with publisher offline')
        receiver.stop()
        publisher.stop()
        receiver.start()
        require(len(receiver.ok('listmodels')['models']) == 1,'restart lost or duplicated model')
        receipt['restart_file_sha384'] = checkout(receiver,uri,expected)
        second = generation(receiver,uri)
        require(first == second,'deterministic generation changed after restart')
        receipt['after_restart'] = second
        receiver.stop()
        receipt['retrieve_generate_restart_pass'] = True
        receipt['pass'] = receipt['discovery_pass']
    finally:
        receiver.cleanup()
        publisher.cleanup()
        receipt['clean_shutdown'] = not any(h.forced or h.cleanup_error for h in (receiver,publisher))
        receipt['pass'] &= receipt['clean_shutdown']


def interrupted_download(root):
    from relay import Relay

    binary, = (WORK/'package').glob('*/bin/btx-modeld')
    real = binary.parent.parent/'libexec/btx-modeld.real'
    receipt.update(wrapper_sha256=digest(binary),helper_sha256=digest(real))
    model = root/'interruptionfixture'
    create_model(model, wide=True)
    expected = {p.name: digest(p,'sha384') for p in sorted(model.iterdir()) if p.is_file()}
    total = sum((model/name).stat().st_size for name in expected)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port = sock.getsockname()[1]
    publisher = Helper(binary,root/'publisher',OUT,'publisher',64<<20,hostport=port)
    relay = Relay(port,rate=128<<10)
    receiver = Helper(binary,root/'receiver',OUT,'receiver',64<<20,peer=f'127.0.0.1:{relay.port}')
    try:
        phase('start interrupted download from an empty library')
        publisher.start()
        receiver.start()
        require(not receiver.ok('listmodels')['models'],'receiver was not empty')
        item = publisher.ok('importmodel',[str(model),{'pin':True,'publish':True}])
        uri = item['uri']
        jid, _ = receiver.request(uri)
        require(jid,'no download job')
        until = time.monotonic()+30
        while True:
            job = receiver.job(jid)
            if job.get('status')=='running' and 0 < job.get('bytes_committed',0) < total:
                relay.call(relay.interrupt())
                if relay.closed_streams:
                    break
                relay.call(relay.resume())
            require(job.get('status') not in ('done','failed','cancelled')
                    and time.monotonic()<until, f'did not interrupt active transfer: {job}')
            time.sleep(.06)
        receipt.update(committed_at_interrupt=job['bytes_committed'],total_bytes=total,
                       interrupted_streams=relay.closed_streams,original_job_id=jid)
        phase('hold publisher connection closed and observe job outcome')
        time.sleep(1)
        end = time.monotonic()+8
        while True:
            during = receiver.job(jid)
            require(during.get('status')!='done','download finished while disconnected')
            if during.get('status') in ('failed','cancelled') or time.monotonic()>=end:
                break
            time.sleep(.2)
        receipt['outage_status'] = during.get('status')
        relay.call(relay.resume())
        phase('restore publisher connection and verify recovery')
        if during.get('status') in ('failed','cancelled'):
            recovered, _ = receiver.request(uri)
        else:
            recovered = jid
        final = receiver.settled(recovered,40)
        if final.get('status')=='failed' and recovered==jid:
            recovered, _ = receiver.request(uri)
            final = receiver.settled(recovered,40)
        receipt.update(recovered_job_id=recovered,final_job=final)
        require(final.get('status')=='done',f'recovery failed: {final}')
        require(recovered == jid, 'Download needed a replacement job')
        receipt['source_file_sha384'] = expected
        receipt['recovered_file_sha384'] = checkout(receiver,uri,expected)
        require(len(receiver.ok('listmodels')['models'])==1,'duplicate or missing model after retry')
        receiver.stop()
        publisher.stop()
        receiver.start()
        receipt['restart_file_sha384'] = checkout(receiver,uri,expected)
        require(len(receiver.ok('listmodels')['models'])==1,'duplicate or missing model after restart')
        receiver.stop()
        receipt['pass'] = True
    finally:
        relay.close()
        receiver.cleanup()
        publisher.cleanup()
        receipt['clean_shutdown'] = not any(h.forced or h.cleanup_error for h in (receiver,publisher))
        receipt['pass'] &= receipt['clean_shutdown']


try:
    with tempfile.TemporaryDirectory(prefix='btx-model-accept-') as name:
        if os.environ.get('BTX_TEST_INTERRUPTION') == '1':
            interrupted_download(Path(name))
        else:
            run(Path(name))
except Exception as error:
    receipt['error'] = str(error)
    raise
finally:
    (OUT/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert receipt['pass']
