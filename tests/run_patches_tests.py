#!/usr/bin/env python3
"""
Master Test Runner — Patch Validation Suite
Runs all 5 test suites (A-E) and reports grand total.
"""
import subprocess
import sys
import time
import re

SUITES = [
    ("A", "Error Handling", "test_patches_errors.py"),
    ("B", "Response Format", "test_patches_response.py"),
    ("C", "Retry Logic", "test_patches_retry.py"),
    ("D", "Crypto Safety", "test_patches_crypto_safety.py"),
    ("E", "End-to-End", "test_patches_e2e.py"),
]

total_pass = 0
total_fail = 0
start = time.time()

print("=" * 60)
print("🧪 PATCH VALIDATION — Full Test Run")
print("=" * 60)

for label, name, filename in SUITES:
    result = subprocess.run(
        [sys.executable, filename],
        capture_output=True, text=True,
        cwd=__import__('os').path.dirname(__import__('os').path.abspath(__file__))
    )

    output = result.stdout
    print(output)

    if result.stderr:
        # Only show stderr if it's not just warnings
        filtered = [ln for ln in result.stderr.splitlines() if "Warning" not in ln]
        if filtered:
            print(f"  ⚠️  STDERR: {''.join(filtered[:3])}")

    # Parse results line: "Results: X/Y passed"
    match = re.search(r'Results:\s*(\d+)/(\d+)\s*passed', output)
    if match:
        p, t = int(match.group(1)), int(match.group(2))
        total_pass += p
        total_fail += (t - p)

elapsed = time.time() - start

print("\n" + "=" * 60)
print(f"GRAND TOTAL: {total_pass} passed, {total_fail} failed ({elapsed:.1f}s)")
print(f"STATUS: {'🟢 ALL PASSED' if total_fail == 0 else f'🔴 {total_fail} FAILURES'}")
print("=" * 60)

sys.exit(0 if total_fail == 0 else 1)
