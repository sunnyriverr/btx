#!/usr/bin/env python3
"""AI-assisted local #340 pinned-consensus real-Metal recovery qualification.

Exact private regtest snapshot pin only. No production or validator bypass.
The peer supplies valid bodies but cannot supply the configured signer's votes.
"""
from pathlib import Path
import hashlib, json, os, shutil, sys, time
ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'toolchain-2026-10-31/source'
sys.path.insert(0, str(SOURCE/'test/functional'))
from feature_assumeutxo import AssumeutxoTest
from test_framework.messages import (CBlock, CBlockHeader, msg_headers, from_hex,
    NODE_NETWORK, NODE_WITNESS, NODE_MATMUL_CONSENSUS)
from test_framework.p2p import P2PDataStore
from test_framework.util import assert_equal

PUB = '0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798'
BASE = 1124
PREFIX = 100


class PrefixPeer(P2PDataStore):
    def peer_connect_send_version(self, services):
        super().peer_connect_send_version(services)
        self.on_connection_send_msg.nStartingHeight = PREFIX


class PinnedSnapshot(AssumeutxoTest):
    def set_test_params(self):
        self.num_nodes = 2
        self.setup_clean_chain = True
        self.rpc_timeout = 20
        common = ['-modelnet=0', '-connect=0', '-dbcache=16', '-assumevalid=0',
            '-checkblockindex=1', '-retainshieldedcommitmentindex=0',
            '-matmulvalidation=consensus', '-matmulrcexecution=strict-device',
            '-matmulrcconfirmcpu=0', '-matmulattestationserve=0']
        self.target_args = common + [f'-matmultrustedpubkey={PUB}',
            '-matmultrustedthreshold=1', '-matmulrcheaderfirst=0']
        self.extra_args = [common, self.target_args]
        self.report = {'variant':os.environ['PINNED_VARIANT'], 'status':'running',
            'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'binary_sha256':hashlib.sha256(Path(os.environ['BTXD']).read_bytes()).hexdigest(),
            'historical_rc_bodies':BASE-PREFIX,
            'scope':'macOS M4 strict-Metal toy regtest, pinned consensus without available quorum',
            'events':[], 'timeline':[]}

    def setup_network(self):
        self.add_nodes(2, self.extra_args)
        shutil.copytree(ROOT/'fixture-run/node0/regtest', self.nodes[0].chain_path, dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('debug.log', '.cookie', 'btxd.pid', 'pinned-window1124.dat'))
        self.start_nodes()

    def event(self, name, **values):
        self.report['phase'] = name
        self.report['events'].append({'phase':name, 'time':time.time(), **values})
        self.save()
        self.log.info(name)

    def save(self):
        (Path(self.options.tmpdir)/'observations.json').write_text(json.dumps(self.report, indent=2, default=str))

    def background(self):
        rows = [c['blocks'] for c in self.nodes[1].getchainstates()['chainstates'] if 'snapshot_blockhash' not in c]
        return rows[0] if rows else BASE

    def check_pin(self):
        s = self.nodes[1].getmatmultrustedstatus()
        assert_equal(s['configured'], True)
        assert_equal(s['trusted_signers'], 1)
        assert_equal(s['trusted_pq_signers'], 0)
        assert_equal(s['threshold'], 1)
        assert_equal(s['local_signer'], False)
        assert_equal(s['local_pq_signer'], False)
        assert_equal(s['stored_attestations'], 0)
        assert_equal(s['blocks_with_quorum'], 0)
        return s

    def runtime(self):
        v = self.nodes[1].getmininginfo()['backend_runtime']['rc_exact_replay']['last_validation']
        assert v['available'] and v['outcome'] == 'valid', v
        assert v['execution_policy'] == 'strict-device' and v['require_device'], v
        assert v['full_metal_pipeline'] and v['fully_accelerated'], v
        for k in ['cpu_gemm_calls', 'cpu_gemm_fallbacks', 'device_xof_fallbacks', 'host_xof_calls']:
            assert_equal(v[k], 0)
        return v

    def snapshot_done(self):
        return not self.nodes[1].getblockchaininfo()['snapshot_sync']['background_validation_in_progress']

    def run_test(self):
        try:
            self._run()
        except Exception as e:
            self.report['status'] = 'failed'
            self.report['exception'] = repr(e)
            self.event('failed', last_phase=self.report.get('phase'))
            raise

    def _run(self):
        source, target = self.nodes
        fixture = json.loads((ROOT/'fixture.json').read_text())['snapshot']
        assert_equal(source.getblockcount(), BASE)
        assert_equal(source.getbestblockhash(), fixture['base_hash'])
        self.event('prefix100-with-pins-and-no-signer', pin_status=self.check_pin())
        peer = PrefixPeer()
        for height in range(1, PREFIX+1):
            block = from_hex(CBlock(), source.getblock(source.getblockhash(height), 0))
            block.calc_sha256();peer.block_store[block.sha256] = block;peer.last_block_hash = block.sha256
        target.add_outbound_p2p_connection(peer, p2p_idx=0,
            services=NODE_NETWORK|NODE_WITNESS|NODE_MATMUL_CONSENSUS)
        peer.send_and_ping(msg_headers(headers=[CBlockHeader(b) for b in peer.block_store.values()]))
        self.wait_until(lambda: target.getblockcount() == PREFIX, timeout=45)
        target.disconnect_p2ps()
        clock = source.getblockheader(source.getbestblockhash())['time']
        source.setmocktime(clock);target.setmocktime(clock)
        self.sync_headers_via_p2p(source, target, BASE)
        loaded = target.loadtxoutset(str(ROOT/'fixture-run/node0/regtest/pinned-window1124.dat'))
        assert_equal(loaded['base_height'], BASE)
        assert_equal(self.background(), PREFIX)
        assert_equal(target.getblockchaininfo()['snapshot_sync']['background_validation_in_progress'], True)
        self.event('exact-snapshot-loaded', loaded=loaded, chainstates=target.getchainstates(),
            finality=target.getfinalityinfo(), pin_status=self.check_pin())

        start = time.monotonic()
        self.connect_nodes(1, 0, wait_for_connect=False)
        last_clock = clock;last_bg = -1;next_injection = 101
        last_progress = start
        foreground = []
        while time.monotonic()-start < 1200:
            elapsed = time.monotonic()-start
            now = clock+int(elapsed)
            if now != last_clock:
                target.setmocktime(now);source.setmocktime(now);last_clock = now
            bg = self.background()
            info = target.getblockchaininfo()
            peers = target.getpeerinfo()
            row = {'seconds':elapsed, 'background':bg, 'active':info['blocks'],
                'source_connections':len(peers), 'background_in_progress':info['snapshot_sync']['background_validation_in_progress']}
            self.report['timeline'].append(row)
            if bg != last_bg:
                last_progress = time.monotonic()
                self.log.info('background=%d active=%d seconds=%.2f', bg, info['blocks'], elapsed)
                self.save();last_bg = bg
            assert time.monotonic()-last_progress < 45, 'Historical replay made no progress for45s'
            if elapsed >= 0.5:
                assert_equal(len(peers), 1)  # No substitute peer or manual re-request.
            if (bg >= next_injection or (not foreground and elapsed >= 2)) and next_injection <= 900:
                before = time.monotonic()
                block = self.generate(source, 1, sync_fun=self.no_op)[-1]
                foreground.append({'hash':block, 'sent_at':time.monotonic()-start,
                    'background_at_injection':bg, 'generation_seconds':time.monotonic()-before})
                next_injection = {101:500, 500:900, 900:99999}[next_injection]
            for item in foreground:
                if 'seen_at' not in item and target.getbestblockhash() == item['hash']:
                    item['seen_at'] = time.monotonic()-start
                    item['latency'] = item['seen_at']-item['sent_at']
            if self.snapshot_done() and len(foreground) == 3 and all('seen_at' in x for x in foreground):
                break
            time.sleep(0.05)
        self.report['foreground'] = foreground
        self.event('catchup-observed', chainstates=target.getchainstates(),
            info=target.getblockchaininfo(), finality=target.getfinalityinfo(),
            peers=target.getpeerinfo(), pin_status=self.check_pin())
        assert self.snapshot_done(), 'Background validation did not complete within1200s'
        assert_equal(target.getbestblockhash(), source.getbestblockhash())
        assert_equal(len(foreground), 3)
        assert all('seen_at' in x for x in foreground), foreground
        assert any(x['background_at_injection'] < BASE for x in foreground)
        assert_equal(len(target.getpeerinfo()), 1)
        historical_status = []
        for height in range(PREFIX+1, BASE+1):
            block_hash = source.getblockhash(height)
            assert_equal(target.getblockhash(height), block_hash)
            assert_equal(target.getblock(block_hash, 0), source.getblock(block_hash, 0))
            status = target.getblockindexstatus(block_hash)
            assert status['nStatus'] & 256  # BLOCK_EXACT_REPLAY_VERIFIED, src/chain.h.
            assert not status['nStatus'] & 512  # No trusted-attestation replay flag.
            historical_status.append(status)
        self.report['historical_block_status'] = historical_status
        f = target.getfinalityinfo()['active_tip']
        assert_equal(f['authenticated_chainwork'], f['chainwork'])
        self.event('catchup-and-real-metal-pass', runtime=self.runtime(), elapsed=time.monotonic()-start)

        old_tip = target.getbestblockhash()
        self.restart_node(1, extra_args=self.target_args)
        assert_equal(target.getbestblockhash(), old_tip)
        assert self.snapshot_done()
        self.check_pin()
        for status in historical_status:
            persisted = target.getblockindexstatus(status['hash'])
            assert persisted['nStatus'] & 256
            assert not persisted['nStatus'] & 512
        self.connect_nodes(1, 0)
        self.event('restart-preserved-catchup', tip=old_tip, info=target.getblockchaininfo())
        for _ in range(3):
            self.generate(source, 1, sync_fun=lambda: self.sync_blocks([source, target]))
            assert self.snapshot_done()
            f = target.getfinalityinfo()['active_tip']
            assert_equal(f['authenticated_chainwork'], f['chainwork'])
        post_start = time.monotonic()
        while time.monotonic()-post_start < 30:
            assert_equal(target.getbestblockhash(), source.getbestblockhash())
            assert_equal(len(target.getpeerinfo()), 1)
            assert self.snapshot_done()
            self.check_pin()
            time.sleep(0.5)
        self.report['status'] = 'passed'
        self.event('complete', runtime=self.runtime(), pin_status=self.check_pin(),
            finality=target.getfinalityinfo(), info=target.getblockchaininfo(),
            source_tip=source.getbestblockhash(), peers=target.getpeerinfo())


if __name__ == '__main__':
    PinnedSnapshot(str(SOURCE/'test/functional/feature_assumeutxo.py')).main()
