#!/usr/bin/env python3
"""ci_simulate.py
A local stand-in for a CI pipeline stage, per this lab's final step:
"a continuous integration (CI) simulation, where you confirm that your
test suite maintains a coverage target of 88%."

Run it exactly like a CI job would:

    python ci_simulate.py

It runs the full pytest suite with coverage, enforces the 88% gate
(via pytest.ini's --cov-fail-under=88, re-asserted here too so this
script's own exit code is meaningful even if pytest.ini is ever
changed), and prints a clear pass/fail summary. Exit code 0 = CI green,
non-zero = CI red -- the same signal a real GitHub Actions job would
use to block a merge.
"""
import subprocess
import sys

COVERAGE_THRESHOLD = 88


def main() -> int:
    print("=" * 70)
    print("CI SIMULATION -- Secure/robust multi-agent test suite")
    print("=" * 70)

    print("\n[1/2] Running pytest with coverage...\n")
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "--cov=agents",
            "--cov-report=term-missing",
            f"--cov-fail-under={COVERAGE_THRESHOLD}",
        ],
    )

    print("\n[2/2] Evaluating CI gate...")
    if result.returncode == 0:
        print(f"\n✅ CI PASSED -- all tests passed and coverage is >= {COVERAGE_THRESHOLD}%.")
        print("   Safe to merge.")
    else:
        print(f"\n❌ CI FAILED -- either a test failed or coverage dropped below {COVERAGE_THRESHOLD}%.")
        print("   Do not merge until this is green.")

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
