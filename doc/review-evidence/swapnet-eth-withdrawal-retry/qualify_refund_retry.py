"""Paired refund-credit check using the retained Anvil launcher and contract."""
from dataclasses import asdict
import json
import sys
from unittest.mock import patch

import anvil_check
from anvil_check import AMOUNT, CLAIM_CAP, CREATION_PIN, RUNTIME_PIN
from test_execution_v2 import A, Pair
from swapnet.canonical import digest
from swapnet.embedded import Host
from swapnet.errors import SwapError
from swapnet.evm import address_bytes, calldata, keccak256
from swapnet.evm_driver import EVMDriver, ZERO
from swapnet.market_application import Application
from swapnet.terms import Agreement, LegTerms

VARIANT = sys.argv[1]
assert VARIANT in {'stock', 'candidate'}
REFUND_CAP = CLAIM_CAP * 2


def run(rpc, artifact, folder):
    pair = Pair(folder)
    sid = '45' * 32
    try:
        creation = bytes.fromhex(artifact['bytecode']['object'].removeprefix('0x'))
        assert keccak256(creation).hex() == CREATION_PIN
        relay = rpc('eth_accounts')[0].lower()

        def relay_call(data, to=None):
            request = {'from': relay, 'data': '0x' + data.hex(),
                       'gas': hex(6_000_000 if to is None else 300_000)}
            if to is not None:
                request['to'] = to
            receipt = rpc.receipt(rpc('eth_sendTransaction', request))
            assert receipt['status'] == '0x1'
            return receipt

        contract = relay_call(creation)['contractAddress'].lower()
        assert keccak256(bytes.fromhex(rpc('eth_getCode', contract, 'latest')[2:])).hex() == RUNTIME_PIN
        genesis = rpc('eth_getBlockByNumber', '0x0', False)['hash'][2:]
        asset = f'evm:{genesis}:31337:native'

        def open_fixture():
            _, journal, authority, coordinator = pair.nodes['alice']
            driver = EVMDriver(asset, rpc.one_underestimate, journal, coordinator.vault, contract, RUNTIME_PIN)
            coordinator.drivers[asset] = driver
            app = object.__new__(Application)
            app.authority = authority
            app.coordinator = coordinator
            host = object.__new__(Host)
            host.app = app
            host._wallet = 'refund-fixture'
            return host, driver

        host, driver = open_fixture()
        key = driver.new_key('refund')
        beneficiary = key['public']
        rpc('anvil_setBalance', beneficiary, hex(10**18))
        hashlock = '12' * 32

        def send_fixture_tx(kind, payload, value=0):
            # Fixture funding and the competing credit are real transactions
            # from the disposable vault signer, outside the withdrawal journal.
            nonce = int(rpc('eth_getTransactionCount', beneficiary, 'pending'), 16)
            with patch.object(driver, 'rpc', rpc):
                prepared = driver._prepare(sid, kind, key['handle'], contract, value, payload,
                                           str(10**16), fixed_nonce=nonce)
            receipt = rpc.receipt(rpc('eth_sendRawTransaction', prepared.raw))
            assert receipt['status'] == '0x1'
            return receipt

        def credit_refund(swap_id):
            salt = digest('BTX/SWAPNET/EVM-SALT/2', {'swap_id': swap_id, 'asset': asset})
            deadline = int(rpc('eth_getBlockByNumber', 'latest', False)['timestamp'], 16) + 7200
            terms = LegTerms(asset, str(AMOUNT), hashlock, relay, beneficiary, relay,
                             beneficiary, 'timestamp', deadline,
                             driver.commitment(hashlock, relay, beneficiary, deadline),
                             str(CLAIM_CAP), str(REFUND_CAP))
            funding = send_fixture_tx('fund', calldata('lockNative(bytes32,bytes32,address,uint64)',
                                      bytes.fromhex(salt), bytes.fromhex(hashlock),
                                      address_bytes(relay), deadline), AMOUNT)
            ref = driver.reference(swap_id, terms, funding['transactionHash'])
            rpc('evm_setNextBlockTimestamp', deadline)
            refund = relay_call(calldata('refund(bytes32)', bytes.fromhex(ref['lock_id'])), contract)
            rpc.finalize(refund['transactionHash'])
            return terms, ref

        credit_data = calldata('credits(address,address)', address_bytes(beneficiary), address_bytes(ZERO))
        withdraw_data = calldata('withdrawAmount(address,address,uint256)', address_bytes(ZERO),
                                 address_bytes(beneficiary), AMOUNT)

        def credit():
            data = {'to': contract, 'data': '0x' + credit_data.hex()}
            return int(rpc('eth_call', data, 'finalized'), 16)

        def balance():
            return int(rpc('eth_getBalance', beneficiary, 'latest'), 16)

        terms, ref = credit_refund(sid)
        assert credit() == AMOUNT
        starting_balance = balance()
        btx = LegTerms(A, '1000000', hashlock, 'claim', 'refund', 'claim', 'refund',
                       'height', 100, 'fixture', '10', '10')
        agreement = Agreement('11' * 32, '22' * 32, 'alice', 'bob', '33' * 32, terms, btx)
        state = {'principal': 'alice', 'peer': 'bob', 'stage': 'withdrawing', 'role': 'initiator',
                 'agreement_id': agreement.id, 'agreement': asdict(agreement), 'last_action': 'refunded',
                 'refs': {'a': ref}, 'keys': {'refund': key}, 'funding_prepared': True}
        driver.journal.save(sid, state)
        assert driver.ensure_withdrawal(sid, terms, key, refund=True) is False
        original, = driver.journal.operations(sid, private=True)
        txid = original['txid']
        receipt = rpc.finalize(txid)
        assert receipt['status'] == '0x0' and not receipt['logs']
        failed_fee = int(receipt['gasUsed'], 16) * int(receipt['effectiveGasPrice'], 16)
        assert credit() == AMOUNT and starting_balance - balance() == failed_fee

        def reopen():
            pair.close('alice')
            pair.open('alice')
            return open_fixture()

        host, driver = reopen()
        request = json.dumps({'swap_id': sid, 'failed_withdrawal_txid': txid})

        def retry(owner=True, wallet='refund-fixture'):
            return json.loads(host.rpc('alice', owner, wallet, 'resumeswap', request))

        def refuses(code, **kwargs):
            result = retry(**kwargs)
            assert result.get('error', {}).get('code') == code, result
            return code

        assert driver.journal.operations(sid, private=True) == [original]
        cap = REFUND_CAP // 2
        common = {'variant': VARIANT, 'refund_credit_initial_wei': AMOUNT,
                  'first_mined_receipt_status': receipt['status'], 'failed_gas_wei': failed_fee,
                  'approved_refund_cap_wei': REFUND_CAP, 'original_withdrawal_subcap_wei': cap}
        if VARIANT == 'stock':
            assert refuses('PARAMS') and credit() == AMOUNT and rpc.submissions == [txid]
            return {**common, 'retry': 'PARAMS', 'credit_remaining_wei': credit()}

        authorization_controls = {'nonowner': refuses('OWNER_REQUIRED', owner=False),
                                  'wrong_wallet': refuses('WALLET_SCOPE', wallet='other-wallet')}
        rev, _ = driver.journal.load(sid)
        rev = driver.journal.save(sid, {**state, 'recovery_facts': {'mode': 'observation_only'}}, rev)
        authorization_controls['observation_only'] = refuses('RECOVERY_READ_ONLY')
        driver.journal.save(sid, state, rev)

        snapshot = rpc('evm_snapshot')
        competing_spend = send_fixture_tx('withdraw', withdraw_data)
        _, _ = credit_refund('46' * 32)
        assert len(competing_spend['logs']) == 1 and credit() == AMOUNT
        history_result = refuses('WITHDRAW_CREDIT_UNKNOWN')
        assert driver.journal.operations(sid, private=True) == [original] and rpc.submissions == [txid]
        assert rpc('evm_revert', snapshot)

        with patch.object(driver.adapter, 'broadcast', side_effect=SwapError('RPC_UNAVAILABLE', 'fixture')):
            refuses('RPC_UNAVAILABLE')
        originals, retry_op = driver.journal.operations(sid, private=True)
        assert originals == original and retry_op['state'] == 'prepared'
        assert retry_op['metadata']['nonce'] == original['metadata']['nonce'] + 1
        assert failed_fee + int(retry_op['metadata']['fee_atoms']) <= cap
        assert rpc.submissions == [txid]
        host, driver = reopen()
        retry_id = retry_op['txid']
        assert retry()['result']['withdrawal_retry_txid'] == retry_id
        assert driver.ensure_withdrawal(sid, terms, key, refund=True) is False
        success = rpc.finalize(retry_id)
        assert success['status'] == '0x1' and len(success['logs']) == 1
        assert driver.ensure_withdrawal(sid, terms, key, refund=True) is True
        assert credit() == 0 and rpc.submissions == [txid, retry_id]
        host, driver = reopen()
        assert retry()['result']['withdrawal_retry_txid'] == retry_id
        assert driver.ensure_withdrawal(sid, terms, key, refund=True) is True
        assert rpc.submissions == [txid, retry_id]
        retry_fee = int(success['gasUsed'], 16) * int(success['effectiveGasPrice'], 16)
        assert balance() == starting_balance + AMOUNT - failed_fee - retry_fee
        assert failed_fee + retry_fee <= cap
        return {**common, 'retry': 'finalized_once', 'credit_remaining_wei': credit(),
                'paid_to_original_beneficiary_wei': AMOUNT,
                'native_credit_history_guard': history_result,
                'authorization_controls': authorization_controls,
                'actual_retry_fee_wei': retry_fee, 'total_fee_wei': failed_fee + retry_fee,
                'withdrawals_submitted': len(rpc.submissions), 'restart_reused_saved_retry': True}
    finally:
        for name in pair.nodes:
            pair.close(name)


if __name__ == '__main__':
    anvil_check.run = run
    anvil_check.main(*sys.argv[2:])
