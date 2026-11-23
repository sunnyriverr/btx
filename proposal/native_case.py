"""One disposable BTX daemon/CLI and Anvil refund-withdrawal retry case."""
from dataclasses import asdict
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import time

from anvil_check import AMOUNT, CLAIM_CAP, CREATION_PIN, LocalRPC, RUNTIME_PIN
from swapnet.canonical import digest
from swapnet.evm import address_bytes, calldata, keccak256
from swapnet.evm_driver import EVMDriver, ZERO
from swapnet.journal import Journal
from swapnet.store import Store
from swapnet.terms import Agreement, LegTerms
from swapnet.vault import ForeignKeyVault

WALLET = 'refund-fixture'
USER = 'restricted-fixture'
HEAD = 'a02fded5d9216f79cde4cc3620bc3941aa94209d'
BTX_GENESIS = '521ad0951ed299e9c56aeb7db8188972772067560351b8e55adf71dbed532360'
SID = '45' * 32
WITHDRAW = keccak256(b'withdrawAmount(address,address,uint256)')[:4].hex()


def wait_until(fn, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = fn()
        if result:
            return result
        time.sleep(0.15)
    raise TimeoutError('Expected observation did not appear')


class CliError(Exception):
    pass


class Node:
    def __init__(self, root, daemon, cli):
        self.data = root / 'node'
        self.data.mkdir(mode=0o700)
        self.home = root / 'home'
        self.home.mkdir(mode=0o700)
        self.daemon, self.client = daemon, cli
        self.process = None
        with socket.socket() as temp:
            temp.bind(('127.0.0.1',0))
            self.port = temp.getsockname()[1]
        self.password = secrets.token_urlsafe(24)
        salt = secrets.token_hex(16)
        secret = hmac.digest(salt.encode(),self.password.encode(),'sha256').hex()
        (self.data/'btx.conf').write_text(f'rpcauth={USER}:{salt}${secret}:{WALLET}\nswapnetowner={USER}\n')
        (self.data/'btx.conf').chmod(0o600)

    def call(self, method, *params, restricted=False):
        argv = [self.client,'-regtest',f'-datadir={self.data}','-conf=btx.conf',f'-rpcport={self.port}']
        if restricted:
            argv += [f'-rpcwallet={WALLET}',f'-rpcuser={USER}',f'-rpcpassword={self.password}']
        encode=lambda value:value if isinstance(value,str) else json.dumps(value,separators=(',',':'))
        p=subprocess.run([*argv,method,*map(encode,params)],capture_output=True,text=True,timeout=18)
        if p.returncode:
            raise CliError(p.stderr.strip())
        if not p.stdout.strip():
            return None
        try:
            return json.loads(p.stdout)
        except json.JSONDecodeError:
            return p.stdout.strip()

    def start(self, swapnet):
        env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','LD_PRELOAD')}
        env['HOME']=str(self.home)
        flags=['-regtest',f'-datadir={self.data}','-conf=btx.conf',f'-rpcport={self.port}','-rpcbind=127.0.0.1',
               '-listen=0','-connect=0','-dnsseed=0','-discover=0','-modelnet=0','-autoupdate=0',
               '-par=1','-autoshieldcoinbase=0','-dbcache=16','-regtestmatmulbindingheight=2147483647',
               '-regtestmatmulproductdigestheight=2147483647','-regtestmatmulv4height=2147483647',
               '-regtestmatmulrequireproductpayload=0']
        helptext=subprocess.run([self.daemon,'-help'],env=env,capture_output=True,text=True,timeout=10,check=True).stdout
        if '\n  -modelnet' not in helptext:
            flags.remove('-modelnet=0')
        if swapnet:
            flags+=['-swapnet=1',f'-swapnetwallet={WALLET}',f'-wallet={WALLET}']
            if '\n  -swapnetmode' in helptext:
                flags.append('-swapnetmode=recovery')
        else:
            flags+=['-swapnet=0']
        launch_log=self.data/'launch.log'
        with launch_log.open('w') as stream:
            self.process=subprocess.Popen([self.daemon,*flags],cwd=self.data,env=env,
                                          stdout=stream,stderr=stream)
        def ready():
            if self.process.poll() is not None:
                detail=next((line for line in reversed(launch_log.read_text().splitlines()) if 'Error:' in line),'no startup error text')
                raise RuntimeError(f'Daemon exited ({self.process.returncode}): {detail}')
            try:
                return self.call('getblockchaininfo')
            except CliError:
                return None
        assert wait_until(ready)['chain']=='regtest'
        assert self.call('getblockhash',0)==BTX_GENESIS

    def stop(self):
        if self.process is None or self.process.poll() is not None:
            return
        try:
            self.call('stop')
            assert self.process.wait(timeout=15)==0
        finally:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)


def proxy_for(eth, fault):
    class Proxy(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            method,args=request['method'],request.get('params',[])
            response={'jsonrpc':'2.0','id':request['id']}
            try:
                result=eth(method,*args)
                if (method=='eth_estimateGas' and args[0].get('data','').startswith('0x'+WITHDRAW)
                        and not fault and int(result,16)>25_200):
                    fault.append(int(result,16))
                    result=hex(21_000)
                response['result']=result
            except RuntimeError:
                response['error']={'code':-32000,'message':'Local Anvil request failed'}
            data=json.dumps(response).encode()
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    return ThreadingHTTPServer(('127.0.0.1',0),Proxy)


def seed_refunded_swap(node, eth, proxy, compiled_contract):
    directory=node.data/'regtest'/'swapnet'
    directory.mkdir(mode=0o700,exist_ok=True)
    master=(directory/'vault.key').read_bytes()
    store=Store(directory/'state.sqlite')
    try:
        journal=Journal(store)
        vault=ForeignKeyVault(directory/'foreign-vault.json',master)
        creation=compiled_contract['bytecode']['object']
        assert keccak256(bytes.fromhex(creation.removeprefix('0x'))).hex()==CREATION_PIN
        relay=eth('eth_accounts')[0].lower()
        deploy=eth.receipt(eth('eth_sendTransaction',{'from':relay,'data':'0x'+creation.removeprefix('0x'),
                                                     'gas':'0x600000'}))
        assert deploy['status']=='0x1'
        contract=deploy['contractAddress'].lower()
        assert keccak256(bytes.fromhex(eth('eth_getCode',contract,'latest')[2:])).hex()==RUNTIME_PIN
        genesis=eth('eth_getBlockByNumber','0x0',False)['hash'][2:]
        asset=f'evm:{genesis}:31337:native'
        # A legacy saved policy is sufficient for existing obligations.
        policy={'asset':asset,'rpc_url':proxy,'contract':contract,'runtime_hash':RUNTIME_PIN}
        journal.set_setting('asset_policies',{asset:policy})
        fixture=EVMDriver(asset,eth,journal,vault,contract,RUNTIME_PIN)
        key=fixture.new_key('refund')
        beneficiary=key['public']
        eth('anvil_setBalance',beneficiary,hex(10**18))
        timestamp=int(eth('eth_getBlockByNumber','latest',False)['timestamp'],16)
        maturity=timestamp+3800
        salt=digest('BTX/SWAPNET/EVM-SALT/2',{'swap_id':SID,'asset':asset})
        hashlock='12'*32
        terms=LegTerms(asset,str(AMOUNT),hashlock,relay,beneficiary,relay,beneficiary,'timestamp',maturity,
                       fixture.commitment(hashlock,relay,beneficiary,maturity),str(CLAIM_CAP),str(CLAIM_CAP*2))
        lock_data=calldata('lockNative(bytes32,bytes32,address,uint64)',bytes.fromhex(salt),
                           bytes.fromhex(hashlock),address_bytes(relay),maturity)
        funding=fixture._prepare(SID,'fund',key['handle'],contract,AMOUNT,lock_data,str(10**16),fixed_nonce=0)
        funded=eth.receipt(eth('eth_sendRawTransaction',funding.raw))
        assert funded['status']=='0x1'
        ref=fixture.reference(SID,terms,funding.txid)
        eth('evm_setNextBlockTimestamp',maturity)
        refund=calldata('refund(bytes32)',bytes.fromhex(ref['lock_id']))
        receipt=eth.finalize(eth('eth_sendTransaction',{'from':relay,'to':contract,'data':'0x'+refund.hex(),'gas':'0x50000'}))
        assert receipt['status']=='0x1'
        btx=LegTerms(f'btx:{BTX_GENESIS}:0:native','1000000',hashlock,'claim','refund',
                     'claim','refund','height',100,'fixture','10','10')
        agreement=Agreement(BTX_GENESIS,'22'*32,'owner:cookie','peer-fixture','33'*32,terms,btx)
        journal.save(SID,{'principal':'owner:cookie','peer':'peer-fixture','stage':'refund_broadcast',
                          'role':'initiator','agreement_id':agreement.id,'agreement':asdict(agreement),
                          'refs':{'a':ref},'keys':{'refund':key},'funding_prepared':True,
                          'funding_broadcast':True,'secret_exposed':False,'recovery_ready':True,
                          'grant_id':'44'*32})
        return terms,contract,beneficiary
    finally:
        store.close()


def run(node, eth, proxy, artifact, fault, stdout, expect):
    node.start(False)
    node.call('createwallet',WALLET)
    node.call('setmocktime',int(time.time())-60)
    result=subprocess.run([node.client,'-regtest',f'-datadir={node.data}','-conf=btx.conf',f'-rpcport={node.port}',
                           f'-rpcwallet={WALLET}','getnewaddress','','p2mr'],
                          capture_output=True,text=True,timeout=15,check=True)
    assert len(node.call('generatetoaddress',1,result.stdout.strip()))==1
    node.stop()
    node.start(True)  # Let the real host initialize its own wrapping key and database.
    assert node.call('getswapnetworkinfo')['in_process'] is True
    node.stop()
    terms,contract,beneficiary=seed_refunded_swap(node,eth,proxy,artifact)
    data={'to':contract,'data':'0x'+calldata('credits(address,address)',address_bytes(beneficiary),
                                           address_bytes(ZERO)).hex()}
    def credit():
        return int(eth('eth_call',data,'finalized'),16)
    assert credit()==AMOUNT
    before=int(eth('eth_getBalance',beneficiary,'latest'),16)
    node.start(True)
    def withdrawals():
        return [row for row in node.call('listswapoperations',{'swap_id':SID})['operations']
                if row['kind']=='withdraw']
    try:
        original,=wait_until(withdrawals,12 if expect=='preflight' else 30)
    except TimeoutError as error:
        view=node.call('getswap',{'swap_id':SID})
        info=node.call('getswapwalletinfo')
        last=view.get('last_error') or {}
        clocks=[node.call('getblockheader',node.call('getbestblockhash'))['time'],
                int(eth('eth_getBlockByNumber','latest',False)['timestamp'],16)]
        raise RuntimeError(f"Withdrawal did not start. stage={view.get('stage')} action={view.get('last_action')} code={last.get('code')} detail={last.get('message')} startup={info.get('startup_errors')} clocks={clocks}") from error
    failure=eth.finalize(original['txid'])
    assert failure['status']=='0x0' and int(failure['gasUsed'],16)==25_200 and len(fault)==1
    failed_fee=int(failure['gasUsed'],16)*int(failure['effectiveGasPrice'],16)
    assert credit()==AMOUNT
    call={'swap_id':SID,'failed_withdrawal_txid':original['txid']}
    if expect=='preflight':
        wallet=node.call('getwalletinfo',restricted=True)
        assert wallet['walletname']==WALLET
        print(json.dumps({'scope':'historical daemon fixture preflight','restricted_wallet_route':wallet['walletname'],
                          'failed_withdrawal_finalized':True,'original_credit_wei':credit(),
                          'failed_gas_wei':failed_fee,'withdrawal_count':1},indent=2),file=stdout)
        return

    owner=node.call('getswapauthinfo')
    restricted=node.call('getswapauthinfo',restricted=True)
    assert owner['owner'] and not restricted['owner'] and restricted['wallet']==WALLET
    try:
        node.call('resumeswap',call,restricted=True)
    except CliError as error:
        denied='OWNER_REQUIRED'
        assert denied in str(error),str(error)
    else:
        raise AssertionError('Restricted caller could start a retry')
    assert withdrawals()==[original] and credit()==AMOUNT
    eth('evm_setAutomine',False)
    response=node.call('resumeswap',call)
    retry_id=response['withdrawal_retry_txid']
    prepared=withdrawals()
    assert len(prepared)==2 and prepared[0]==original and prepared[1]['txid']==retry_id
    assert failed_fee+int(prepared[1]['metadata']['fee_atoms'])<=int(terms.max_refund_fee_atoms)//2
    assert eth('eth_getTransactionByHash',retry_id)['hash']==retry_id
    assert eth('eth_getTransactionReceipt',retry_id) is None
    node.stop()
    node.start(True)
    assert node.call('resumeswap',call)['withdrawal_retry_txid']==retry_id
    assert withdrawals()==prepared and eth('eth_getTransactionReceipt',retry_id) is None
    eth('evm_setAutomine',True)
    eth('evm_mine')
    paid=eth.finalize(retry_id)
    assert paid['status']=='0x1' and len(paid['logs'])==1
    retry_fee=int(paid['gasUsed'],16)*int(paid['effectiveGasPrice'],16)
    wait_until(lambda:node.call('getswap',{'swap_id':SID})['stage']=='refunded')
    node.stop()
    node.start(True)
    assert node.call('resumeswap',call)['withdrawal_retry_txid']==retry_id
    assert withdrawals()==prepared and credit()==0
    assert int(eth('eth_getBalance',beneficiary,'latest'),16)==before+AMOUNT-failed_fee-retry_fee
    print(json.dumps({'scope':'compiled BTX daemon and CLI','target':HEAD,'denial':denied,
                      'withdrawal_ids':[original['txid'],retry_id],
                      'first_attempt_finalized_revert':True,'restart_while_retry_pending':True,
                      'paid_original_wei':AMOUNT,'remaining_credit_wei':credit(),
                      'failed_gas_wei':failed_fee,'retry_gas_wei':retry_fee,
                      'withdrawal_cap_wei':int(terms.max_refund_fee_atoms)//2,
                      'duplicate_request_same_id':True},indent=2),file=stdout)


def main(daemon, cli, anvil, contract, expect):
    assert expect in ('preflight','candidate')
    with TemporaryDirectory(prefix='btx939-') as temp:
        root=Path(temp)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port=sock.getsockname()[1]
        eth=LocalRPC(f'http://127.0.0.1:{port}')
        anvil_process=subprocess.Popen([anvil,'--host','127.0.0.1','--port',str(port),'--chain-id','31337',
                                        '--timestamp',str(int(time.time())-3900),'--accounts','1'],
                                       cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        node=Node(root,daemon,cli)
        proxy=None
        fault=[]
        try:
            def chain_ready():
                assert anvil_process.poll() is None
                try:
                    return eth('eth_chainId')=='0x7a69'
                except OSError:
                    return False
            wait_until(chain_ready,10)
            proxy=proxy_for(eth,fault)
            Thread(target=proxy.serve_forever,daemon=True).start()
            address=f'http://127.0.0.1:{proxy.server_address[1]}'
            run(node,eth,address,json.loads(Path(contract).read_text()),fault,sys.stdout,expect)
        finally:
            try:
                node.stop()
            finally:
                if proxy:
                    proxy.shutdown()
                    proxy.server_close()
                anvil_process.terminate()
                try:
                    anvil_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    anvil_process.kill()
                    anvil_process.wait(timeout=5)


if __name__=='__main__':
    main(*sys.argv[1:])
