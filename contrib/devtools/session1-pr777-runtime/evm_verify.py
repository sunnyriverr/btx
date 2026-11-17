"""Read-only native-ETH receipt verification for the PR777 controller.

rpc is the production-style callable rpc(method, *params). terms is LegTerms or
its public dictionary; operations is Journal.operations(sid), public or private,
from BOTH nodes (the funder and beneficiary own different operation journals).
The caller must pin the deployed contract runtime against its approved artifact;
this helper returns its hash, never guesses the deployment address/runtime.
No raw transaction, metadata, preimage, key handle or credential is returned.
"""
import hashlib

from swapnet.assets import Asset
from swapnet.canonical import atoms, digest, hex32
from swapnet.evm import address_bytes, abi_word, calldata, keccak256, lock_id
from swapnet.terms import LegTerms

ZERO = '0x' + '00' * 20


def _check(ok, message):
    # Fixed messages intentionally exclude raw RPC payloads and claim witnesses.
    if not ok:
        raise AssertionError(message)


def _data(value):
    return bytes.fromhex(value.removeprefix('0x'))


def _topic(signature):
    return '0x' + keccak256(signature.encode('ascii')).hex()


def verify_evm_leg(rpc, terms, reference, operations, kind='claim'):
    """Assert finalized funding, exact claim/refund and exact ETH withdrawal.

    ETH amounts and gas charges are integer wei (agreement atoms), not gwei.
    A finalized canonical Withdrawn event proves transfer success under the
    caller-pinned SwapNetHTLC code. Balance movement is additionally asserted
    when the withdrawal is the only transaction in its block. With concurrent
    block transactions, balances are evidence only, not an attribution claim.
    """
    _check(kind in ('claim', 'refund'), 'Invalid EVM settlement kind')
    t = LegTerms.parse(terms) if isinstance(terms, dict) else terms
    asset = Asset.parse(t.asset)
    _check(asset.family == 'evm' and asset.token == 'native', 'Expected native ETH terms')
    _check(t.claim_key == t.payout and t.refund_key == t.refund_payout,
           'EVM beneficiary terms changed')
    _check(set(reference) == {'txid', 'lock_id', 'salt'}, 'Unexpected EVM reference shape')
    for name in ('lock_id', 'salt'):
        hex32(reference[name])
    hex32(reference['txid'].removeprefix('0x'))
    _check(int(rpc('eth_chainId'), 16) == asset.chain_id, 'EVM chain ID mismatch')
    _check(rpc('eth_getBlockByNumber', '0x0', False)['hash'][2:] == asset.genesis,
           'EVM genesis mismatch')
    final = rpc('eth_getBlockByNumber', 'finalized', False)
    _check(bool(final and final.get('hash')), 'EVM finalized block unavailable')
    final_height = int(final['number'], 16)

    def confirmed(txid):
        receipt = rpc('eth_getTransactionReceipt', txid)
        _check(bool(receipt and receipt.get('blockNumber')), 'EVM receipt unavailable')
        _check(receipt.get('transactionHash') == txid, 'EVM receipt transaction mismatch')
        _check(int(receipt.get('status', '0x0'), 16) == 1, 'EVM transaction reverted')
        _check(int(receipt['blockNumber'], 16) <= final_height, 'EVM transaction not finalized')
        block = rpc('eth_getBlockByNumber', receipt['blockNumber'], False)
        _check(block['hash'] == receipt['blockHash'], 'EVM receipt is not canonical')
        tx = rpc('eth_getTransactionByHash', txid)
        _check(bool(tx and tx.get('hash') == txid and tx.get('blockHash') == block['hash']),
               'EVM transaction inclusion mismatch')
        return receipt, tx, block

    funding, fund_tx, fund_block = confirmed(reference['txid'])
    contract = fund_tx['to'].lower()
    address_bytes(contract)
    _check(lock_id(asset.chain_id, contract, t.refund_key, reference['salt']) == reference['lock_id'],
           'EVM sender-scoped lock ID mismatch')
    amount = atoms(t.amount_atoms)
    lock = bytes.fromhex(reference['lock_id'])
    _check(fund_tx['from'].lower() == t.refund_key and int(fund_tx['value'], 16) == amount,
           'EVM funding sender/value mismatch')
    _check(_data(fund_tx['input']) == calldata('lockNative(bytes32,bytes32,address,uint64)',
           bytes.fromhex(reference['salt']), bytes.fromhex(t.hashlock),
           address_bytes(t.claim_key), t.lock_value), 'EVM funding calldata mismatch')
    code = _data(rpc('eth_getCode', contract, final['number']))
    _check(bool(code), 'EVM contract runtime missing')
    runtime_hash = keccak256(code).hex()
    commitment = digest('BTX/SWAPNET/EVM-CONTRACT/2', {
        'asset': asset.id, 'contract': contract, 'runtime_hash': runtime_hash,
        'hashlock': t.hashlock, 'claim_to': t.claim_key, 'refund_to': t.refund_key,
        'refund_at': t.lock_value})
    _check(commitment == t.lock_commitment, 'EVM contract commitment mismatch')
    _check(keccak256(_data(rpc('eth_getCode', contract, funding['blockNumber']))).hex()
           == runtime_hash, 'EVM funding runtime differs from finalized runtime')

    def event(receipt, signature, indexed, data):
        wanted = [_topic(signature)] + ['0x' + x.hex() for x in indexed]
        logs = [log for log in receipt.get('logs', [])
                if log.get('address', '').lower() == contract and log.get('topics') == wanted
                and not log.get('removed', False) and _data(log['data']) == data]
        _check(len(logs) == 1, 'EVM expected exact event missing or duplicated')

    event(funding, 'Locked(bytes32,bytes32,address,address,address,uint256,uint64)',
          [lock, abi_word(address_bytes(t.refund_key)), abi_word(address_bytes(t.claim_key))],
          bytes.fromhex(t.hashlock) + abi_word(address_bytes(ZERO)) + abi_word(amount) + abi_word(t.lock_value))
    state_raw = _data(rpc('eth_call', {'to': contract, 'data': '0x' + calldata('getSwap(bytes32)', lock).hex()}, final['number']))
    expected = (bytes.fromhex(t.hashlock) + abi_word(address_bytes(ZERO)) +
                abi_word(address_bytes(t.refund_key)) + abi_word(address_bytes(t.claim_key)) +
                abi_word(amount) + abi_word(t.lock_value) + abi_word(2 if kind == 'claim' else 3))
    _check(state_raw == expected, 'EVM finalized swap terms/state mismatch')
    ops = [o for o in operations if o['asset'] == t.asset]
    _check({o['txid'] for o in ops if o['kind'] == 'fund'} == {reference['txid']},
           'EVM duplicate or missing original funding operation')

    def select(operation_kind):
        # Deduplicate the same public operation if journals were combined twice.
        ids = list(dict.fromkeys(o['txid'] for o in ops if o['kind'] == operation_kind))
        _check(len(ids) == 1, 'Expected exactly one EVM settlement operation')
        return ids[0]

    settle_id, withdraw_id = select(kind), select('withdraw')
    settlement, settle_tx, settle_block = confirmed(settle_id)
    withdrawal, withdraw_tx, withdraw_block = confirmed(withdraw_id)
    for tx in (settle_tx, withdraw_tx):
        _check(tx['to'].lower() == contract and int(tx['value'], 16) == 0,
               'EVM settlement destination/value mismatch')
    if kind == 'claim':
        raw = _data(settle_tx['input'])
        _check(len(raw) == 68 and raw[:36] == calldata('claim(bytes32,bytes32)', lock),
               'EVM claim calldata mismatch')
        witness = raw[36:]
        _check(hashlib.sha256(witness).hexdigest() == t.hashlock, 'EVM claim hashlock mismatch')
        _check(int(settle_block['timestamp'], 16) < t.lock_value, 'EVM claim after deadline')
        event(settlement, 'Claimed(bytes32,bytes32)', [lock], witness)
    else:
        _check(_data(settle_tx['input']) == calldata('refund(bytes32)', lock), 'EVM refund calldata mismatch')
        _check(int(settle_block['timestamp'], 16) >= t.lock_value, 'EVM refund before deadline')
        event(settlement, 'Refunded(bytes32)', [lock], b'')
    beneficiary = t.payout if kind == 'claim' else t.refund_payout
    _check(withdraw_tx['from'].lower() == beneficiary, 'EVM withdrawal owner mismatch')
    _check(_data(withdraw_tx['input']) == calldata('withdrawAmount(address,address,uint256)',
           address_bytes(ZERO), address_bytes(beneficiary), amount), 'EVM withdrawal calldata mismatch')
    event(withdrawal, 'Withdrawn(address,address,address,uint256)',
          [abi_word(address_bytes(beneficiary)), abi_word(address_bytes(ZERO))],
          abi_word(address_bytes(beneficiary)) + abi_word(amount))
    order = lambda r: (int(r['blockNumber'], 16), int(r['transactionIndex'], 16))
    _check(order(funding) < order(settlement) < order(withdrawal), 'EVM settlement ordering mismatch')
    fees = [int(r['gasUsed'], 16) * int(r['effectiveGasPrice'], 16)
            for r in (funding, settlement, withdrawal)]
    cap = atoms(t.max_claim_fee_atoms if kind == 'claim' else t.max_refund_fee_atoms)
    _check(fees[1] + fees[2] <= cap, 'EVM settlement gas exceeds agreement cap')
    height = int(withdrawal['blockNumber'], 16)
    before = int(rpc('eth_getBalance', beneficiary, hex(height - 1)), 16)
    after = int(rpc('eth_getBalance', beneficiary, withdrawal['blockNumber']), 16)
    isolated = withdraw_block.get('transactions') == [withdraw_id]
    if isolated:
        _check(after - before == amount - fees[2], 'EVM beneficiary balance delta mismatch')
    credit = int(rpc('eth_call', {'to': contract, 'data': '0x' + calldata('credits(address,address)',
                 address_bytes(beneficiary), address_bytes(ZERO)).hex()}, final['number']), 16)
    _check(rpc('eth_getBlockByNumber', final['number'], False)['hash'] == final['hash'],
           'EVM finalized snapshot changed')
    return {'kind': kind, 'funding_txid': reference['txid'], 'settlement_txid': settle_id,
            'withdrawal_txid': withdraw_id, 'finalized_block_hash': final['hash'],
            'runtime_hash': runtime_hash, 'amount_wei': str(amount),
            'funding_fee_wei': str(fees[0]), 'settlement_fee_wei': str(fees[1]),
            'withdrawal_fee_wei': str(fees[2]), 'beneficiary_balance_before_wei': str(before),
            'beneficiary_balance_after_wei': str(after), 'remaining_credit_wei': str(credit),
            'isolated_withdrawal_balance_verified': isolated}
