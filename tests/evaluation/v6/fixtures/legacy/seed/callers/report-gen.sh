#!/usr/bin/env bash
# Downstream caller (simulated user automation). Its command line is a
# compatibility contract: if csvreport's CLI changes shape, this breaks, and
# the maintenance task that changed it is wrong.
set -eu

IN="${1:?usage: report-gen.sh INPUT.csv OUTPUT.csv}"
OUT="${2:?usage: report-gen.sh INPUT.csv OUTPUT.csv}"

exec python3 -m csvreport --columns name,score --in "$IN" --out "$OUT"
