"""Simple latency probe for key HTTP endpoints."""
from __future__ import annotations

import os
import sys
import time

import requests

BASE = os.getenv("MODERATOR_API_BASE", "http://127.0.0.1:5000").rstrip("/")


def main() -> None:
    endpoints = [
        ("/health?lite=1", "Health (lite, no DB ping)"),
        ("/health", "Health (with DB ping)"),
        ("/admin/rooms", "List rooms"),
        ("/admin/stats", "Stats"),
    ]
    print("\nPERFORMANCE (ms)")
    print("=" * 44)
    for path, label in endpoints:
        url = f"{BASE}{path}"
        t0 = time.perf_counter()
        try:
            r = requests.get(url, timeout=30)
            ms = (time.perf_counter() - t0) * 1000
            ok = "OK" if r.status_code == 200 else f"HTTP {r.status_code}"
            print(f"{ok:12} {label}: {ms:,.0f} ms")
        except Exception as e:
            ms = (time.perf_counter() - t0) * 1000
            print(f"{'ERR':12} {label}: {ms:,.0f} ms — {e}")
    print("=" * 44)


if __name__ == "__main__":
    main()
    sys.exit(0)
