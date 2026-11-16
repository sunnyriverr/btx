#!/usr/bin/env python3
# Copyright (c) 2026 The BTX developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/license/mit-license.php.
"""P2MR payment with an ineligible self-spend chain and sufficient confirmed funds.

Adapted from Bitcoin Core PR36284; complements Jpp-matata's BTX PR774
unit regression. No non-P2MR address types or policy-limit relaxation.
"""
from decimal import Decimal
import json
from pathlib import Path

from test_framework.authproxy import JSONRPCException
from test_framework.blocktools import REGTEST_GENERIC_P2P_MATMUL_ARGS
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal


class P2MRAPSInputTest(BitcoinTestFramework):
    CHAIN_LIMIT = 100
    CHAIN_SIZE_LIMIT = 1024 * 1000
    FEE_RATE = Decimal("2")  # atoms/vB

    def add_options(self, parser):
        self.add_wallet_options(parser, legacy=False)

    def set_test_params(self):
        self.num_nodes = 1
        self.setup_clean_chain = True
        # Pin current BTX defaults explicitly so an upstream policy change
        # cannot silently make a shorter chain eligible in this fixture.
        self.extra_args = [list(REGTEST_GENERIC_P2P_MATMUL_ARGS) + [
            "-autoshieldcoinbase=0", "-fallbackfee=0.0002",
            "-walletrejectlongchains=1", "-spendzeroconfchange=1",
            "-limitancestorcount=100", "-limitdescendantcount=100",
            "-limitancestorsize=1024", "-limitdescendantsize=1024",
            "-swapnet=0", "-autoupdate=0", "-networkactive=0",
            "-dnsseed=0", "-listenonion=0", "-natpmp=0",
        ]]

    def setup_network(self):
        if self.config["components"].getboolean("ENABLE_MODELNET", fallback=False):
            self.extra_args[0].append("-nomodelnet")
        self.setup_nodes()

    def skip_test_if_missing_module(self):
        self.skip_if_no_wallet()

    def run_test(self):
        node = self.nodes[0]
        evidence = {"stage": "setup", "policy_count": self.CHAIN_LIMIT,
                    "policy_size_vbytes": self.CHAIN_SIZE_LIMIT, "fee_rate": self.FEE_RATE}
        receipt = Path(self.options.tmpdir) / "p2mr-aps-payment.json"
        try:
            node.createwallet("funder")
            node.createwallet("aps", avoid_reuse=True)
            funder = node.get_wallet_rpc("funder")
            aps = node.get_wallet_rpc("aps")
            def new_address(wallet):
                return wallet.getnewaddress(address_type="p2mr")
            mining_address = new_address(funder)
            self.generatetoaddress(node, 110, mining_address)
            assert_equal(aps.getwalletinfo()["avoid_reuse"], True)
            first_address = new_address(aps)
            first = funder.sendtoaddress(first_address, Decimal("0.3"), fee_rate=self.FEE_RATE)
            self.generatetoaddress(node, 1, mining_address)
            initial = aps.listunspent()
            assert_equal(len(initial), 1)
            assert_equal(initial[0]['txid'], first)
            assert_equal(initial[0]['address'], first_address)
            previous = (first, initial[0]['vout'])
            chain = []
            chain_sizes = []
            evidence["stage"] = "building_chain"
            for count in range(1, self.CHAIN_LIMIT + 1):
                destination = new_address(aps)
                txid = aps.sendall([destination], fee_rate=self.FEE_RATE)["txid"]
                decoded = node.decoderawtransaction(aps.gettransaction(txid)["hex"])
                assert_equal([(x["txid"], x["vout"]) for x in decoded["vin"]], [previous])
                assert_equal(len(decoded["vout"]), 1)
                assert_equal(decoded["vout"][0]["scriptPubKey"]["address"], destination)
                entry = node.getmempoolentry(txid)
                assert_equal(entry["ancestorcount"], count)
                assert entry["ancestorsize"] <= self.CHAIN_SIZE_LIMIT
                chain.append(txid)
                chain_sizes.append(decoded["vsize"])
                previous = (txid, 0)
                evidence["chain_count"] = count
                evidence["last_entry"] = entry
                evidence["chain_vsizes"] = chain_sizes
            evidence["stage"] = "independent_confirmed_deposit"
            confirmed_address = new_address(aps)
            confirmed_txid = funder.sendtoaddress(confirmed_address, Decimal("0.7"), fee_rate=self.FEE_RATE)
            assert_equal(node.getmempoolancestors(confirmed_txid), [])
            deposit = node.decoderawtransaction(funder.gettransaction(confirmed_txid)['hex'])
            matches = [x['n'] for x in deposit['vout']
                       if x['scriptPubKey'].get('address') == confirmed_address]
            assert_equal(len(matches), 1)
            confirmed = (confirmed_txid, matches[0])
            block_hash = self.generateblock(node, mining_address, [confirmed_txid])["hash"]
            assert_equal(node.getblock(block_hash)["tx"][1:], [confirmed_txid])
            assert_equal(set(node.getrawmempool()), set(chain))
            tip_entry = node.getmempoolentry(chain[-1])
            assert_equal(tip_entry["ancestorcount"], self.CHAIN_LIMIT)
            assert_equal(tip_entry["descendantcount"], 1)
            rows = {(x["txid"], x["vout"]): x for x in aps.listunspent(0)}
            assert_equal(set(rows), {previous, confirmed})
            assert_equal(rows[confirmed]["amount"], Decimal("0.7"))
            assert rows[confirmed]["confirmations"] >= 1
            assert_equal(rows[previous]["confirmations"], 0)
            assert rows[previous]["safe"] and rows[previous]["spendable"]
            # Duplicate subtraction must materially reduce apparent funds:
            # available (.7 + chain) - 2*chain < the .65 requested amount.
            assert rows[previous]["amount"] > Decimal("0.05")
            assert Decimal("0.7") - rows[previous]["amount"] < Decimal("0.65")
            evidence.update(stage="payment", chain_tip=previous, confirmed_input=confirmed,
                            rows=list(rows.values()), tip_entry=tip_entry)
            receipt.write_text(json.dumps(evidence, default=str, indent=2))
            # Expected success on both products. The unpatched failure must be
            # observed by the runner; do not encode it as an expected error.
            payment_address = new_address(funder)
            payment = aps.sendtoaddress(payment_address, Decimal("0.65"),
                                        avoid_reuse=True, fee_rate=self.FEE_RATE)
            node.getmempoolentry(payment)
            wallet_tx = aps.gettransaction(payment)
            decoded = node.decoderawtransaction(wallet_tx["hex"])
            assert_equal([(x["txid"], x["vout"]) for x in decoded["vin"]], [confirmed])
            outputs = decoded["vout"]
            assert_equal(len(outputs), 2)
            paid = [x for x in outputs if x["scriptPubKey"].get("address") == payment_address]
            assert_equal(len(paid), 1)
            assert_equal(paid[0]["value"], Decimal("0.65"))
            fee = Decimal("0.7") - sum(x["value"] for x in outputs)
            assert 0 < fee < Decimal("0.05")
            assert_equal(fee, -wallet_tx["fee"])
            change = next(x for x in outputs if x is not paid[0])
            assert aps.getaddressinfo(change["scriptPubKey"]["address"])["ismine"]
            assert set(chain) <= set(node.getrawmempool())
            assert node.gettxout(*previous) is not None
            evidence.update(stage="passed", payment=payment, fee=fee,
                            payment_inputs=decoded["vin"], payment_outputs=outputs)
        except JSONRPCException as error:
            evidence["rpc_error"] = error.error
            raise
        finally:
            receipt.write_text(json.dumps(evidence, default=str, indent=2))


if __name__ == '__main__':
    P2MRAPSInputTest(__file__).main()
