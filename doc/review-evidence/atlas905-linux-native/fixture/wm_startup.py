"""Pure classification of the captured, bounded wmctrl startup condition."""
import math


def transient_missing_client_list(returncode, stdout, stderr, elapsed_seconds):
    """Admit only a known missing-list diagnostic before ten seconds, no rows."""
    if (returncode != 1 or stdout.strip() or not math.isfinite(elapsed_seconds)
            or not 0 <= elapsed_seconds < 10):
        return False
    lines = tuple(line.strip() for line in stderr.strip().splitlines())
    first = 'Cannot get client list properties.'
    return lines in {
        (first,),
        (first, '(_NET_CLIENT_LIST or _WIN_CLIENT_LIST)'),
    }
