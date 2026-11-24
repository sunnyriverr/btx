"""Bounded local withdrawal diagnostic with real receipts and one estimator fault."""
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from urllib.request import Request, urlopen

from test_execution_v2 import Pair
from swapnet.errors import SwapError
from swapnet.evm import address_bytes, calldata, keccak256, lock_id
from swapnet.evm_driver import EVMDriver, ZERO
from swapnet.terms import LegTerms


AMOUNT = 10**17
CLAIM_CAP = 10**15
CREATION_PIN = '401e81e4ab795f39e48b76bda608771e10078e23cfc1d807983b05ee3da97cde'
RUNTIME_PIN = 'a06e30bad714ff02db5a2401a898bd7194d1c475b61bdab312ae194b1509e45d'
WITHDRAW_SELECTOR = keccak256(b'withdrawAmount(address,address,uint256)')[:4].hex()


class LocalRPC:
    def __init__(self, url):
        self.url = url
        self.estimates = []
        self.submissions = []

    def __call__(self, method, *params):
        req = Request(self.url, json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method,
                                           'params': params}).encode(), {'Content-Type': 'application/json'})
        with urlopen(req, timeout=4) as response:
            result = json.load(response)
        if result.get('error'):
            raise RuntimeError(f"{method}: {result['error']['message']}")
        return result['result']

    def one_underestimate(self, method, *params):
        value = self(method, *params)
        if method == 'eth_estimateGas' and params[0].get('data', '').startswith('0x' + WITHDRAW_SELECTOR):
            if not self.estimates:
                actual = int(value, 16)
                assert actual > 25_200
                self.estimates.append(actual)
                return hex(21_000)
        if method == 'eth_sendRawTransaction':
            self.submissions.append(value)
        return value

    def receipt(self, txid):
        for _ in range(80):
            receipt = self('eth_getTransactionReceipt', txid)
            if receipt:
                assert receipt['transactionHash'] == txid
                return receipt
            time.sleep(0.025)
        raise AssertionError('Transaction receipt unavailable')

    def finalize(self, txid):
        receipt = self.receipt(txid)
        for _ in range(80):
            finalized = self('eth_getBlockByNumber', 'finalized', False)
            if finalized and int(finalized['number'], 16) >= int(receipt['blockNumber'], 16):
                assert self('eth_getBlockByNumber', receipt['blockNumber'], False)['hash'] == receipt['blockHash']
                return receipt
            self('evm_mine')
        raise AssertionError('Receipt never reached the finalized tip')


def run(rpc, artifact, folder):
    pair = Pair(folder)
    try:
        creation = bytes.fromhex(artifact['bytecode']['object'].removeprefix('0x'))
        assert keccak256(creation).hex() == CREATION_PIN
        funder = rpc('eth_accounts')[0].lower()

        def send(data, to=None, value=0):
            request = {'from': funder, 'data': '0x' + data.hex(),
                       'gas': hex(6_000_000 if to is None else 300_000), 'value': hex(value)}
            if to is not None:
                request['to'] = to
            receipt = rpc.receipt(rpc('eth_sendTransaction', request))
            assert receipt['status'] == '0x1'
            return receipt

        contract = send(creation)['contractAddress'].lower()
        assert keccak256(bytes.fromhex(rpc('eth_getCode', contract, 'latest')[2:])).hex() == RUNTIME_PIN
        genesis = rpc('eth_getBlockByNumber', '0x0', False)['hash'][2:]
        chain_id = int(rpc('eth_chainId'), 16)
        assert chain_id == 31337
        asset = f'evm:{genesis}:{chain_id}:native'

        def open_driver():
            _, journal, _, coordinator = pair.nodes['alice']
            return EVMDriver(asset, rpc.one_underestimate, journal, coordinator.vault, contract, RUNTIME_PIN)

        driver = open_driver()
        key = driver.new_key('claim')
        beneficiary = key['public']
        rpc('anvil_setBalance', beneficiary, hex(10**18))
        preimage = b'\x12' * 32
        hashlock = hashlib.sha256(preimage).digest()
        salt = b'\x34' * 32
        deadline = int(rpc('eth_getBlockByNumber', 'latest', False)['timestamp'], 16) + 7200
        lock = bytes.fromhex(lock_id(chain_id, contract, funder, salt.hex()))
        send(calldata('lockNative(bytes32,bytes32,address,uint64)', salt, hashlock,
                      address_bytes(beneficiary), deadline), contract, AMOUNT)
        claim = send(calldata('claim(bytes32,bytes32)', lock, preimage), contract)
        rpc.finalize(claim['transactionHash'])
        terms = LegTerms(asset, str(AMOUNT), hashlock.hex(), beneficiary, funder, beneficiary,
                         funder, 'timestamp', deadline,
                         driver.commitment(hashlock.hex(), beneficiary, funder, deadline),
                         str(CLAIM_CAP), str(CLAIM_CAP))
        driver.verify_terms(terms)

        def finalized_credit():
            final = rpc('eth_getBlockByNumber', 'finalized', False)
            read = calldata('credits(address,address)', address_bytes(beneficiary), address_bytes(ZERO))
            return int(rpc('eth_call', {'to': contract, 'data': '0x' + read.hex()}, final['number']), 16)

        credit_before = finalized_credit()
        balance_before = int(rpc('eth_getBalance', beneficiary, 'latest'), 16)
        assert credit_before == AMOUNT
        sid = '12' * 32
        assert driver.ensure_withdrawal(sid, terms, key) is False
        original, = driver.journal.operations(sid, private=True)
        txid = original['txid']
        receipt = rpc.finalize(txid)
        tx = rpc('eth_getTransactionByHash', txid)
        expected_input = calldata('withdrawAmount(address,address,uint256)',
                                  address_bytes(ZERO), address_bytes(beneficiary), AMOUNT)
        assert tx['input'] == '0x' + expected_input.hex() and tx['from'].lower() == beneficiary
        assert tx['to'].lower() == contract and int(tx['value'], 16) == 0
        gas_used = int(receipt['gasUsed'], 16)
        gas_price = int(receipt['effectiveGasPrice'], 16)
        assert receipt['status'] == '0x0' and not receipt['logs']
        assert gas_used == int(tx['gas'], 16) == 25_200
        credit_after = finalized_credit()
        balance_after = int(rpc('eth_getBalance', beneficiary, 'latest'), 16)
        failed_fee = gas_used * gas_price
        assert credit_after == credit_before and balance_before - balance_after == failed_fee
        assert original['state'] == 'broadcast'

        pair.close('alice')
        pair.open('alice')
        driver = open_driver()
        try:
            driver.ensure_withdrawal(sid, terms, key)
        except SwapError as error:
            assert error.code == 'WITHDRAW_REVERTED'
            retry = error.code
        else:
            raise AssertionError('Expected the pinned driver to stop at the failed receipt')
        assert driver.journal.operations(sid, private=True) == [original]
        assert rpc.submissions == [txid] and finalized_credit() == credit_before

        real_estimate = int(rpc('eth_estimateGas', {'from': beneficiary, 'to': contract,
                                                 'data': '0x' + expected_input.hex(), 'value': '0x0'}), 16)
        assert real_estimate > gas_used
        _, max_price = driver._fees(CLAIM_CAP // 2)
        retry_ceiling = max(21_000, (real_estimate * 12 + 9) // 10) * max_price
        withdrawal_cap = CLAIM_CAP // 2
        assert failed_fee <= int(original['metadata']['fee_atoms']) <= withdrawal_cap
        return {
            'chain_id': chain_id, 'runtime_keccak256': RUNTIME_PIN,
            'claim_txid': claim['transactionHash'], 'withdrawal_txid': txid,
            'receipt_status': receipt['status'], 'receipt_block': int(receipt['blockNumber'], 16),
            'canonical_and_finalized': True, 'credit_before_wei': credit_before,
            'credit_after_wei': credit_after, 'wallet_balance_delta_wei': balance_before - balance_after,
            'gas_estimate_before_fault': rpc.estimates[0], 'injected_gas_estimate': 21_000,
            'gas_used': gas_used, 'effective_gas_price_wei': gas_price, 'failed_fee_wei': failed_fee,
            'original_signed_fee_ceiling_wei': int(original['metadata']['fee_atoms']),
            'approved_claim_cap_wei': CLAIM_CAP, 'withdrawal_subcap_wei': withdrawal_cap,
            'withdrawal_subcap_remaining_after_failed_fee_wei': withdrawal_cap - failed_fee,
            'current_unmodified_gas_estimate': real_estimate,
            'current_estimated_retry_ceiling_wei': retry_ceiling,
            'current_estimated_retry_fits_remaining_subcap': retry_ceiling <= withdrawal_cap - failed_fee,
            'claim_fee_paid_by_fixture_relayer': True, 'retry_after_reopen': retry,
            'submitted_withdrawals': len(rpc.submissions), 'original_operation_unchanged': True,
        }
    finally:
        for name in pair.nodes:
            pair.close(name)


def main(anvil, artifact_path):
    with TemporaryDirectory(prefix='swapnet-anvil-withdrawal-') as temp:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        rpc = LocalRPC(f'http://127.0.0.1:{port}')
        proc = subprocess.Popen([anvil, '--host', '127.0.0.1', '--port', str(port),
                                 '--chain-id', '31337', '--accounts', '1'],
                                cwd=temp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                assert proc.poll() is None
                try:
                    if rpc('eth_chainId') == '0x7a69':
                        break
                except OSError:
                    time.sleep(0.05)
            else:
                raise RuntimeError('Disposable Anvil failed to start')
            result = run(rpc, json.loads(Path(artifact_path).read_text()), Path(temp))
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=4)
        result['owned_anvil_reaped'] = proc.poll() is not None
    result['temporary_directory_removed'] = not Path(temp).exists()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main(*sys.argv[1:])
