#!/usr/bin/env python3
"""PRIVATE observational pilot. Ordinary convergence is not PR794 qualification."""
import json
import os
from pathlib import Path
import re
import sys
import time

SOURCE = Path(os.environ.get('BTX_PR794_SOURCE', Path(__file__).resolve().parents[1] / 'source')).resolve()
sys.path.insert(0, str(SOURCE / 'test' / 'functional'))
from test_framework.authproxy import JSONRPCException
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, p2p_port


class RealNodesPilot(BitcoinTestFramework):
    def add_options(self, parser):
        parser.add_argument('--require-pr794-path', action='store_true')
        parser.add_argument('--short-branch', type=int, choices=(6, 20), default=6,
                            help='6: primary ordinary-reorg pilot; 20: separate author topology, default policy may park')
        parser.add_argument('--pilot-timeout', type=int, default=90)
        parser.add_argument('--receipt', help='Absolute receipt path, default in disposable tmpdir')

    def set_test_params(self):
        self.num_nodes = 2
        self.setup_clean_chain = True
        self.extra_args = [['-debug=net', '-debug=validation', '-disablewallet'] for _ in range(2)]

    def connect_real_outbound(self):
        source, receiver = self.nodes
        receiver.addconnection(f"127.0.0.1:{p2p_port(0)}", "outbound-full-relay", False)
        def peers_ready(node, tag, inbound):
            return any(tag in p['subver'] and p['inbound'] == inbound and
                       p.get('bytesrecv_per_msg', {}).get('pong', 0) >= 29
                       for p in node.getpeerinfo())
        self.wait_until(lambda: peers_ready(receiver, 'testnode0', False))
        self.wait_until(lambda: peers_ready(source, 'testnode1', True))
        peer = next(p for p in receiver.getpeerinfo() if not p['inbound'] and 'testnode0' in p['subver'])
        assert_equal(peer['connection_type'], 'outbound-full-relay')
        assert 'noban' not in peer.get('permissions', [])

    def snapshot(self):
        return [{'best': n.getbestblockhash(), 'height': n.getblockcount(),
                 'chain': n.getblockchaininfo(), 'tips': n.getchaintips(),
                 'peers': n.getpeerinfo()} for n in self.nodes]

    def known_header(self, node, h):
        try:
            return node.getblockheader(h)
        except JSONRPCException as e:
            if e.error['code'] != -5:
                raise
            return None

    def has_body(self, node, h):
        try:
            node.getblock(h, 0)
            return True
        except JSONRPCException as e:
            if e.error['code'] not in (-1, -5):
                raise
            return False

    def run_test(self):
        source, receiver = self.nodes
        r = {'scope': 'PRIVATE two actual btxd processes, observational reachability',
             'source_tree': str(SOURCE), 'short_branch': self.options.short_branch,
             'intended_path': 'UNPROVED', 'workflow': 'NOT_COMPLETED', 'snapshots': {},
             'profile': 'wallet-disabled maintained regtest; framework Phase-A/economic/cpu-diagnostic defaults; product fork choice unchanged'}
        target = Path(self.options.receipt or (Path(self.options.tmpdir) / 'pr794-receipt.json'))
        assert target.is_absolute(), '--receipt must be absolute'
        assert 1 <= self.options.pilot_timeout <= 300, 'pilot timeout must be 1..300 seconds'
        try:
            self.generate(source, 1)
            self.disconnect_nodes(1, 0)
            self.generate(receiver, self.options.short_branch, sync_fun=self.no_op)
            heavy = self.generate(source, 93, sync_fun=self.no_op)
            r['heavy_hashes'] = heavy
            r['snapshots']['partitioned'] = self.snapshot()
            self.connect_real_outbound()
            peers = [p for p in receiver.getpeerinfo() if not p['inbound'] and 'testnode0' in p['subver']]
            assert_equal(len(peers), 1)
            peer_id = peers[0]['id']
            r['receiver_outbound_peer_id'] = peer_id
            r['receiver_connection_type'] = peers[0].get('connection_type')
            source_peers = [p for p in source.getpeerinfo() if p['inbound'] and 'testnode1' in p['subver']]
            assert_equal(len(source_peers), 1)
            r['source_inbound_peer_id'] = source_peers[0]['id']
            r['snapshots']['after_handshake'] = self.snapshot()
            r['headers_known_after_handshake'] = [h for h in heavy if self.known_header(receiver, h)]
            r['live_parent_known_before_announcement'] = bool(self.known_header(receiver, heavy[-1]))
            fresh = self.generate(source, 1, sync_fun=self.no_op)[0]
            r['first_live_extension'] = fresh
            deadline = time.monotonic() + self.options.pilot_timeout
            while time.monotonic() < deadline:
                if not any(p['id'] == peer_id for p in receiver.getpeerinfo()):
                    r['original_peer_retained'] = False
                    break
                if receiver.getbestblockhash() == fresh:
                    break
                time.sleep(0.1)
            r['snapshots']['after_recovery_window'] = self.snapshot()
            r['original_peer_retained'] = any(p['id'] == peer_id for p in receiver.getpeerinfo())
            r['acquired_heavy_headers'] = [h for h in heavy if self.known_header(receiver, h)]
            r['acquired_heavy_bodies'] = [h for h in heavy if self.has_body(receiver, h)]
            r['acquired_live_body'] = self.has_body(receiver, fresh)
            if not r['original_peer_retained']:
                raise AssertionError('Original real source peer disconnected; inspect exact logs')
            if receiver.getbestblockhash() != fresh:
                # Deep-reorg parking is a valid product decision. Preserve evidence
                # rather than override it or call body acquisition active catch-up.
                r['workflow'] = 'INCOMPLETE_active_chain_did_not_converge_inspect_policy_and_downloads'
                if self.options.short_branch == 6:
                    raise AssertionError('Shallow pilot did not converge within bound; inspect policy, headers and bodies')
            else:
                self.generate(source, 2)
                r['snapshots']['fresh_progress'] = self.snapshot()
                assert any(p['id'] == peer_id for p in receiver.getpeerinfo()), 'Original peer lost during fresh progress'
                before = source.getbestblockhash()
                self.restart_node(1)
                assert_equal(receiver.getbestblockhash(), before)
                self.connect_real_outbound()
                self.generate(source, 2)
                assert_equal(receiver.getbestblockhash(), source.getbestblockhash())
                r['snapshots']['restart_and_progress'] = self.snapshot()
                r['workflow'] = 'PASS_exact_hash_catchup_fresh_blocks_restart_fresh_blocks'
        except Exception as e:
            r['failure'] = f'{type(e).__name__}: {e}'
            raise
        finally:
            logs = [n.debug_log_path.read_text(errors='replace') for n in self.nodes]
            pid = str(r.get('receiver_outbound_peer_id', 'NO_PEER'))
            skipped = re.findall(r'skipping unauthenticated header lead ([0-9a-f]{64})', logs[1])
            missing = re.findall(r'received header ([0-9a-f]{64}): missing prev block ([0-9a-f]{64}).*?\(peer=' + pid + r'\)', logs[1])
            dropped = re.findall(r'Dropping block ([0-9a-f]{64}) from peer=' + pid + r': its announced header did not connect', logs[1])
            source_pid = str(r.get('source_inbound_peer_id', 'NO_PEER'))
            sent = re.findall(r'sending next honest body ([0-9a-f]{64}).*?to behind peer=' + source_pid + r'\b', logs[0])
            sent += re.findall(r'sending full block ([0-9a-f]{64}) to peer=' + source_pid + r'\b', logs[0])
            matched = []
            real_announcements = []
            for h, parent in missing:
                skip_pos = logs[1].find('skipping unauthenticated header lead ' + parent)
                missing_pos = logs[1].find('received header ' + h + ': missing prev block ' + parent)
                drop_pos = logs[1].find('Dropping block ' + h + ' from peer=' + pid + ':')
                if h in sent and 0 <= skip_pos < missing_pos:
                    real_announcements.append(h)
                if h in dropped and h in sent and 0 <= skip_pos < missing_pos < drop_pos:
                    matched.append(h)
            # Missing-prev log is conditional on the getheaders throttle. The
            # candidate drop itself requires HandleUnconnectingHeaders' marker.
            for h in dropped:
                drop_pos = logs[1].find('Dropping block ' + h + ' from peer=' + pid + ':')
                skip_positions = [logs[1].find('skipping unauthenticated header lead ' + x) for x in skipped]
                if (h == r.get('first_live_extension') and h in sent and
                    r.get('live_parent_known_before_announcement') is False and
                    any(0 <= pos < drop_pos for pos in skip_positions)):
                    if h not in matched: matched.append(h)
            r['path_evidence'] = {'skipped_headers': skipped, 'unconnecting': missing,
                                 'dropped_announced_bodies': dropped,
                                 'sender_next_honest_bodies': sent, 'matched_real_sender_hashes': matched,
                                 'real_unconnecting_announcements': real_announcements}
            needles = ('skipping unauthenticated header lead', 'missing prev block',
                       'its announced header did not connect', 'prev-blk-not-found',
                       'Disconnecting peer=', 'parked', 'hysteresis')
            r['receiver_evidence_lines'] = [l for l in logs[1].splitlines() if any(s in l for s in needles)]
            r['intended_path'] = ('OBSERVED_candidate_header_and_body_branch' if matched else
                                  'OBSERVED_real_unconnecting_header_only' if real_announcements else
                                  'NON_REPRODUCTION_not_PR794_qualification')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(r, indent=2, default=str) + '\n')
            self.log.info('PRIVATE receipt %s: workflow=%s intended_path=%s', target, r['workflow'], r['intended_path'])
        if self.options.require_pr794_path:
            assert r['path_evidence']['matched_real_sender_hashes'], 'PR794 path not proved; ordinary sync does not qualify'
            assert r['workflow'].startswith('PASS_'), 'Full active-chain recovery workflow not completed'


if __name__ == '__main__':
    RealNodesPilot(__file__).main()
