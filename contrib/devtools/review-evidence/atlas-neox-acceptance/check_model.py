from pathlib import Path
import json,sys,hashlib,shutil,importlib.metadata,traceback
import torch,transformers
from transformers import GPTNeoXConfig,GPTNeoXForCausalLM,PreTrainedTokenizerFast
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from safetensors.torch import load_file,save_file
ROOT=Path(__file__).resolve().parent;torch.set_num_threads(1);torch.manual_seed(42)
mode,fixture=sys.argv[1:3];root=ROOT/'fixtures'/fixture
versions={n:importlib.metadata.version(n) for n in ['torch','transformers','safetensors','tokenizers','numpy','huggingface-hub']}
if mode=='save':
 tied=sys.argv[3]=='tied';root.mkdir(parents=True,exist_ok=False)
 cfg=GPTNeoXConfig(vocab_size=32,hidden_size=32,intermediate_size=64,num_hidden_layers=1,num_attention_heads=4,max_position_embeddings=64,tie_word_embeddings=tied,attention_dropout=0.0,hidden_dropout=0.0,bos_token_id=1,eos_token_id=2)
 model=GPTNeoXForCausalLM(cfg).eval();model.save_pretrained(root,safe_serialization=True)
 tok=Tokenizer(WordLevel({'[UNK]':0,'[BOS]':1,'[EOS]':2,**{f'tok{i}':i for i in range(3,32)}},unk_token='[UNK]'));tok.pre_tokenizer=Whitespace()
 tokenizer=PreTrainedTokenizerFast(tokenizer_object=tok,unk_token='[UNK]',bos_token='[BOS]',eos_token='[EOS]');tokenizer.save_pretrained(root)
 keys=list(load_file(str(root/'model.safetensors')))
 result={'fixture':fixture,'versions':versions,'tied':tied,'file_keys':keys,'live_keys':list(model.state_dict()),'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir() if p.is_file()}}
 (ROOT/(fixture+'-saved.json')).write_text(json.dumps(result,indent=2));print('saved',fixture)
elif mode=='check':
 profile,label=sys.argv[3:5];sys.path.insert(0,str(ROOT/profile/'contrib/atlas/neuronlab'))
 from btx_neuronlab.models import load_local
 from btx_neuronlab.codec import LabError
 result={'profile':profile,'fixture':fixture,'versions':versions,'source_models_sha384':hashlib.sha384((ROOT/profile/'contrib/atlas/neuronlab/btx_neuronlab/models.py').read_bytes()).hexdigest()}
 try:
  model,tokenizer,adapter,binding=load_local(root,device='cpu')
  reference=GPTNeoXForCausalLM.from_pretrained(root,local_files_only=True,trust_remote_code=False,use_safetensors=True,torch_dtype=torch.float32).eval()
  weights_equal=all(torch.equal(v,reference.state_dict()[k]) for k,v in model.state_dict().items());assert weights_equal
  ids=torch.tensor([[1,3,4,5,2]])
  with torch.no_grad():a=model(ids).logits;b=reference(ids).logits
  assert torch.allclose(a,b,atol=1e-6,rtol=1e-5)
  assert model.get_input_embeddings().weight.data_ptr()==model.get_output_embeddings().weight.data_ptr() if model.config.tie_word_embeddings else model.get_input_embeddings().weight.data_ptr()!=model.get_output_embeddings().weight.data_ptr()
  result.update(status='PASS',weights_equal=True,max_logit_delta=(a-b).abs().max().item(),tied=model.config.tie_word_embeddings,fingerprint=binding['execution_fingerprint'])
 except LabError as e:result.update(status='REFUSED',code=e.code,cause=str(e.__cause__))
 except Exception:result.update(status='ERROR',error=traceback.format_exc())
 (ROOT/(label+'.json')).write_text(json.dumps(result,indent=2));print(label,result['status'])
elif mode=='mutate':
 source=ROOT/'fixtures'/'521-untied';shutil.copytree(source,root);state=load_file(str(root/'model.safetensors'))
 kind=sys.argv[3]
 if kind=='extra':state['unrelated.extra.weight']=torch.zeros(1)
 elif kind=='missing':state.pop('gpt_neox.embed_in.weight')
 elif kind=='head':state.pop('embed_out.weight')
 save_file(state,str(root/'model.safetensors'),metadata={'format':'pt'});print('mutated',fixture,kind)
