import {test} from 'node:test';
import assert from 'node:assert/strict';
import {swapnetView} from '../web/views/swapnet.js';
import {installDom, findAll, buttonNamed, fire, settle} from './dom-stub.mjs';

const METHODS = ['getswapnetworkinfo', 'getswapbootstrapinfo', 'getswapvalidationinfo', 'getswaphealth', 'listswapassets', 'getswapcapabilities'];
const FIXTURES = {
  getswapnetworkinfo: {version:'2.0.0', protocol:2, peers:0, providers:0, automatic_spend_atoms:'0', in_process:true, wallet_loaded:false, wallet_warning:'No wallet loaded'},
  getswapbootstrapinfo: {mechanism:'existing_btx_peers', separate_seeds:false, admitted_peers:0, fabricated_liquidity:false, discovery:'awaiting_compatible_peer'},
  getswapvalidationinfo: {source_version:'2.0.0', client_version:'v0.34.17', runtime_observations_are_not_release_certification:true, protocol_profile:'native-btx-btc-eth-htlc-v2'},
  getswaphealth: {audit_head:'diagnostic-audit-head', database_schema:2, last_tick_error:'RPC_UNAVAILABLE', pending_outbox:2, sessions:3},
  listswapassets: {assets:[{asset:'btx:diagnostic:0:native', family:'btx', ready:false, reason:'WALLET_LOCKED'}], unknown_assets_enabled:false},
  getswapcapabilities: {methods:[{name:'getswaphealth',scope:'read'}], settlement:['sha256-htlc-v1'], partial_fills:false, multihop_settlement:false},
};

function appWith(reply) {
  const reads=[], writes=[];
  const forbidden = name => async (...args) => {writes.push([name,...args]); throw Error('Unexpected mutation from status page');};
  return {
    reads, writes,
    bridge: {
      read: async (method, params) => {reads.push({method,params}); return reply(method, reads.length);},
      prepare:forbidden('prepare'), execute:forbidden('execute'), cancel:forbidden('cancel'),
    },
  };
}
const panels = root => findAll(root, n=>n.tagName==='SECTION' && n.className==='panel');
const records = root => findAll(root,n=>n.tagName==='DETAILS' && n.className==='json');
function checkSequence(app, cycles=1) {
  assert.deepEqual(app.reads.map(r=>r.method),Array.from({length:cycles},()=>METHODS).flat());
  for(const r of app.reads)assert.deepEqual(r.params,[]);
  assert.deepEqual(app.writes,[]);
}
function checkRecord(panel, value) {
  const pre=findAll(panel,n=>n.tagName==='PRE');
  assert.equal(pre.length,1);
  assert.deepEqual(JSON.parse(pre[0].textContent),value);
  const details=records(panel);assert.equal(details.length,1);
  assert.equal(details[0].getAttribute('open'),null,'records are collapsed, not promoted to visible summary metrics');
}

test('all six status envelopes reach exact native records without authorization calls',async()=>{
  installDom();
  const app=appWith(method=>({ok:true,epoch:3,observed_at:123,result:FIXTURES[method]}));
  const root=swapnetView(app);await settle();
  assert.equal(panels(root).length,6);assert.equal(records(root).length,6);
  METHODS.forEach((method,i)=>{
    checkRecord(panels(root)[i],FIXTURES[method]);
    assert.ok(panels(root)[i].textContent.includes(method));
  });
  assert.ok(root.textContent.includes('not release qualification'));
  assert.equal(buttonNamed(root,'Refresh').disabled,false);
  checkSequence(app);
});

test('legacy bare replies retain unavailable/awaiting/error/false fields without invented healthy metrics',async()=>{
  installDom();const app=appWith(method=>FIXTURES[method]);
  const root=swapnetView(app);await settle();
  METHODS.forEach((method,i)=>checkRecord(panels(root)[i],FIXTURES[method]));
  assert.ok(root.textContent.includes('awaiting_compatible_peer'));
  assert.ok(root.textContent.includes('WALLET_LOCKED'));
  assert.ok(root.textContent.includes('RPC_UNAVAILABLE'));
  assert.ok(root.textContent.includes('No wallet loaded'));
  assert.equal(findAll(root,n=>n.className==='metrics').length,0);
  checkSequence(app);
});

for(const failed of METHODS) {
  test(`one rejected ${failed} read is explicit and preserves the other five`,async()=>{
    installDom();const message=`diagnostic ${failed} unavailable`;
    const app=appWith(method=>{if(method===failed)throw Object.assign(Error(message),{code:'RPC_UNAVAILABLE'});return {result:FIXTURES[method]};});
    const root=swapnetView(app);await settle();
    const shown=panels(root);assert.equal(shown.length,6);assert.equal(records(root).length,5);
    METHODS.forEach((method,i)=>{
      if(method===failed) {
        assert.ok(shown[i].textContent.includes(message));
        assert.equal(records(shown[i]).length,0);
        assert.equal(findAll(shown[i],n=>n.className==='note warning').length,1);
      } else checkRecord(shown[i],FIXTURES[method]);
    });
    assert.equal(buttonNamed(root,'Refresh').disabled,false);checkSequence(app);
  });
}

test('disabled/disconnected reads produce six warnings and no successful native records',async()=>{
  installDom();const app=appWith(()=>{throw Object.assign(Error('SwapNet is unavailable on this connection'),{code:'RPC'});});
  const root=swapnetView(app);await settle();
  assert.equal(panels(root).length,6);assert.equal(records(root).length,0);
  assert.equal(findAll(root,n=>n.className==='note warning').length,6);
  assert.equal(root.textContent.includes('diagnostic-audit-head'),false);
  assert.equal(buttonNamed(root,'Refresh').disabled,false);checkSequence(app);
});

test('refresh discards old healthy records on error and recovers with new responses',async()=>{
  installDom();let phase=0;
  const app=appWith(method=>{
    if(phase===1 && method==='getswaphealth')throw Error('health temporarily unavailable');
    return {result:{...FIXTURES[method],diagnostic_generation:phase}};
  });
  const root=swapnetView(app);await settle();
  const refresh=buttonNamed(root,'Refresh');
  phase=1;fire(refresh,'click');
  assert.equal(refresh.disabled,true);assert.equal(records(root).length,0);
  assert.ok(root.textContent.includes('Reading this node'));
  await settle();assert.equal(records(root).length,5);
  assert.ok(root.textContent.includes('health temporarily unavailable'));
  assert.equal(root.textContent.includes('"diagnostic_generation": 0'),false);
  phase=2;fire(refresh,'click');await settle();
  assert.equal(records(root).length,6);
  assert.equal(root.textContent.includes('health temporarily unavailable'),false);
  METHODS.forEach((method,i)=>checkRecord(panels(root)[i],{...FIXTURES[method],diagnostic_generation:2}));
  assert.equal(refresh.disabled,false);checkSequence(app,3);
});

test('a pending read remains explicitly loading until it completes, then restores refresh',async()=>{
  installDom();let release;
  const pending=new Promise(resolve=>{release=resolve;});
  const app=appWith(async method=>{if(method==='getswapbootstrapinfo')await pending;return {result:FIXTURES[method]};});
  const root=swapnetView(app);await settle();
  assert.equal(app.reads.length,2);
  assert.ok(root.textContent.includes('Reading this node'));
  assert.equal(buttonNamed(root,'Refresh').disabled,true);
  assert.equal(records(root).length,0);
  release();await settle();
  assert.equal(records(root).length,6);
  assert.equal(buttonNamed(root,'Refresh').disabled,false);checkSequence(app);
});
