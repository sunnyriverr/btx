from pathlib import Path
import functools,importlib.util,json,os,sys,time
ROOT=Path(os.environ['GITHUB_WORKSPACE']);HERE=Path(__file__).parent;PRODUCT=ROOT/'p2mr-parent-product';OUT=ROOT/'rpc-help-live-results';variant=os.environ['RPC_VARIANT'];events=[]
sys.path.insert(0,str(PRODUCT/'test/functional'))
spec=importlib.util.spec_from_file_location('qualified_help',HERE/(variant+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
cls=m.HelpRpcTest
original_params=cls.set_test_params
# Help metadata requires no mined chain or external service. Same fixture on both variants.
def params(self):
 original_params(self);self.setup_clean_chain=True;self.extra_args=[['-modelnet=0','-connect=0','-dnsseed=0','-discover=0']]
cls.set_test_params=params
for name in ['test_client_conversion_table','test_argument_names','test_categories','dump_help','wallet_help']:
 if not hasattr(cls,name):continue
 original=getattr(cls,name)
 @functools.wraps(original)
 def wrapped(self,original=original,name=name):
  item={'name':name,'start':time.time()};events.append(item)
  try:
   if name=='test_client_conversion_table':
    (OUT/(variant+'-server-map.json')).write_text(json.dumps(self.nodes[0].help('dump_all_command_conversions')))
   result=original(self);item['result']='pass';return result
  except Exception as e:item.update(result='fail',error=str(e));raise
  finally:
   item['end']=time.time();(OUT/(variant+'-stages.json')).write_text(json.dumps(events,indent=2))
 setattr(cls,name,wrapped)
cls(__file__).main()
