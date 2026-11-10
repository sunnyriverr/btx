#!/usr/bin/env python3
# Copyright (c) 2026 The BTX developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://opensource.org/license/mit/.
"""Observe loaded shielded state during a real native Qt unlock; never send.

Requires a disposable Linux/X11 test-framework runtime. Exit zero means that
the observation and RPC control completed, not that Qt accounting was correct.
See fixture-notes.md for scope, provenance requirements and interpretation.
"""

from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

if os.environ.get("QT_SHIELDED_FUNCTIONAL"):
    sys.path.insert(0, os.environ["QT_SHIELDED_FUNCTIONAL"])

import pyatspi

from test_framework.blocktools import REGTEST_GENERIC_P2P_MATMUL_ARGS
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, assert_raises_rpc_error


PASSPHRASE = "disposable-qt-shielded-state"
WALLET = "qt-shielded-observation"
ERROR_TEXT = "The amount exceeds your balance."


def walk_accessible(node, depth=0):
    if depth > 25:
        return
    try:
        if node.getState().contains(pyatspi.STATE_SHOWING):
            yield node
        for child in node:
            if child is not None:
                yield from walk_accessible(child, depth + 1)
    except (RuntimeError, AttributeError):
        return


def shown_text(text):
    return any(text in node.name for node in walk_accessible(pyatspi.Registry.getDesktop(0)))


def wait_for(predicate, description, seconds=30):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        value = predicate()
        if value:
            return value
        time.sleep(0.15)
    raise AssertionError(f"Native observation unavailable: {description}")


def xdotool(*args):
    subprocess.run(["xdotool", *map(str, args)], check=True, timeout=6)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def window(title):
    def matching():
        query = subprocess.run(
            ["xdotool", "search", "--onlyvisible", "--name", title],
            capture_output=True, text=True, timeout=5,
        )
        ids = query.stdout.split()
        return ids if len(ids) == 1 else None
    (window_id,) = wait_for(matching, f"exactly one visible window matching {title!r}")
    xdotool("windowactivate", "--sync", window_id)


class QtLoadedShieldedStateObservation(BitcoinTestFramework):
    def add_options(self, parser):
        self.add_wallet_options(parser, legacy=False)

    def set_test_params(self):
        self.num_nodes = 1
        self.setup_clean_chain = True
        # Same wallet-only regtest height overrides used by #499. These are
        # fixture prerequisites, not consensus/production qualification.
        self.extra_args = [list(REGTEST_GENERIC_P2P_MATMUL_ARGS) + [
            "-autoshieldcoinbase=0", "-nomodelnet", "-keypool=4",
            "-connect=0", "-dnsseed=0", "-persistmempool=1",
        ]]
        self.rpc_timeout = 300

    def skip_test_if_missing_module(self):
        self.skip_if_no_wallet()
        self.skip_if_no_sqlite()

    def run_test(self):
        self.records = Path(os.environ["QT_SHIELDED_RECORDS"]).resolve()
        self.records.mkdir(parents=True, exist_ok=True)
        self.result = {"schema_version": 1, "status": "setup_in_progress", "stages": {}}
        try:
            self.observe()
        except Exception:
            self.result["status"] = "fixture_or_control_failure"
            self.result["exception"] = traceback.format_exc()
            self.capture_desktop("failure")
            raise
        finally:
            self.save()

    def save(self):
        (self.records / "observation.json").write_text(
            json.dumps(self.result, indent=2, sort_keys=True, default=str) + "\n"
        )

    def capture_desktop(self, label):
        # Diagnostics must not mask the product/control observation.
        try:
            rows = [f"{node.getRoleName()}: {node.name}"
                    for node in walk_accessible(pyatspi.Registry.getDesktop(0))]
            (self.records / f"{label}-accessibility.txt").write_text("\n".join(rows) + "\n")
            windows = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, timeout=5)
            (self.records / f"{label}-windows.txt").write_text(windows.stdout)
            subprocess.run(["scrot", str(self.records / f"{label}.png")], check=False, timeout=5)
        except Exception as error:
            self.result.setdefault("diagnostic_errors", []).append(str(error))

    def snapshot(self, label):
        node = self.nodes[0]
        wallet = node.get_wallet_rpc(WALLET)
        node.syncwithvalidationinterfacequeue()
        notes = wallet.z_listunspent(0, 9999999, False, True)
        # Preserve every returned field, not just count or balance. This fixture
        # uses only disposable keys, and explicitly requests unredacted note IDs.
        notes = sorted(notes, key=lambda row: json.dumps(row, sort_keys=True, default=str))
        state = {
            "balance_0": wallet.z_getbalance(0),
            "balance_1": wallet.z_getbalance(1),
            "notes": notes,
            "wallet_info": wallet.getwalletinfo(),
            "mempool": sorted(node.getrawmempool()),
            "tip": node.getbestblockhash(),
        }
        self.result["stages"][label] = state
        self.save()
        return state

    @staticmethod
    def accounting(state):
        return {field: state[field] for field in ("balance_0", "balance_1", "notes")}

    def observe(self):
        node = self.nodes[0]
        qt = Path(os.environ["QT_SHIELDED_QT"]).resolve(strict=True)
        qt_digest = sha256_file(qt)
        expected_digest = os.environ.get("QT_SHIELDED_QT_SHA256")
        if expected_digest:
            assert_equal(qt_digest, expected_digest)
        self.result["inputs"] = {
            "qt_binary": str(qt), "qt_sha256": qt_digest,
            "qt_expected_sha256": expected_digest,
            "source_contract": "release dac9aee5 + unchanged #498 a2ee89e7 + #499 57c98fa3",
            "extra_args": self.extra_args[0],
            "fixture_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        }

        node.createwallet(wallet_name="miner", descriptors=True)
        miner = node.get_wallet_rpc("miner")
        node.createwallet(wallet_name=WALLET, descriptors=True, passphrase=PASSPHRASE)
        wallet = node.get_wallet_rpc(WALLET)
        # Initial setup unlock is allowed. No RPC unlock is used again until
        # the native observation, cancellation and relock have been recorded.
        wallet.walletpassphrase(PASSPHRASE, 600)
        zaddr = wallet.z_getnewaddress()
        transparent_address = wallet.getnewaddress(address_type="p2mr")
        destination = miner.getnewaddress(address_type="p2mr")
        mining_address = miner.getnewaddress(address_type="p2mr")
        self.generatetoaddress(node, 3, transparent_address, sync_fun=self.no_op)
        self.generatetoaddress(node, 101, mining_address, sync_fun=self.no_op)

        confirmed_txid = wallet.z_shieldcoinbase(zaddr, None, 1)["txid"]
        self.generatetoaddress(node, 1, mining_address, sync_fun=self.no_op)
        pending_txid = wallet.z_shieldcoinbase(zaddr, None, 1)["txid"]
        assert pending_txid in node.getrawmempool()
        before = self.snapshot("before_locked_reload")
        assert_equal(sorted(note["confirmations"] for note in before["notes"]), [0, 1])
        assert all(note.get("nullifier") and note.get("commitment") for note in before["notes"])
        assert Decimal(str(before["balance_0"]["balance"])) > Decimal(str(before["balance_1"]["balance"])) > 0
        assert_equal(before["mempool"], [pending_txid])
        # A positive, valid monetary amount well above these three coinbases
        # makes PrepareSendText stop at its post-unlock balance error, never at
        # signing or confirmation/broadcast. Assert the premise independently.
        attempted_amount = Decimal("1000000")
        assert wallet.getbalance() < attempted_amount
        self.result["fixture_transactions"] = {
            "confirmed_shield": confirmed_txid, "pending_shield": pending_txid,
            "native_send_attempt_amount": str(attempted_amount),
        }
        wallet.walletlock()
        for name in node.listwallets():
            if name != WALLET:
                node.unloadwallet(name, False)
        self.stop_node(0)

        profile = node.datadir_path / "isolated-native-qt"
        for name in ("runtime", "config", "data"):
            (profile / name).mkdir(mode=0o700, parents=True)
        node.args[0] = str(qt)
        self.start_node(0, extra_args=node.extra_args + [
            "-server=1", "-splash=0", f"-wallet={WALLET}",
        ], env={
            "QT_LINUX_ACCESSIBILITY_ALWAYS_ON": "1", "QT_QPA_PLATFORM": "xcb",
            "XDG_RUNTIME_DIR": str(profile / "runtime"),
            "XDG_CONFIG_HOME": str(profile / "config"),
            "XDG_DATA_HOME": str(profile / "data"), "LC_ALL": "C.UTF-8",
        })
        assert_equal(node.listwallets(), [WALLET])
        wallet = node.get_wallet_rpc(WALLET)
        wait_for(lambda: pending_txid in node.getrawmempool(), "pending shielding tx restored to mempool")
        assert_raises_rpc_error(-13, "walletpassphrase", wallet.keypoolrefill, 1)
        locked = self.snapshot("loaded_locked")
        assert_equal(locked["tip"], before["tip"])
        assert_equal(locked["mempool"], before["mempool"])

        window("regtest")
        xdotool("key", "alt+2")  # BitcoinGUI Send action.
        wait_for(lambda: shown_text("Pay") and shown_text("Amount"), "native Send form")
        # Source-declared QLabel buddies: Pay &To -> payTo; A&mount -> payAmount.
        xdotool("key", "alt+t", "ctrl+a")
        xdotool("type", "--clearmodifiers", "--", destination)
        xdotool("key", "alt+m", "ctrl+a")
        xdotool("type", "--clearmodifiers", "--", str(attempted_amount))
        xdotool("key", "alt+e")  # S&end, not the sidebar action.
        window("Unlock wallet")
        self.result["native_passphrase_dialog_observed"] = True
        self.capture_desktop("unlock-prompt")
        xdotool("type", "--clearmodifiers", "--", PASSPHRASE)
        xdotool("key", "Return")
        window("Send Coins")
        wait_for(lambda: shown_text(ERROR_TEXT), "post-unlock amount-exceeds-balance modal")
        # nRelockTime/unlocked_until stays zero for Qt unlock, so it is not a
        # lock-state oracle. A real unlock-required RPC supplies that oracle.
        wallet.keypoolrefill(1)
        self.result["native_unlock_required_rpc_succeeded"] = True
        qt_state = self.snapshot("native_qt_unlocked_error_modal")
        self.capture_desktop("native-unlocked-error")
        assert_equal(qt_state["tip"], before["tip"])
        assert_equal(qt_state["mempool"], before["mempool"])
        self.result["qt_accounting_matches_baseline"] = self.accounting(qt_state) == self.accounting(before)

        # Dismiss only the known error modal. No confirmation dialog is reached.
        xdotool("key", "Return")
        wait_for(lambda: not shown_text(ERROR_TEXT), "balance error modal dismissed")
        assert_raises_rpc_error(-13, "walletpassphrase", wallet.keypoolrefill, 1)
        self.result["native_action_relocked"] = True
        after = self.snapshot("native_error_dismissed_relocked")
        assert_equal(after["mempool"], before["mempool"])

        # Positive control on the same fixed-height, same-mempool Qt process.
        # This is the first walletpassphrase call after the locked reload.
        wallet.walletpassphrase(PASSPHRASE, 600)
        node.syncwithvalidationinterfacequeue()
        rpc_state = self.snapshot("rpc_unlock_positive_control")
        assert_equal(rpc_state["tip"], before["tip"])
        assert_equal(rpc_state["mempool"], before["mempool"])
        assert_equal(self.accounting(rpc_state), self.accounting(before))
        self.result["rpc_control_matches_baseline"] = True
        wallet.walletlock()
        assert_raises_rpc_error(-13, "walletpassphrase", wallet.keypoolrefill, 1)
        self.result["status"] = "observation_complete"
        self.result["interpretation"] = (
            "Qt accounting matches baseline" if self.result["qt_accounting_matches_baseline"]
            else "Qt accounting differs; RPC unlock restores the exact baseline accounting"
        )
        self.log.info("OBSERVATION COMPLETE: %s", self.result["interpretation"])
        self.save()


if __name__ == "__main__":
    QtLoadedShieldedStateObservation(__file__).main()
