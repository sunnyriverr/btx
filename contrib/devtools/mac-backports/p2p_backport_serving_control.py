#!/usr/bin/env python3
"""Positive #698 controls on genesis: no wallets, mining or weaker assertions."""
from test_framework.messages import (CInv, MSG_FILTERED_BLOCK, MSG_WITNESS_FLAG, NODE_BLOOM, BlockTransactionsRequest, msg_filterload, msg_getdata, msg_getblocktxn)
from test_framework.p2p import P2PInterface, p2p_lock
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal

class BackportServingControl(BitcoinTestFramework):
    def set_test_params(self):
        self.setup_clean_chain = True
        self.num_nodes = 1
        self.extra_args = [['-peerbloomfilters=1']]

    def run_test(self):
        node = self.nodes[0]
        genesis = node.getblockhash(0)
        expected_txid = node.getblock(genesis)['tx'][0]
        peer = node.add_p2p_connection(P2PInterface())
        assert peer.nServices & NODE_BLOOM
        peer.send_and_ping(msg_filterload(data=b'\xff', nHashFuncs=1, nTweak=0, nFlags=0))
        for kind in [MSG_FILTERED_BLOCK, MSG_FILTERED_BLOCK | MSG_WITNESS_FLAG]:
            with p2p_lock:
                peer.last_message.pop('merkleblock', None)
            peer.send_message(msg_getdata([CInv(kind, int(genesis, 16))]))
            peer.wait_for_merkleblock(genesis, timeout=15)
            peer.sync_with_ping()
            assert_equal(node.getconnectioncount(), 1)
        request = msg_getblocktxn()
        request.block_txn_request = BlockTransactionsRequest(blockhash=int(genesis, 16), indexes=[0])
        peer.send_message(request)
        peer.wait_until(lambda: 'blocktxn' in peer.last_message, timeout=15)
        with p2p_lock:
            response = peer.last_message['blocktxn'].block_transactions
            assert_equal(response.blockhash, int(genesis, 16))
            assert_equal(len(response.transactions), 1)
            assert_equal(response.transactions[0].rehash(), expected_txid)
        peer.sync_with_ping()
        assert_equal(node.getconnectioncount(), 1)
        node.getblockcount()

if __name__ == '__main__':
    BackportServingControl(__file__).main()
