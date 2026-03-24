"""
Smoke tests for HTTP admin API + /health. Run with the server up:
  cd server && python app.py

Then:
  python scripts/e2e_test.py
"""
from __future__ import annotations

import os
import sys

import requests

BASE_URL = os.getenv("MODERATOR_API_BASE", "http://127.0.0.1:5000").rstrip("/")


def e2e_test() -> bool:
    print("\n" + "=" * 60)
    print("END-TO-END API SMOKE TEST")
    print("=" * 60)

    results: list[tuple[str, bool, object]] = []

    try:
        r = requests.get(f"{BASE_URL}/health", timeout=15)
        j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        db = j.get("supabase_connected")
        ok = r.status_code == 200 and j.get("status") == "healthy"
        results.append(("Backend /health", ok, j))
    except Exception as e:
        results.append(("Backend /health", False, str(e)))

    room_id = None
    try:
        r = requests.post(
            f"{BASE_URL}/admin/rooms",
            json={"mode": "active", "max_participants": 3},
            timeout=30,
        )
        data = r.json() if r.content else {}
        room_id = (data.get("room") or {}).get("id")
        ok = r.status_code == 200 and bool(room_id)
        results.append(("POST /admin/rooms", ok, room_id or data))
    except Exception as e:
        results.append(("POST /admin/rooms", False, str(e)))

    try:
        r = requests.get(f"{BASE_URL}/admin/rooms", timeout=15)
        data = r.json() if r.content else {}
        ok = r.status_code == 200 and isinstance(data.get("rooms"), list)
        results.append(("GET /admin/rooms", ok, len(data.get("rooms", []))))
    except Exception as e:
        results.append(("GET /admin/rooms", False, str(e)))

    try:
        r = requests.get(f"{BASE_URL}/admin/stats", timeout=15)
        data = r.json() if r.content else {}
        ok = r.status_code == 200 and "rooms" in data
        results.append(("GET /admin/stats", ok, data.get("rooms", {})))
    except Exception as e:
        results.append(("GET /admin/stats", False, str(e)))

    print("\nRESULTS")
    print("-" * 40)
    passed = 0
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}: {detail}")
        if ok:
            passed += 1
    print("-" * 40)
    print(f"{passed}/{len(results)} passed")

    all_ok = passed == len(results)
    print("\nAll passed." if all_ok else "\nSome checks failed (is the server running with valid .env?).")
    return all_ok


if __name__ == "__main__":
    ok = e2e_test()
    sys.exit(0 if ok else 1)
