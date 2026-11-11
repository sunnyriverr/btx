"""Archive argument matrix against a disposable, unfunded regtest wallet."""
import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import traceback

EXPECTED = {
    'btxd': 'ffd6c2dc95df0111a8152b5d5f82244190cad2323981376ffed7c21a1cfd9fc6',
    'btx-cli': '921c54e5f0c92745b42bd63711bf404f9e50b7be3d39e2d82916d0439b9633c8',
}
SOURCE = 'dac9aee53520bd49ed320ec7a49b9072fc7d88d9'
WALLET_PASS, ARCHIVE_PASS, WRONG_PASS = 'FixtureWallet-103', 'FixtureArchive-207', 'FixtureWrong-901'
EQUALS_PASS = 'FixtureArchive=equals=208'
LABEL, WALLET = 'unfunded-fixture-label', 'source'
WFLAG, AFLAG = '-stdinwalletpassphrase', '-stdinbundlepassphrase'
BACKUP, RESTORE = 'backupwalletbundlearchive', 'restorewalletbundlearchive'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def scrub(text):
    for value in (WALLET_PASS, ARCHIVE_PASS, WRONG_PASS, EQUALS_PASS):
        text = text.replace(value, '<synthetic-passphrase>')
    return text


class Fixture:
    def __init__(self, binaries, records, runtime, expected_cli):
        self.binaries, self.records, self.runtime = binaries, records, runtime
        self.daemon = None
        self.expected = dict(EXPECTED, **{"btx-cli": expected_cli})
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        self.env = dict(os.environ, HOME=str(runtime), XDG_DATA_HOME=str(runtime / 'xdg'))
        self.args = [str(binaries / 'btx-cli'), '-regtest', f'-datadir={runtime}',
                     f'-rpcport={self.port}', '-rpcconnect=127.0.0.1', '-rpcclienttimeout=12']
        self.result = {'source': SOURCE, 'cases': {}, 'status': 'in_progress'}

    def save(self):
        (self.records / 'result.json').write_text(scrub(json.dumps(self.result, indent=2) + '\n'))

    def cli(self, method, args=(), flags=(), stdin=None, wallet=None):
        argv = [*self.args, *flags]
        if wallet:
            argv.append('-rpcwallet=' + wallet)
        argv.extend([method, *map(str, args)])
        return subprocess.run(argv, input=stdin or '', text=True, capture_output=True, env=self.env, timeout=25)

    def rpc(self, method, *args, wallet=None, flags=(), stdin=None):
        p = self.cli(method, args, flags, stdin, wallet)
        assert p.returncode == 0, f'{method}: {scrub(p.stderr)}'
        if not p.stdout.strip():
            return None
        try:
            return json.loads(p.stdout)
        except json.JSONDecodeError:
            return p.stdout.strip()

    def start(self):
        observed = {name: digest(self.binaries / name) for name in EXPECTED}
        assert observed == self.expected, observed
        self.result.update(binary_sha256=observed, fixture_sha256=digest(Path(__file__)))
        (self.runtime / 'wallets').mkdir(mode=0o700)
        flags = [
            f'-datadir={self.runtime}', '-regtest=1', '-server=1', '-disablewallet=0',
            f'-walletdir={self.runtime / "wallets"}', '-keypool=2', '-modelnet=0',
            '-networkactive=0', '-listen=0', '-connect=0', '-dnsseed=0', '-discover=0',
            '-upnp=0', '-natpmp=0', '-walletbroadcast=0', '-persistmempool=0',
            '-nosettings', '-nodebuglogfile', '-printtoconsole=1',
            f'-rpcport={self.port}', '-rpcbind=127.0.0.1', '-rpcallowip=127.0.0.1',
        ]
        with (self.runtime / 'daemon.log').open('wb') as log:
            self.daemon = subprocess.Popen([str(self.binaries / 'btxd'), *flags], env=self.env,
                                           stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        end = time.monotonic() + 35
        while time.monotonic() < end:
            assert self.daemon.poll() is None, 'daemon exited during startup'
            if (self.runtime / 'regtest/.cookie').is_file():
                p = self.cli('getblockchaininfo')
                if p.returncode == 0:
                    assert json.loads(p.stdout)['chain'] == 'regtest'
                    break
            time.sleep(.15)
        else:
            raise RuntimeError('daemon startup timed out')
        assert self.rpc('getblockcount') == 0 and self.rpc('getconnectioncount') == 0
        assert self.rpc('getnetworkinfo')['networkactive'] is False
        assert self.rpc('listwallets') == []
        self.result['isolation'] = {'chain': 'regtest', 'height': 0, 'connections': 0, 'wallets_at_start': []}

    def help(self):
        cli = subprocess.run([str(self.binaries / 'btx-cli'), '-help'], capture_output=True,
                             text=True, env=self.env, timeout=15, check=True).stdout
        backup = self.rpc('help', BACKUP)
        restore = self.rpc('help', RESTORE)
        assert all(x in cli for x in ('-named', WFLAG, AFLAG))
        assert all(x in backup for x in ('destination_archive', 'archive_passphrase', 'wallet_passphrase'))
        assert all(x in restore for x in ('wallet_name', 'archive_file', 'archive_passphrase'))
        for name, body in [('cli-help.txt', cli), ('backup-help.txt', backup), ('restore-help.txt', restore)]:
            (self.records / name).write_text(body + '\n')

    def wallet_state(self, name, address):
        assert self.rpc('getwalletinfo', wallet=name)['unlocked_until'] == 0
        assert Decimal(str(self.rpc('getbalance', wallet=name))) == 0
        assert self.rpc('getaddressinfo', address, wallet=name)['ismine'] is True
        assert self.rpc('getaddressesbylabel', LABEL, wallet=name)[address]['purpose'] == 'receive'
        return {'locked': True, 'balance': '0', 'ownership_and_label_match': True}

    def attempt(self, name, method, args, flags, stdin, wallet=None):
        p = self.cli(method, args, flags, stdin, wallet)
        row = {'returncode': p.returncode, 'stderr': scrub(p.stderr.strip())}
        self.result['cases'][name] = row
        print(name, p.returncode, row['stderr'], flush=True)
        self.save()
        return (json.loads(p.stdout) if p.returncode == 0 else None), row

    def backup(self, name, args, flags, stdin, address):
        archive = self.runtime / (name + '.btx')
        values = [arg.replace('ARCHIVE_PATH', str(archive)) for arg in args]
        self.wallet_state(WALLET, address)
        result, row = self.attempt(name, BACKUP, values, flags, stdin, WALLET)
        row['archive_created'] = archive.is_file()
        row['source_after'] = self.wallet_state(WALLET, address)
        if result is not None:
            assert row['archive_created'] and archive.stat().st_size > 0
            assert Path(result['archive_file']) == archive and result['wallet_encrypted']
            assert result['unlocked_by_rpc'] and not result['wallet_passphrase_included']
            assert result['integrity']['integrity_ok'] is True
            row.update(sha256=digest(archive), bytes=archive.stat().st_size, integrity_ok=True)
        else:
            assert not archive.exists(), name
        self.save()
        return archive if result is not None else None

    def restore(self, name, archive, mode, address, passphrase=ARCHIVE_PASS):
        wallet = name.replace('_', '-')
        args = [wallet, str(archive)]
        flags, stdin = [], None
        before = digest(archive)
        assert wallet not in self.rpc('listwallets')
        if mode == 'mixed_stdin':
            flags.append('-named')
        if mode.startswith('named'):
            args = [f'wallet_name={wallet}', f'archive_file={archive}', 'load_on_startup=false']
            flags.append('-named')
        if mode.endswith('stdin'):
            flags.append(AFLAG)
            stdin = passphrase + '\n'
            if mode == 'mixed_stdin':
                args.append('load_on_startup=false')
        elif mode.startswith('named'):
            args.append('archive_passphrase=' + passphrase)
        else:
            args.append(passphrase)
        result, row = self.attempt(name, RESTORE, args, flags, stdin)
        assert digest(archive) == before
        row['archive_unchanged'] = True
        if result is not None:
            assert result['name'] == wallet and result['bundled_integrity']['integrity_ok']
            assert result['bundled_manifest']['wallet_encrypted'] is True
            row['initial'] = self.wallet_state(wallet, address)
            self.rpc('walletpassphrase', '20', wallet=wallet, flags=[WFLAG], stdin=WALLET_PASS + '\n')
            assert self.rpc('getwalletinfo', wallet=wallet)['unlocked_until'] > 0
            self.rpc('walletlock', wallet=wallet)
            self.rpc('unloadwallet', wallet, 'false')
            self.rpc('loadwallet', wallet, 'false')
            row['after_reload'] = self.wallet_state(wallet, address)
            self.rpc('unloadwallet', wallet, 'false')
        else:
            assert wallet not in self.rpc('listwallets')
            assert not (self.runtime / 'wallets' / wallet).exists(), wallet
            row['no_partial_wallet'] = True
        self.save()
        return result is not None

    def test(self):
        self.help()
        self.rpc('createwallet', f'wallet_name={WALLET}', 'load_on_startup=false', flags=['-named'])
        address = self.rpc('getnewaddress', LABEL, wallet=WALLET)
        self.rpc('encryptwallet', WALLET_PASS, wallet=WALLET)
        self.wallet_state(WALLET, address)
        dst = 'destination_archive=ARCHIVE_PATH'
        ap = 'archive_passphrase=' + ARCHIVE_PASS
        wp = 'wallet_passphrase=' + WALLET_PASS
        view = 'include_viewing_keys=false'
        cases = [
            ('backup_positional_stdin', ['ARCHIVE_PATH', 'false'], [WFLAG, AFLAG], WALLET_PASS + '\n' + ARCHIVE_PASS + '\n'),
            ('backup_named_explicit', [dst, ap, wp, view], ['-named'], None),
            ('backup_named_archive_stdin', [dst, wp, view], ['-named', AFLAG], ARCHIVE_PASS + '\n'),
            ('backup_named_wallet_stdin', [dst, ap, view], ['-named', WFLAG], WALLET_PASS + '\n'),
            ('backup_named_both_stdin', [dst, view], ['-named', WFLAG, AFLAG], WALLET_PASS + '\n' + ARCHIVE_PASS + '\n'),
            ('backup_mixed_stdin', ['ARCHIVE_PATH', view], ['-named', WFLAG, AFLAG],
             WALLET_PASS + '\n' + ARCHIVE_PASS + '\n'),
            ('backup_named_equals_stdin', [dst, wp, view], ['-named', AFLAG], EQUALS_PASS + '\n'),
        ]
        archives = {name: self.backup(name, args, flags, stdin, address) for name, args, flags, stdin in cases}
        positional = archives['backup_positional_stdin']
        explicit = archives['backup_named_explicit']
        assert positional and explicit and archives['backup_mixed_stdin'], 'backup controls failed'
        duplicate_cases = [
            ('backup_duplicate_archive_passphrase', [dst, ap, wp, view], ['-named', AFLAG], ARCHIVE_PASS + '\n'),
            ('backup_duplicate_wallet_passphrase', [dst, ap, view], ['-named', '-stdin', WFLAG],
             WALLET_PASS + '\n' + wp + '\n'),
        ]
        for name, args, flags, stdin in duplicate_cases:
            assert self.backup(name, args, flags, stdin, address) is None
        p = self.cli(RESTORE, ['unintended', 'wallet_name=duplicate', f'archive_file={positional}', ap],
                     ['-named'])
        assert p.returncode == 8 and 'Parameter wallet_name specified twice' in p.stderr
        self.result['cases']['restore_genuine_mixed_duplicate'] = {
            'returncode': p.returncode, 'stderr': scrub(p.stderr.strip())}
        assert not (self.runtime / 'wallets' / 'unintended').exists()
        assert not (self.runtime / 'wallets' / 'duplicate').exists()
        assert not self.restore('restore_wrong_archive_pass', positional, 'positional_stdin', address, WRONG_PASS)
        assert 'error code: -14' in self.result['cases']['restore_wrong_archive_pass']['stderr']
        assert self.restore('restore_positional_stdin', positional, 'positional_stdin', address)
        assert self.restore('restore_named_explicit', explicit, 'named_explicit', address)
        assert self.restore('restore_same_archive_named_control', positional, 'named_explicit', address)
        self.restore('restore_named_stdin', positional, 'named_stdin', address)
        for name, path in archives.items():
            if not path or name in ('backup_positional_stdin', 'backup_named_explicit'):
                continue
            mode = 'mixed_stdin' if name == 'backup_mixed_stdin' else 'named_stdin'
            passphrase = EQUALS_PASS if name == 'backup_named_equals_stdin' else ARCHIVE_PASS
            assert self.restore('restore_' + name, path, mode, address, passphrase)
        assert self.rpc('listwallets') == [WALLET] and self.rpc('getblockcount') == 0
        self.result['status'] = 'observed_controls_passed'

    def close(self):
        if self.daemon is None:
            return
        try:
            stop = self.cli('stop') if self.daemon.poll() is None else None
            self.daemon.wait(timeout=15)
            self.result['clean_shutdown'] = stop is not None and stop.returncode == 0 and self.daemon.returncode == 0
        finally:
            if self.daemon.poll() is None:
                self.daemon.kill()
                self.daemon.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binaries', type=Path, required=True)
    parser.add_argument('--expected-cli', default=EXPECTED['btx-cli'])
    parser.add_argument('--records', type=Path, required=True)
    args = parser.parse_args()
    args.records.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='btx-cli-archive-') as directory:
        fixture = Fixture(args.binaries.resolve(), args.records.resolve(), Path(directory), args.expected_cli)
        try:
            fixture.start()
            fixture.test()
        except Exception:
            fixture.result['status'] = 'inconclusive'
            fixture.result['failure'] = scrub(traceback.format_exc())
            print(fixture.result['failure'], flush=True)
        finally:
            try:
                fixture.close()
            except Exception:
                fixture.result['cleanup_failure'] = scrub(traceback.format_exc())
            if not fixture.result.get('clean_shutdown'):
                fixture.result['status'] = 'inconclusive'
                log = fixture.runtime / 'daemon.log'
                if log.exists():
                    (fixture.records / 'daemon-tail.txt').write_text(scrub(log.read_text(errors='replace')[-9000:]))
            fixture.save()
    fixture.result['runtime_removed'] = not fixture.runtime.exists()
    fixture.save()
    return 0 if fixture.result['status'] == 'observed_controls_passed' and fixture.result['runtime_removed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
