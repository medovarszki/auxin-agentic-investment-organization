"""Runs inside an agent container: blocked hosts must fail, allowed hosts must answer."""
import sys
import urllib.error
import urllib.request

CASES = {"https://example.com": False, "https://api.anthropic.com": True}


def reachable(url: str) -> bool:
    try:
        urllib.request.urlopen(url, timeout=10)
        return True
    except urllib.error.HTTPError:
        return True  # an HTTP answer (e.g. 404) means the proxy let us through
    except Exception:
        return False


failed = False
for url, expected in CASES.items():
    got = reachable(url)
    ok = got == expected
    failed |= not ok
    print(f"{'OK  ' if ok else 'FAIL'} {url}: {'reachable' if got else 'blocked'} (expected {'reachable' if expected else 'blocked'})")
sys.exit(1 if failed else 0)
