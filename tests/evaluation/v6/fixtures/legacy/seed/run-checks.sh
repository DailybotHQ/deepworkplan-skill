#!/usr/bin/env bash
# csvreport developer checks (the fixture's public check contract).
#
# 1. compile everything;
# 2. the green suite must pass;
# 3. the K1 detector must STILL fail on the pristine fixture — when a repair
#    makes it pass, this script fails with "K1 no longer reproduces" until the
#    docs are reconciled (that refusal is the point: stale docs must not
#    survive silently);
# 4. the downstream caller script must keep working.
set -eu

cd "$(dirname "$0")"

echo "== compile =="
python3 -m compileall -q csvreport tests

echo "== green suite =="
python3 -m unittest discover -s tests -p 'test_green_*.py'

echo "== K1 detector (expected to fail: defect still present) =="
if python3 -m unittest discover -s tests -p 'test_k1_*.py' >/dev/null 2>&1; then
	echo "FAIL: K1 no longer reproduces - reconcile README/CHANGELOG before declaring the repair" >&2
	exit 1
else
	echo "K1 reproduces (expected on the pristine fixture)"
fi

echo "== downstream caller =="
printf 'name,score\nana,10\nbo,7\n' > /tmp/csvreport-caller-input.txt
./callers/report-gen.sh /tmp/csvreport-caller-input.txt /tmp/csvreport-caller-out.csv
grep -q '^ana,10$' /tmp/csvreport-caller-out.csv
grep -q '^bo,7$' /tmp/csvreport-caller-out.csv

echo "all checks passed"
