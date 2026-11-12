from pathlib import Path
import subprocess
import tempfile

directory = Path(__file__).resolve().parent
for variant in ('baseline', 'candidate'):
    for case, failure, evidence in (
        ('hydration', 'old cursor did not survive',
         'fault_retry start=4194304 bytes_read=8388608'),
        ('bundle', 'old bundle did not survive',
         'retry_bytes=100 exact_bytes=1 imported_sequence=2'),
    ):
        name = f'{case}-{variant}'
        with tempfile.TemporaryDirectory(prefix=f'btx-{case}-') as scratch:
            result = subprocess.run([directory / name, scratch],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, timeout=30)
        (directory / f'{name}.log').write_text(result.stdout)
        print(f'{name} exit={result.returncode}\n{result.stdout}', flush=True)
        if variant == 'baseline':
            assert result.returncode == 1 and failure in result.stdout, name
            assert 'after_bytes=8 preserved=0 reopened=0' in result.stdout, name
        else:
            assert result.returncode == 0 and evidence in result.stdout, name
            assert 'preserved=1 reopened=1' in result.stdout, name
