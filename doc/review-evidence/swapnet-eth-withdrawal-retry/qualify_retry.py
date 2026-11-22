"""Paired Anvil regression for an explicitly authorized withdrawal retry."""
from dataclasses import asdict
import hashlib
import sys

import anvil_check
from anvil_check import AMOUNT, CLAIM_CAP, CREATION_PIN, RUNTIME_PIN
from test_execution_v2 import A, Pair
from swapnet.application import Application
from swapnet.authorization import Principal
from swapnet.canonical import digest
from swapnet.errors import SwapError
from swapnet.evm import address_bytes, calldata, keccak256, lock_id
from swapnet.evm_driver import EVMDriver, ZERO
from swapnet.terms import Agreement, LegTerms

variant=sys.argv[1]
assert variant in {'stock','candidate'}

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
        sid = '12' * 32
        salt = bytes.fromhex(digest('BTX/SWAPNET/EVM-SALT/2',{'swap_id':sid,'asset':asset}))
        deadline = int(rpc('eth_getBlockByNumber', 'latest', False)['timestamp'], 16) + 7200
        lock = bytes.fromhex(lock_id(chain_id, contract, funder, salt.hex()))
        funding = send(calldata('lockNative(bytes32,bytes32,address,uint64)', salt, hashlock,
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
        ref=driver.reference(sid,terms,funding['transactionHash'])
        assert ref['lock_id']==lock.hex()
        _,journal,_,_=pair.nodes['alice']
        btx=LegTerms(A,'1000000',hashlock.hex(),'dummy-claim','dummy-funder','dummy-claim',
                     'dummy-funder','height',100,'dummy-commitment','10','10')
        agreement=Agreement('11'*32,'22'*32,'alice','bob','33'*32,btx,terms)
        journal.save(sid,{'principal':'alice','peer':'bob','stage':'withdrawing','role':'initiator',
                          'agreement_id':agreement.id,'agreement':asdict(agreement),
                          'last_action':'complete','refs':{'b':ref},'keys':{'claim':key}})

        def opened_app():
            _,_,auth,coordinator=pair.nodes['alice']
            coordinator.drivers[asset]=open_driver()
            app=object.__new__(Application)
            app.authority=auth
            app.coordinator=coordinator
            return app,coordinator.drivers[asset]

        app,_=opened_app()
        owner=Principal('alice',True)
        rpc('evm_setAutomine',False)
        assert driver.ensure_withdrawal(sid, terms, key) is False
        original, = driver.journal.operations(sid, private=True)
        txid = original['txid']
        try:
            app.rpc(owner,'resumeswap',{'swap_id':sid,'failed_withdrawal_txid':txid})
        except SwapError as error:
            assert error.code==('WITHDRAW_NOT_FINAL' if variant=='candidate' else 'PARAMS'),error.code
            pending_result=error.code
        else:
            raise AssertionError('Pending original withdrawal admitted a retry')
        assert driver.journal.operations(sid,private=True)==[original]
        assert rpc.submissions==[txid]
        rpc('evm_setAutomine',True)
        rpc('evm_mine')
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
        app,driver = opened_app()
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
        request={'swap_id':sid,'failed_withdrawal_txid':txid}

        def refuses(code,callback):
            try:
                callback()
            except SwapError as error:
                assert error.code==code,(error.code,error.message)
                return error.code
            raise AssertionError(f'Expected {code}')

        common={'variant':variant,'original_pending_guard':pending_result,
                'status_after_reopen_before_opt_in':retry,'original_credit_wei':credit_after,
                'failed_fee_wei':failed_fee,'original_withdrawal_cap_wei':withdrawal_cap}
        if variant=='stock':
            result=refuses('PARAMS',lambda:app.rpc(owner,'resumeswap',request))
            assert finalized_credit()==AMOUNT and len(rpc.submissions)==1
            return {**common,'explicit_opt_in':result,'credit_after_opt_in_wei':AMOUNT,'withdrawals_submitted':1}

        refuses('OWNER_REQUIRED',lambda:app.rpc(Principal('alice'),'resumeswap',request))
        refuses('WITHDRAW_SCOPE',lambda:app.rpc(owner,'resumeswap',
                                                {**request,'failed_withdrawal_txid':'0x'+'ab'*32}))
        def nonce_rows():
            return driver.journal.store.db.execute(
                'SELECT nonce,operation FROM sn_nonces WHERE asset=? ORDER BY nonce',(asset,)).fetchall()

        original_nonces=nonce_rows()

        from unittest.mock import patch

        def without_known_fee(method,*args):
            result=rpc.one_underestimate(method,*args)
            if method=='eth_getTransactionReceipt' and args[0]==txid:
                result.pop('effectiveGasPrice')
            return result

        def noncanonical_receipt(method,*args):
            result=rpc.one_underestimate(method,*args)
            if method=='eth_getTransactionReceipt' and args[0]==txid:
                result['blockHash']='0x'+'00'*32
            return result

        for scripted,code in ((without_known_fee,'WITHDRAW_FEE_UNKNOWN'),
                              (noncanonical_receipt,'WITHDRAW_NOT_FINAL')):
            with patch.object(driver,'rpc',scripted):
                refuses(code,lambda:app.rpc(owner,'resumeswap',request))
        with patch.object(driver,'_verify_retry_credit',side_effect=SwapError('WITHDRAW_CREDIT_UNKNOWN','ambiguous fixture')):
            refuses('WITHDRAW_CREDIT_UNKNOWN',lambda:app.rpc(owner,'resumeswap',request))

        # Fit under the full cap but exceed the remainder after paying for the revert.
        signed_gas=max(21_000,(real_estimate*12+9)//10)
        high_price=withdrawal_cap//signed_gas
        assert withdrawal_cap-failed_fee<high_price*signed_gas<=withdrawal_cap
        with patch.object(driver,'_fees',return_value=(1,high_price)):
            refuses('FEE_CAP',lambda:app.rpc(owner,'resumeswap',request))
        assert nonce_rows()==original_nonces and len(rpc.submissions)==1

        with patch.object(driver.journal,'prepare',side_effect=SwapError('IO','test journal failure')):
            refuses('IO',lambda:app.rpc(owner,'resumeswap',request))
        assert nonce_rows()==original_nonces and driver.journal.operations(sid,private=True)==[original]

        with patch.object(driver.adapter,'broadcast',side_effect=SwapError('RPC_UNAVAILABLE','test interruption')):
            refuses('RPC_UNAVAILABLE',lambda:app.rpc(owner,'resumeswap',request))
        first,retry_op=driver.journal.operations(sid,private=True)
        assert first==original and retry_op['state']=='prepared'
        assert retry_op['metadata']['nonce']==original['metadata']['nonce']+1
        assert retry_op['metadata']['data']==original['metadata']['data']
        assert len(rpc.submissions)==1
        retry_txid=retry_op['txid']

        pair.close('alice')
        pair.open('alice')
        app,driver=opened_app()
        assert driver.journal.operations(sid,private=True)==[original,retry_op]
        assert app.rpc(owner,'resumeswap',request)['withdrawal_retry_txid']==retry_txid
        with patch.object(driver,'rpc',noncanonical_receipt):
            refuses('WITHDRAW_NOT_FINAL',lambda:driver.ensure_withdrawal(sid,terms,key))
        assert rpc.submissions==[txid]
        send_retry=driver.adapter.broadcast

        def send_then_lose_response(raw):
            send_retry(raw)
            raise SwapError('RPC_UNAVAILABLE','fixture interrupted after send')

        with patch.object(driver.adapter,'broadcast',send_then_lose_response):
            refuses('RPC_UNAVAILABLE',lambda:driver.ensure_withdrawal(sid,terms,key))
        assert rpc.submissions==[txid,retry_txid]
        pair.close('alice')
        pair.open('alice')
        app,driver=opened_app()
        assert app.rpc(owner,'resumeswap',request)['withdrawal_retry_txid']==retry_txid
        payout=rpc.finalize(retry_txid)
        assert payout['status']=='0x1'
        assert len(payout['logs'])==1 and finalized_credit()==0
        assert driver.ensure_withdrawal(sid,terms,key) is True
        assert rpc.submissions==[txid,retry_txid]
        assert app.rpc(owner,'resumeswap',request)['withdrawal_retry_txid']==retry_txid
        assert rpc.submissions==[txid,retry_txid]
        actual_retry_fee=int(payout['gasUsed'],16)*int(payout['effectiveGasPrice'],16)
        assert failed_fee+int(retry_op['metadata']['fee_atoms'])<=withdrawal_cap
        assert failed_fee+actual_retry_fee<=withdrawal_cap
        assert int(rpc('eth_getBalance',beneficiary,'latest'),16)==balance_before+AMOUNT-failed_fee-actual_retry_fee
        return {**common,'explicit_opt_in':'finalized_success','refused_oversized_retry':'FEE_CAP',
                'credit_after_opt_in_wei':0,'actual_retry_fee_wei':actual_retry_fee,
                'retry_signed_fee_ceiling_wei':int(retry_op['metadata']['fee_atoms']),
                'total_actual_withdrawal_fees_wei':failed_fee+actual_retry_fee,
                'withdrawals_submitted':2,'restart_reused_prepared_transaction':True,
                'original_attempt_and_nonce_preserved':True,'exact_payout_balance_delta':True,
                'unknown_fee_and_noncanonical_receipt_refused':True,
                'rolled_back_nonce_on_failed_journal_write':True,
                'interrupted_after_send_reopened_without_resubmission':True}
    finally:
        for name in pair.nodes:
            pair.close(name)

if __name__=='__main__':
    anvil_check.run=run
    anvil_check.main(*sys.argv[2:])
