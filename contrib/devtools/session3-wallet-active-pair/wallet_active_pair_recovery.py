#!/usr/bin/env python3
# Copyright (c) 2026 The BTX developers
# Distributed under the MIT software license; see COPYING.
"""Local, unexecuted #917 active-P2MR-pair recovery acceptance fixture."""
import json
import os
from pathlib import Path
from decimal import Decimal
import shutil

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, assert_raises_rpc_error


class ActivePairRecoveryTest(BitcoinTestFramework):
    def add_options(self, parser):
        self.add_wallet_options(parser, legacy=False)

    def set_test_params(self):
        self.num_nodes = 2
        self.setup_clean_chain = True
        self.wallet_names = [False, False]
        # Reuse the transparent-wallet diagnostic regtest profile from the
        # retained producer's prior funded fixture; no mainnet/release claim.
        flags = ["-fallbackfee=0.0002", "-swapnet=0", "-autoshieldcoinbase=0",
                 "-regtestmatmulbindingheight=2147483647",
                 "-regtestmatmulproductdigestheight=2147483647",
                 "-regtestmatmulv4height=2147483647",
                 "-regtestmatmulrequireproductpayload=0", "-autoupdate=0",
                 "-dbcache=16", "-par=1"]
        self.extra_args = [list(flags), list(flags)]

    def skip_test_if_missing_module(self):
        self.skip_if_no_wallet()
        self.skip_if_no_sqlite()

    @staticmethod
    def record(stage, **public):
        # Explicit, public-only evidence. Never serialize RPC inputs or bundles.
        destination = os.environ.get("BTX917_PROGRESS_FILE")
        if destination:
            with Path(destination).open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"stage": stage, "status": "PASS", **public}) + "\n")

    def seed_wallet(self, name, byte):
        # Synthetic fixture seeds and all RPC/debug logs stay in disposable scratch.
        path = self.nodes[0].datadir_path / (name + "-input.btxwallet.json")
        path.write_text(json.dumps({"format": "btx-wallet-bundle", "version": 1,
                                   "network": "regtest", "pq_master_seed": byte * 32,
                                   "coin_type": 1, "account": 0, "birthday": 1,
                                   "algorithms": ["ml-dsa-44", "slh-dsa-128s"]}))
        result = self.nodes[0].restorewalletbundle(name, str(path), None, False)
        assert_equal(result["success"], True)
        wallet = self.nodes[0].get_wallet_rpc(name)
        out = self.nodes[0].datadir_path / (name + "-baseline.btxwallet.json")
        assert_equal(wallet.exportwalletbundle(str(out), None, 1)["success"], True)
        bundle = json.loads(out.read_text())
        assert_equal(len(bundle["descriptors"]), 2)
        return wallet, bundle

    @staticmethod
    def active_pair(wallet):
        rows = [row for row in wallet.listdescriptors()["descriptors"]
                if row.get("active") and "pqhd(" in row["desc"]]
        assert_equal(len(rows), 2)
        assert_equal({bool(row.get("internal", False)) for row in rows}, {False, True})
        return {bool(row.get("internal", False)): row["desc"] for row in rows}

    def import_pair(self, wallet, bundle, *, receive_only=False):
        requests = [{"desc": desc, "timestamp": "now", "active": True,
                     "internal": bool(side), "range": [0, 5], "next_index": 0}
                    for side, desc in enumerate(bundle["descriptors"])
                    if not receive_only or side == 0]
        result = wallet.importdescriptors(requests, [], [bundle["pq_master_seed"]])
        assert_equal(len(result), len(requests))
        assert all(row["success"] for row in result)

    def recover_spend(self, name, wallet, expected, address, change_address, txid):
        source, receiver = self.nodes
        # Export before unloading; the original wallet is not visible to node1.
        out = source.datadir_path / (name + "-export.btxwallet.json")
        result = wallet.exportwalletbundle(str(out), None, 1)
        assert_equal(result["success"], True)
        exported = json.loads(out.read_text())
        assert_equal(exported["pq_master_seed"], expected["pq_master_seed"])
        source.unloadwallet(name)
        assert name not in source.listwallets()
        copied = receiver.datadir_path / (name + "-independent.btxwallet.json")
        shutil.copy2(out, copied)
        restored_name = "restored-" + name
        result = receiver.restorewalletbundle(restored_name, str(copied), None, True)
        assert_equal(result["success"], True)
        restored = receiver.get_wallet_rpc(restored_name)
        assert_equal(self.active_pair(restored), dict(enumerate(expected["descriptors"])))
        # Rescan may advance the receive index past funded index0. Verify the
        # known pair-derived receive/change addresses, not the next unused index.
        receive_info = restored.getaddressinfo(address)
        change_info = restored.getaddressinfo(change_address)
        assert receive_info["ismine"] and change_info["ismine"]
        assert not receive_info["iswatchonly"] and not change_info["iswatchonly"]
        assert_equal(receive_info["parent_desc"], expected["descriptors"][0])
        assert_equal(change_info["parent_desc"], expected["descriptors"][1])
        coins = [u for u in restored.listunspent() if u["txid"] == txid and u["address"] == address]
        assert_equal(len(coins), 1)
        coin = coins[0]
        assert coin["spendable"] and coin["confirmations"] >= 1
        # Lock every other UTXO: a successful spend must consume this known output.
        others = [{"txid": u["txid"], "vout": u["vout"]} for u in restored.listunspent()
                  if (u["txid"], u["vout"]) != (coin["txid"], coin["vout"])]
        if others:
            assert restored.lockunspent(False, others)
        spend = restored.sendtoaddress(self.miner.getnewaddress(), Decimal("1.0"))
        decoded = receiver.decoderawtransaction(restored.gettransaction(spend)["hex"])
        assert any(vin["txid"] == txid and vin["vout"] == coin["vout"] for vin in decoded["vin"])
        self.sync_mempools()
        assert spend in source.getrawmempool()
        self.generatetoaddress(source, 1, self.miner.getnewaddress())
        self.sync_blocks()
        assert restored.gettransaction(spend)["confirmations"] >= 1
        assert all(not (u["txid"] == txid and u["vout"] == coin["vout"])
                   for u in restored.listunspent())
        return {"receive_address": address, "change_address": change_address,
                "outpoint": {"txid": txid, "vout": coin["vout"]},
                "spend_txid": spend, "confirmations": restored.gettransaction(spend)["confirmations"],
                "source_wallet_unloaded": True, "exported_seed_matches": True,
                "parent_descriptors_match": True, "known_input_consumed": True}

    def run_test(self):
        source, receiver = self.nodes
        source.createwallet("miner", descriptors=True)
        self.miner = source.get_wallet_rpc("miner")
        self.generatetoaddress(source, 101, self.miner.getnewaddress())
        self.sync_blocks()
        control, first = self.seed_wallet("control", "11")
        donor, second = self.seed_wallet("donor", "22")
        changed, initial = self.seed_wallet("changed", "33")
        mixed, _ = self.seed_wallet("mixed", "44")
        assert_equal(self.active_pair(control), dict(enumerate(first["descriptors"])))
        previous = self.active_pair(changed)
        assert previous != self.active_pair(donor)
        self.import_pair(changed, second)
        assert_equal(self.active_pair(changed), dict(enumerate(second["descriptors"])))
        # Keep the prior pair as inactive entries, the condition #917 must handle.
        all_desc = changed.listdescriptors()["descriptors"]
        assert all(any(row["desc"] == desc and not row.get("active") for row in all_desc)
                   for desc in previous.values())
        control_address, control_change = control.getnewaddress(), control.getrawchangeaddress()
        changed_address, changed_change = changed.getnewaddress(), changed.getrawchangeaddress()
        assert_equal(control_address, first["first_receive_address"])
        assert_equal(changed_address, second["first_receive_address"])
        assert changed_address != initial["first_receive_address"]
        control_tx = self.miner.sendtoaddress(control_address, Decimal("2.0"))
        changed_tx = self.miner.sendtoaddress(changed_address, Decimal("2.0"))
        self.generatetoaddress(source, 1, self.miner.getnewaddress())
        self.sync_blocks()
        self.record("control", **self.recover_spend(
            "control", control, first, control_address, control_change, control_tx))
        # Remove the donor too, leaving node1 with only the exported changed bundle.
        source.unloadwallet("donor")
        self.record("replacement", original_pair_inactive=True, replacement_distinct=True,
                    **self.recover_spend("changed", changed, second, changed_address, changed_change, changed_tx))
        before_mixed = self.active_pair(mixed)
        self.import_pair(mixed, second, receive_only=True)
        after_mixed = self.active_pair(mixed)
        assert_equal(after_mixed[False], second["descriptors"][0])
        assert_equal(after_mixed[True], before_mixed[True])
        assert after_mixed[True] != second["descriptors"][1]
        refused = source.datadir_path / "mixed-refused.btxwallet.json"
        assert not refused.exists()
        assert_raises_rpc_error(-4, "Wallet contains multiple PQ master seeds",
                                mixed.exportwalletbundle, str(refused), None, 1)
        assert not refused.exists()
        self.record("mixed_refusal", error_code=-4, mixed_pair_proven=True, output_absent=True)


if __name__ == "__main__":
    ActivePairRecoveryTest(__file__).main()
