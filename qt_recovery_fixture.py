#!/usr/bin/env python3
# Copyright (c) 2026 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Compare native Qt recovery on a disposable encrypted stale backup."""

from decimal import Decimal
import os
import subprocess
import time
from pathlib import Path
import pyatspi

from test_framework.authproxy import JSONRPCException
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, assert_raises_rpc_error


def shown_text(text):
    found = False
    def visit(node, depth=0):
        nonlocal found
        if found or depth > 25:
            return
        try:
            if text in node.name and node.getState().contains(pyatspi.STATE_SHOWING):
                found = True
            for child in node:
                if child is not None:
                    visit(child, depth+1)
        except (RuntimeError, AttributeError):
            pass
    visit(pyatspi.Registry.getDesktop(0))
    return found

def shown_buttons(prefix):
    matches = []
    def visit(node, depth=0):
        if depth > 25:
            return
        try:
            if node.getRoleName() == "push button" and node.name.lstrip("&").startswith(prefix):
                if node.getState().contains(pyatspi.STATE_SHOWING):
                    matches.append(node)
            for child in node:
                if child is not None:
                    visit(child, depth+1)
        except (RuntimeError, AttributeError):
            pass
    visit(pyatspi.Registry.getDesktop(0))
    return matches

def wait_for(predicate, seconds=25):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        result = predicate()
        if result:
            return result
        time.sleep(0.15)
    raise AssertionError("Expected native Qt observation unavailable")

def xdotool(*args):
    subprocess.run(["xdotool", *map(str, args)], check=True, timeout=6)

def click(label):
    (button,) = wait_for(lambda: shown_buttons(label))
    pos = button.queryComponent().getExtents(pyatspi.DESKTOP_COORDS)
    assert pos.width > 0 and pos.height > 0
    xdotool("mousemove", pos.x + pos.width//2, pos.y + pos.height//2, "click", 1)

def window(title):
    def match():
        query = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", "^" + title + "$"],
                               capture_output=True, text=True, timeout=5)
        return query.stdout.split()
    (window_id,) = wait_for(match)
    xdotool("windowactivate", "--sync", window_id)

class EncryptedBackupRecoveryTest(BitcoinTestFramework):
    def add_options(self, parser):
        self.add_wallet_options(parser, legacy=False)

    def set_test_params(self):
        self.num_nodes = 1
        self.setup_clean_chain = True
        # Wallet-only fixture: explicitly avoid the independent default-consensus
        # block-100 setup problem. These policies do not qualify consensus.
        self.extra_args = [[
            "-keypool=4", "-modelnet=0", "-autoshieldcoinbase=0",
            "-connect=0", "-dnsseed=0", "-matmulvalidation=economic",
            "-matmulrcexecution=cpu-diagnostic",
        ]]

    def skip_test_if_missing_module(self):
        self.skip_if_no_wallet()
        self.skip_if_no_sqlite()

    def run_test(self):
        node = self.nodes[0]
        passphrase = "disposable-regtest-only"
        receipt_txids = []

        def receipts(wallet, addresses):
            # Check recognition, not AvailableCoins/locked signing capability.
            rows = []
            for txid in receipt_txids:
                try:
                    tx = wallet.gettransaction(txid)
                except JSONRPCException as error:
                    if error.error["code"] == -5:
                        continue
                    raise
                assert tx["confirmations"] >= 1
                rows.extend(
                    (f"{txid}:{detail['vout']}", detail["amount"])
                    for detail in tx["details"]
                    if detail["category"] == "receive" and detail.get("address") in addresses
                )
            return sorted(outpoint for outpoint, _ in rows), sum((amount for _, amount in rows), Decimal(0))

        node.createwallet(wallet_name="funder", descriptors=True)
        funder = node.get_wallet_rpc("funder")
        mining_address = funder.getnewaddress()
        self.generatetoaddress(node, 101, mining_address, sync_fun=self.no_op)

        cases = {}
        for name, encrypted in [("encrypted", True), ("plain", False)]:
            node.createwallet(wallet_name=name, descriptors=True, **({"passphrase": passphrase} if encrypted else {}))
            wallet = node.get_wallet_rpc(name)
            if encrypted:
                wallet.walletpassphrase(passphrase, 600)
            known_address = wallet.getnewaddress()
            remaining = wallet.getwalletinfo()["keypoolsize"]
            assert 0 < remaining <= 32
            backup = node.datadir_path / f"{name}-stale.bak"
            wallet.backupwallet(str(backup))
            # A genuinely issued address just beyond the backup's cached range.
            for _ in range(remaining + 1):
                later_address = wallet.getnewaddress()
            assert later_address != known_address
            if encrypted:
                wallet.walletlock()
            cases[name] = {"wallet": wallet, "addresses": [known_address, later_address], "backup": backup}

        # Separate blocks let the unencrypted restore extend its range when it
        # encounters the earlier known script, before the later payment.
        for position in (0, 1):
            destinations = {case["addresses"][position]: Decimal(position + 1) for case in cases.values()}
            receipt_txids.append(funder.sendmany("", destinations))
            self.generatetoaddress(node, 1, mining_address, sync_fun=self.no_op)

        for name, case in cases.items():
            expected, total = receipts(case["wallet"], case["addresses"])
            assert_equal(len(expected), 2)
            assert_equal(total, Decimal(3))
            case["expected"] = expected
            node.unloadwallet(name)
        self.log.info("CONTROL: original locked encrypted wallet recognizes both receipts")

        assert_raises_rpc_error(-8, "Backup file does not exist", node.restorewallet,
                                "missing-backup", str(node.datadir_path / "does-not-exist.bak"))
        assert "missing-backup" not in node.listwallets()

        plain = cases["plain"]
        plain_result = node.restorewallet("plain-restored", str(plain["backup"]))
        assert_equal(receipts(node.get_wallet_rpc("plain-restored"), plain["addresses"]), (plain["expected"], Decimal(3)))
        self.log.info("CONTROL: plain backup recovers both receipts without encrypted recovery warning")

        case = cases["encrypted"]
        restored = node.restorewallet("encrypted-restored", str(case["backup"]))
        wallet = node.get_wallet_rpc("encrypted-restored")
        warnings = restored.get("warnings", [])
        assert any("contains shielded state" in warning for warning in warnings)
        assert_equal(wallet.getwalletinfo()["unlocked_until"], 0)
        before_receipts, _ = receipts(wallet, case["addresses"])
        assert_equal(len(before_receipts), 1)
        assert_raises_rpc_error(-13, "walletpassphrase", wallet.keypoolrefill)
        assert_raises_rpc_error(-14, "incorrect", wallet.walletpassphrase, "wrong-disposable-passphrase", 600)
        assert_equal(wallet.getwalletinfo()["unlocked_until"], 0)
        assert_equal(receipts(wallet, case["addresses"])[0], before_receipts)

        tip = node.getbestblockhash()
        root = Path(os.environ["RECOVERY_RECORDS"])
        gate, observed = root/"delay.gate", root/"delay.observed"
        qt = os.environ["RECOVERY_QT"]
        profile = node.datadir_path / "isolated-qt"
        profile.mkdir(mode=0o700)
        for name in ("runtime", "config", "data"):
            (profile/name).mkdir(mode=0o700)
        self.stop_node(0)
        node.args[0] = qt
        self.start_node(0, extra_args=node.extra_args + [
            "-server=1", "-splash=0", "-wallet=encrypted-restored"
        ], env={"QT_LINUX_ACCESSIBILITY_ALWAYS_ON": "1", "QT_QPA_PLATFORM": "xcb",
                "XDG_RUNTIME_DIR": str(profile/"runtime"),
                "XDG_CONFIG_HOME": str(profile/"config"),
                "XDG_DATA_HOME": str(profile/"data"),
                "LC_ALL": "C.UTF-8",
                "LD_PRELOAD": os.environ["RECOVERY_DELAY_LIBRARY"],
                "BTX_RECOVERY_DELAY_GATE": str(gate),
                "BTX_RECOVERY_DELAY_OBSERVED": str(observed)})
        assert_equal(node.listwallets(), ["encrypted-restored"])
        wallet = node.get_wallet_rpc("encrypted-restored")
        assert_equal(receipts(wallet, case["addresses"])[0], before_receipts)
        assert_raises_rpc_error(-13, "walletpassphrase", wallet.keypoolrefill)
        # On the ordinary Transactions tab, establish that the window and
        # accessibility are working before interpreting a missing control.
        wait_for(lambda: subprocess.run(["xdotool", "search", "--onlyvisible", "--name", "regtest"],
                    capture_output=True, timeout=5).returncode == 0)
        ids = subprocess.check_output(["xdotool", "search", "--onlyvisible", "--name", "regtest"],
                                      text=True, timeout=5).split()
        assert len(ids) == 1, ids
        xdotool("windowactivate", "--sync", ids[0])
        xdotool("key", "alt+4")
        wait_for(lambda: shown_buttons("Export"))
        if os.environ["RECOVERY_VARIANT"] == "baseline":
            assert not shown_buttons("Recover missing payments")
            self.log.info("BASELINE: Transactions tab renders and has no recovery action")
            return

        def begin(unlock=True):
            click("Recover missing payments")
            window("Recover missing payments")
            xdotool("key", "Return")  # Accept the displayed finite default of 20.
            click("Yes")
            if not unlock:
                return
            window("Unlock wallet")
            xdotool("type", "--clearmodifiers", "--", passphrase)
            xdotool("key", "Return")

        gate.touch()
        try:
            begin()
            wait_for(observed.is_file)
            click("Cancel")
        finally:
            gate.unlink(missing_ok=True)
        window("Recovery incomplete")
        wait_for(lambda: shown_text("Rescan aborted."))
        xdotool("key", "Return")
        wait_for(lambda: wallet.getwalletinfo()["scanning"] is False)
        assert_raises_rpc_error(-13, "walletpassphrase", wallet.keypoolrefill)
        assert_equal(receipts(wallet, case["addresses"])[0], before_receipts)
        self.log.info("CANDIDATE: active scan cancelled, reservation released, wallet relocked")
        begin()
        window("Recovery complete")
        subprocess.run(["scrot", str(root/"recovery-complete.png")], check=True, timeout=5)
        xdotool("key", "Return")
        assert_equal(receipts(wallet, case["addresses"]), (case["expected"], Decimal(3)))
        assert_equal(node.getbestblockhash(), tip)
        assert_raises_rpc_error(-13, "walletpassphrase", wallet.keypoolrefill)
        assert wallet.getwalletinfo()["scanning"] is False
        self.log.info("CANDIDATE: retry recovered both exact outpoints at the same tip and relocked")
        wallet.walletpassphrase(passphrase, 600)
        begin(unlock=False)
        window("Recovery complete")
        xdotool("key", "Return")
        wallet.keypoolrefill(1)  # An already-unlocked wallet is not relocked by the action.
        rpc_scan = wallet.rescanblockchain(0)
        assert_equal(rpc_scan["stop_height"], node.getblockcount())
        assert_equal(receipts(wallet, case["addresses"]), (case["expected"], Decimal(3)))
        wallet.walletlock()
        self.log.info("CONTROL: direct RPC rescan still reaches the same tip and preserves both receipts")
        self.log.info("CONTROL: action preserved an existing unlock and its RPC relock policy")


if __name__ == "__main__":
    EncryptedBackupRecoveryTest(__file__).main()
