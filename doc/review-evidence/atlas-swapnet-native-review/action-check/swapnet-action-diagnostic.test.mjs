import {test} from 'node:test';
import assert from 'node:assert/strict';
import {swapnetView} from '../web/views/swapnet.js';
import {OPERATIONS} from '../web/core/catalog.js';
import {installDom, fieldInput, buttonNamed, fire, settle, findAll} from './dom-stub.mjs';

// Exercise the real JS Bridge; replace only the Tauri/native invocation boundary.
// This controlled boundary is not execution of Rust, a confirmation window or RPC.
let current;
globalThis.__TAURI__={core:{invoke:(command,args)=>current.invoke(command,args)}};
const {Bridge}=await import('../web/core/bridge.js?swapnet-action-diagnostic');
const SWAP='a'.repeat(64), QUOTE='b'.repeat(64), MANDATE='c'.repeat(64);
function setup({outcome='success',prepareWait=null}={}) {
  installDom();
  const runtime={calls:[],prepared:null,submitted:[],
    async invoke(command,args) {
      this.calls.push({command,args:structuredClone(args)});
      if(command==='atlas_read')return {ok:true,epoch:7,result:{diagnostic:true}};
      if(command==='atlas_prepare') {
        this.prepared=structuredClone(args.request);
        if(prepareWait)await prepareWait;
        return {id:'prepared-diagnostic-000001',wallet:this.prepared.wallet,method:this.prepared.method};
      }
      if(command==='atlas_execute') {
        assert.deepEqual(args,{id:'prepared-diagnostic-000001'});
        if(outcome==='CANCELLED')throw {code:'CANCELLED',message:'Cancelled in the native confirmation dialog',outcome_unknown:false};
        if(outcome==='CONNECTION_CHANGED')throw {code:outcome,message:'Approval belongs to another connection',outcome_unknown:false};
        this.submitted.push(structuredClone(this.prepared));
        if(outcome==='RPC_-1')throw {code:'RPC_-1',message:'WALLET_SCOPE: RPC wallet differs from the bound SwapNet wallet',outcome_unknown:false};
        if(outcome==='OUTCOME_UNKNOWN')throw {code:outcome,message:'Request delivery failed; do not automatically retry a mutation',outcome_unknown:true};
        return {ok:true,epoch:7,result:{diagnostic_operation:this.prepared.method,swap_id:SWAP,state:'diagnostic-result'}};
      }
      throw Error('Unexpected native command '+command);
    },
  };
  current=runtime;
  const bridge=new Bridge();bridge.available=new Set(OPERATIONS.map(o=>o.method));
  const app={bridge,state:{state:{wallet:'bound wallet'}},refreshed:0,refreshSoon(){this.refreshed++;}};
  return {app,runtime};
}
async function openFromPage(app,method) {
  const root=swapnetView(app);await settle();
  const entry=buttonNamed(root,method);assert.ok(entry,'Missing SwapNet page entry');
  fire(entry,'click');
  const dialogs=findAll(document.body,n=>n.tagName==='DIALOG'&&n.open);
  assert.equal(dialogs.length,1);return dialogs[0];
}
const mutationCalls = r=>r.calls.filter(c=>c.command!=='atlas_read');
const runButton = d=>buttonNamed(d,'Prepare for native review');

// Equivalent JSON request shapes are grouped; do not rerun the already-qualified
// password/export controls or the status-page tests.
const shapes=[
  ['requestswapquote',{sell_asset:'btx:diagnostic:0:native',buy_asset:'btc:diagnostic:0:native',sell_atoms:'9007199254740993'},null],
  ['acceptswapquote',{quote_id:QUOTE,mandate_id:MANDATE,max_local_fee_atoms:'9007199254740993'},null],
  ['refundswap',{swap_id:SWAP},'explicit wallet'],
  ['createswapmandate',{mandate:{principal:'owner:cookie',asset:'diagnostic-asset',max_total_atoms:'200000',max_trade_atoms:'100000',max_fee_atoms:'10000',expires_at:1900000000,nonce:'d'.repeat(64)}},null],
  ['publishswapprovider',undefined,''],
  ['getswapwalletinfo',{},null],
];
for(const [method,request,override] of shapes)test(`page → form → real Bridge preserves ${method} request and context`,async()=>{
  const {app,runtime}=setup();const d=await openFromPage(app,method);
  assert.deepEqual(mutationCalls(runtime),[],'Opening an action must not prepare or execute it');
  assert.equal(buttonNamed(d,'Read observation'),undefined);
  if(request!==undefined)fieldInput(d,'request').value=JSON.stringify(request);
  if(override!==null)fieldInput(d,'Wallet context (blank means node endpoint)').value=override;
  fire(runButton(d),'click');await settle();
  assert.deepEqual(mutationCalls(runtime).map(c=>c.command),['atlas_prepare','atlas_execute']);
  const params=request===undefined?[]:[request];
  assert.equal(runtime.prepared.method,method);
  assert.equal(runtime.prepared.wallet,override===null?'bound wallet':override||null);
  assert.deepEqual(JSON.parse(runtime.prepared.params_json),params);
  assert.deepEqual(runtime.submitted,[runtime.prepared]);
  assert.ok(d.textContent.includes('diagnostic-result'));assert.equal(app.refreshed,1);
});

test('editing form/global wallet while prepare awaits does not rewrite the prepared operation',async()=>{
  let release;const wait=new Promise(resolve=>{release=resolve;});
  const {app,runtime}=setup({prepareWait:wait});const d=await openFromPage(app,'refundswap');
  fieldInput(d,'request').value=JSON.stringify({swap_id:SWAP});
  fire(runButton(d),'click');await settle();
  assert.equal(runButton(d).disabled,true);
  assert.deepEqual(mutationCalls(runtime).map(c=>c.command),['atlas_prepare']);
  fieldInput(d,'request').value=JSON.stringify({swap_id:'e'.repeat(64)});
  fieldInput(d,'Wallet context (blank means node endpoint)').value='different wallet';
  app.state.state.wallet='another wallet';release();await settle();
  assert.equal(runtime.prepared.wallet,'bound wallet');
  assert.deepEqual(JSON.parse(runtime.prepared.params_json),[{swap_id:SWAP}]);
  assert.deepEqual(runtime.submitted,[runtime.prepared]);
});

for(const outcome of ['CANCELLED','CONNECTION_CHANGED','RPC_-1','OUTCOME_UNKNOWN'])test(`real Bridge preserves ${outcome} and the form never automatically retries`,async()=>{
  const {app,runtime}=setup({outcome});const d=await openFromPage(app,'refundswap');
  fieldInput(d,'request').value=JSON.stringify({swap_id:SWAP});
  fire(runButton(d),'click');await settle();await settle();
  assert.deepEqual(mutationCalls(runtime).map(c=>c.command),['atlas_prepare','atlas_execute']);
  assert.equal(runtime.submitted.length,['CANCELLED','CONNECTION_CHANGED'].includes(outcome)?0:1);
  assert.ok(d.textContent.includes(outcome));
  assert.equal(d.textContent.includes('diagnostic-result'),false);
  assert.equal(app.refreshed,0);assert.equal(runButton(d).disabled,false);
  if(outcome==='OUTCOME_UNKNOWN')assert.ok(d.textContent.includes('DO NOT RETRY. Reconcile'));
});

test('a failed prepare does not execute and a later healthy attempt keeps its new request',async()=>{
  const {app,runtime}=setup();const invoke=runtime.invoke.bind(runtime);let reject=true;
  runtime.invoke=async(command,args)=>{
    if(command==='atlas_prepare'&&reject){runtime.calls.push({command,args:structuredClone(args)});throw {code:'QUEUE_FULL',message:'At most sixteen pending approvals',outcome_unknown:false};}
    return invoke(command,args);
  };
  const d=await openFromPage(app,'refundswap');fieldInput(d,'request').value=JSON.stringify({swap_id:SWAP});
  fire(runButton(d),'click');await settle();assert.ok(d.textContent.includes('QUEUE_FULL'));
  assert.equal(runtime.calls.filter(c=>c.command==='atlas_execute').length,0);
  assert.equal(app.refreshed,0);reject=false;
  const changed='f'.repeat(64);fieldInput(d,'request').value=JSON.stringify({swap_id:changed});
  fire(runButton(d),'click');await settle();
  assert.deepEqual(JSON.parse(runtime.prepared.params_json),[{swap_id:changed}]);
  assert.equal(runtime.calls.filter(c=>c.command==='atlas_execute').length,1);
  assert.ok(d.textContent.includes('diagnostic-result'));assert.equal(app.refreshed,1);
});
