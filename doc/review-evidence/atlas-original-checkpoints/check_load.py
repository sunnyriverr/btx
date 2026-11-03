from pathlib import Path
import sys,json,time,hashlib,resource,importlib.metadata,traceback
import torch
from transformers import AutoTokenizer,AutoModelForCausalLM
O=Path(__file__).resolve().parent;root=O/'models'/sys.argv[1]
sys.path.insert(0,str(O/'source/contrib/atlas/neuronlab'))
from btx_neuronlab.models import load_local
start=time.monotonic();torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.manual_seed(42)
def hashes():
 return {p.name:hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in root.iterdir() if p.is_file()}
original=hashes();result={'model':sys.argv[1],'entrypoint':'btx_neuronlab.models.load_local','device':'cpu','threads':1,'versions':{n:importlib.metadata.version(n) for n in ['torch','transformers','safetensors','tokenizers','numpy','huggingface-hub']},'source_commit':'afd6591970e7f8d65871412b9d7cf03b48f30b97','source_models_sha256':hashlib.sha256((O/'source/contrib/atlas/neuronlab/btx_neuronlab/models.py').read_bytes()).hexdigest()}
try:
 model,tokenizer,adapter,binding=load_local(root,device='cpu')
 assert tokenizer is not None and adapter is not None
 assert binding['architecture']=='GPTNeoXForCausalLM'
 ids=tokenizer('The purpose of this test is to load a local model.',return_tensors='pt')['input_ids'][:,:12]
 assert 1<ids.shape[1]<=12
 with torch.inference_mode():actual=model(ids).logits
 # One independent normal-framework load of the same original files; no re-save.
 reference=AutoModelForCausalLM.from_pretrained(str(root),local_files_only=True,trust_remote_code=False,use_safetensors=True,torch_dtype=torch.float32).eval()
 reference_tokenizer=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
 assert torch.equal(ids,reference_tokenizer('The purpose of this test is to load a local model.',return_tensors='pt')['input_ids'][:,:12])
 state=model.state_dict();ref=reference.state_dict();assert set(state)==set(ref)
 assert all(torch.equal(t,ref[k]) for k,t in state.items())
 with torch.inference_mode():expected=reference(ids).logits
 assert torch.isfinite(actual).all() and torch.equal(actual,expected)
 assert adapter.output_weight().shape==model.get_output_embeddings().weight.shape
 assert original==hashes()
 result.update(status='PASS',model_binding=binding,token_ids=ids.tolist(),learned_tensors_compared=len(state),all_tensors_exact=True,logits_shape=list(actual.shape),max_logit_delta=(actual-expected).abs().max().item(),argmax_ids=actual.argmax(-1).tolist(),tokenizer_matches=True,checkpoint_files_unchanged=True,adapter_output_shape=list(adapter.output_weight().shape))
except Exception:
 result.update(status='ERROR',error=traceback.format_exc());raise
finally:
 result.update(elapsed_seconds=time.monotonic()-start,max_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
 (O/(sys.argv[1]+'-load.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result.get(k) for k in ['model','status','elapsed_seconds','max_rss_bytes','max_logit_delta']},indent=2))
