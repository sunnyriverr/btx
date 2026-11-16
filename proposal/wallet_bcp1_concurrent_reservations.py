#!/usr/bin/env python3
# Copyright (c) 2026 The BTX developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/license/mit/.
"""Bounded observation of overlapping unsigned package reservations.

A clean run establishes bounded non-reproduction, not deterministic atomicity.
No prepared package is signed or broadcast.
"""
from decimal import Decimal
import json
from pathlib import Path
from threading import Barrier, Thread
from time import monotonic
from urllib.parse import quote

from test_framework.authproxy import AuthServiceProxy, JSONRPCException
from test_framework.blocktools import REGTEST_GENERIC_P2P_MATMUL_ARGS
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, assert_raises_rpc_error, find_vout_for_address


def selected(package):
    rows = package["selected_utxos"]
    result = {(row["txid"], row["vout"]) for row in rows}
    assert_equal(len(rows), len(result))
    return result


def outpoints(coins):
    return [{"txid": t, "vout": v} for t, v in sorted(coins)]


class ConcurrentReservationsTest(BitcoinTestFramework):
    def add_options(self, parser):
        self.add_wallet_options(parser, legacy=False)

    def set_test_params(self):
        self.num_nodes = 1
        self.setup_clean_chain = True
        self.extra_args = [list(REGTEST_GENERIC_P2P_MATMUL_ARGS) + [
            "-autoshieldcoinbase=0", "-fallbackfee=0.0002", "-rpcthreads=2", "-swapnet=0",
            "-autoupdate=0", "-dnsseed=0", "-listen=0", "-listenonion=0", "-natpmp=0",
        ]]

    def setup_network(self):
        if self.config["components"].getboolean("ENABLE_MODELNET", fallback=False):
            self.extra_args[0].append("-nomodelnet")
        self.setup_nodes()

    def skip_test_if_missing_module(self):
        self.skip_if_no_wallet()

    def locked(self):
        return {(x["txid"], x["vout"]) for x in self.venue.listlockunspent()}

    def call(self, client, kind, *, reserve=True, fee_refusal=False):
        if hasattr(self, "deadline"):
            assert monotonic() < self.deadline, "observation deadline exceeded"
        options = {"change_address": self.change, "lock_unspents": reserve,
                   "fee_rate": Decimal("2")}
        if fee_refusal:
            options["fee_ceiling"] = Decimal("0.00000001")
        if kind == "batch":
            return client.createexchangebatch(self.pay, options)
        return client.createconsolidationtx(options)

    def check_package(self, package):
        assert_equal(selected(package), self.available)
        assert_equal(package["broadcast"], False)
        assert_equal(package["complete"], False)
        return package

    def reset_and_retry(self):
        assert_equal(self.locked(), self.sentinel | self.available)
        self.venue.lockunspent(True, outpoints(self.available))
        assert_equal(self.locked(), self.sentinel)
        self.check_package(self.call(self.venue, "batch"))
        assert_equal(self.locked(), self.sentinel | self.available)
        self.venue.lockunspent(True, outpoints(self.available))
        assert_equal(self.locked(), self.sentinel)
        for txid, vout in self.available | self.sentinel:
            assert self.nodes[0].gettxout(txid, vout) is not None

    def pair(self, kinds):
        assert monotonic() < self.deadline, "bounded observation deadline exceeded"
        assert_equal(self.locked(), self.sentinel)
        barrier = Barrier(2, timeout=10)
        results = [None, None]

        def worker(index):
            try:
                # A new root proxy creates a new HTTP connection. Do not derive
                # both clients from node.rpc, which shares its connection.
                client = AuthServiceProxy(self.wallet_url, timeout=10)
                barrier.wait()
                try:
                    results[index] = {"package": self.call(client, kinds[index])}
                except JSONRPCException as error:
                    results[index] = {"error": error.error}
            except Exception as error:
                results[index] = {"unexpected": repr(error)}
                barrier.abort()

        threads = [Thread(target=worker, args=(i,), daemon=True) for i in range(2)]
        for thread in threads:
            thread.start()
        join_deadline = monotonic() + 12
        for thread in threads:
            thread.join(max(0, join_deadline - monotonic()))
        self.observations.append({"kinds": kinds, "responses": results,
                                  "threads_finished": all(not t.is_alive() for t in threads)})
        self.save_observations()
        assert all(not t.is_alive() for t in threads), "client did not finish; stop node via framework cleanup"
        assert all(r is not None and "unexpected" not in r for r in results), results
        successes = [r["package"] for r in results if "package" in r]
        # Preserve both raw responses before this detects overlapping winners.
        assert_equal(len(successes), 1)
        self.check_package(successes[0])
        for kind, result in zip(kinds, results):
            if "error" in result:
                code, message = (-4, "Insufficient funds") if kind == "batch" else (-6, "no deposit UTXOs")
                assert_equal(result["error"]["code"], code)
                assert message in result["error"]["message"], result
        self.reset_and_retry()

    def save_observations(self):
        self.record_path.write_text(json.dumps(self.observations, default=str, indent=2))

    def run_test(self):
        node = self.nodes[0]
        node.createwallet("miner")
        node.createwallet("source")
        node.createwallet("venue", disable_private_keys=True, blank=True)
        miner = node.get_wallet_rpc("miner")
        source = node.get_wallet_rpc("source")
        self.venue = node.get_wallet_rpc("venue")
        mining_address = miner.getnewaddress()
        self.generatetoaddress(node, 110, mining_address)
        keys = [source.getaddressinfo(source.getnewaddress())["pubkey"] for _ in range(3)]
        addresses = [node.deriveaddresses(f"mr({key})", None, {"require_checksum": False})[0] for key in keys]
        self.venue.importdepositpool([{"pubkey": key, "index": i} for i, key in enumerate(keys)])
        coins = []
        for address in addresses[:2]:
            txid = miner.sendtoaddress(address, Decimal("3"))
            coins.append((txid, find_vout_for_address(node, txid, address)))
        self.generatetoaddress(node, 1, mining_address)
        self.available, self.sentinel = {coins[0]}, {coins[1]}
        self.change = addresses[2]
        self.pay = [{"address": mining_address, "amount": Decimal("2")}]
        self.venue.lockunspent(False, outpoints(self.sentinel))
        assert_equal(self.venue.getwalletinfo()["private_keys_enabled"], False)
        assert_equal({(r["txid"], r["vout"]) for r in self.venue.listunspent()}, self.available)
        self.wallet_url = node.url.rstrip("/") + "/wallet/" + quote("venue", safe="")
        # Controls also get a fresh connection with a short timeout.
        self.venue = AuthServiceProxy(self.wallet_url, timeout=10)
        self.observations = []
        self.record_path = Path(self.options.tmpdir) / "concurrent-package-observations.json"
        self.deadline = monotonic() + 120
        try:
            # Sequential positive/refusal controls reject an always-refusing fixture.
            self.check_package(self.call(self.venue, "batch"))
            assert_raises_rpc_error(-4, "Insufficient funds", self.call, self.venue, "batch")
            self.reset_and_retry()
            self.check_package(self.call(self.venue, "consolidation"))
            assert_raises_rpc_error(-6, "no deposit UTXOs", self.call, self.venue, "consolidation")
            self.reset_and_retry()
            assert_raises_rpc_error(-4, "fee_ceiling", self.call, self.venue, "batch", fee_refusal=True)
            assert_equal(self.locked(), self.sentinel)
            for _ in range(2):
                self.check_package(self.call(self.venue, "batch", reserve=False))
            assert_equal(self.locked(), self.sentinel)
            for kinds in [("batch", "batch"), ("batch", "consolidation")]:
                for _ in range(25):
                    self.pair(kinds)
            self.log.info("50 bounded pairs completed; server interleaving was not forced")
        finally:
            self.save_observations()
            # On failure retain reservations/evidence; the normal framework
            # stops this disposable node. Never clear all wallet locks.


if __name__ == '__main__':
    ConcurrentReservationsTest(__file__).main()
