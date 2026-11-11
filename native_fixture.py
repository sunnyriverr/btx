"""Run the documented zero-wallet model workflow on the published helper."""
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import time

from helpers import Helper, digest, require

WORK = Path.cwd()
OUT = WORK / 'evidence'
receipt = {'pass': False, 'archive_sha256': '0552bcbceef9fab5a6b9e24f26f4ccf7e615437e5d4c4af608a6247d5c21e6dc'}


def phase(name):
    receipt['last_stage'] = name
    print(name, flush=True)
    (OUT/'result.json').write_text(json.dumps(receipt, indent=2)+'\n')


def create_model(path):
    import torch
    from tokenizers import Tokenizer, models, pre_tokenizers
    from transformers import GPT2Config, GPT2LMHeadModel, PreTrainedTokenizerFast

    torch.manual_seed(43)
    vocab = {'[UNK]': 0, '[PAD]': 1, 'hello': 2, 'world': 3}
    vocab.update({f'word{i}': i for i in range(4, 32)})
    raw = Tokenizer(models.WordLevel(vocab, unk_token='[UNK]'))
    raw.pre_tokenizer = pre_tokenizers.Whitespace()
    tok = PreTrainedTokenizerFast(tokenizer_object=raw, unk_token='[UNK]', pad_token='[PAD]')
    config = GPT2Config(vocab_size=len(vocab), n_positions=32, n_embd=24, n_layer=1, n_head=2,
                        bos_token_id=None, eos_token_id=None, pad_token_id=1)
    GPT2LMHeadModel(config).eval().save_pretrained(path, safe_serialization=True)
    tok.save_pretrained(path)


def generation(helper, uri):
    result = helper.ok('generatemodel', [uri, {'prompt':'hello world', 'max_new_tokens':4}])
    require(result.get('generated') is True and result.get('local_generate') is True,
            f'local generation did not complete: {result}')
    text = result.get('text', '')
    require(isinstance(text, str) and text.strip(), f'empty generated output: {result}')
    return {'text':text, 'backend':result.get('backend'), 'device':result.get('device')}


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
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port = sock.getsockname()[1]
    publisher = Helper(binary, root/'publisher',OUT,'publisher',64<<20,hostport=port)
    receiver = Helper(binary, root/'receiver',OUT,'receiver',64<<20,peer=f'127.0.0.1:{port}')
    try:
        phase('start packaged publisher and import')
        publisher.start()
        item = publisher.ok('importmodel',[str(model),{'pin':True,'publish':True}])
        uri = item['uri']
        require(item.get('seeded') and uri.startswith('btx://'),'publisher did not seed')
        receipt.update(model_id=item['model_id'],artifact_id=item['artifact_id'],uri=uri)
        phase('start packaged receiver with empty library')
        receiver.start()
        require(not receiver.ok('listmodels')['models'],'receiver was not empty')
        phase('discover publisher over documented network search')
        end = time.monotonic()+20
        while True:
            found = receiver.ok('searchmodels',[{'scope':'NETWORK','limit':20}])
            receipt['search'] = found
            matches = [card for card in found['results'] if card.get('model_id') == item['model_id']
                       or card.get('btx_uri') == uri or uri in json.dumps(card)]
            if matches and found.get('remote_count',0)>0:
                break
            require(time.monotonic()<end,'known publisher missing from network search')
            time.sleep(.4)
        phase('download from discovered publisher')
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
        receipt['pass'] = True
    finally:
        receiver.cleanup()
        publisher.cleanup()
        receipt['clean_shutdown'] = not any(h.forced or h.cleanup_error for h in (receiver,publisher))
        receipt['pass'] &= receipt['clean_shutdown']


try:
    with tempfile.TemporaryDirectory(prefix='btx-model-accept-') as name:
        run(Path(name))
except Exception as error:
    receipt['error'] = str(error)
    raise
finally:
    (OUT/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert receipt['pass']
