"""#39: read-only local page response/HTML size checks.

Usage (server must be running):
    python scripts/measure_pages.py --base http://127.0.0.1:8000

Budgets are initial warning thresholds, not guarantees: 2 seconds and
500 KiB of HTML per page. Network/Canvas delays may affect timing.
Only requests GET pages; never reads credentials or writes database records.
"""
import argparse
import time
import urllib.error
import urllib.request

PAGES = ("/", "/afternoon", "/api/health")
DEFAULT_MS = 2000
DEFAULT_KIB = 500


def measure(base, path, timeout):
    start = time.perf_counter()
    request = urllib.request.Request(base.rstrip("/") + path,
                                     headers={"Accept": "text/html"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        status = response.status
    return status, (time.perf_counter() - start) * 1000, len(body)


def main():
    parser = argparse.ArgumentParser(description="Measure local SyncCanvas page budgets")
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--max-ms", type=float, default=DEFAULT_MS)
    parser.add_argument("--max-kib", type=float, default=DEFAULT_KIB)
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()
    failures = 0
    for path in PAGES:
        try:
            status, ms, size = measure(args.base, path, args.timeout)
            ok = status == 200 and ms <= args.max_ms and size <= args.max_kib * 1024
            print(f"{'PASS' if ok else 'WARN'} {path}: HTTP {status}, {ms:.0f} ms, {size/1024:.1f} KiB")
            failures += not ok
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"FAIL {path}: {exc}")
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
