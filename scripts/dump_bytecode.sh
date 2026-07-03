#!/usr/bin/env bash
# Dump a deterministic, path-free manifest of every compiled contract's bytecode.
#
# Used by .github/workflows/verify-bytecode-parity.yml to compare the native CI
# build against the dev-container build. The manifest lists only contract names
# and their bytecode / deployedBytecode hex (no absolute paths), so two builds'
# manifests are directly diffable. The $HOME-dependence we care about lives
# *inside* the hashed bytecode, which is exactly what the diff compares.
#
# Usage: scripts/dump_bytecode.sh [output-file]   (default: bytecode-manifest.txt)
set -euo pipefail

out="${1:-bytecode-manifest.txt}"

shopt -s nullglob
files=(build/contracts/*.json)   # top-level only; skips build/contracts/dependencies/
if [ ${#files[@]} -eq 0 ]; then
  echo "error: no build/contracts/*.json found — run 'brownie compile' first" >&2
  exit 1
fi

for f in "${files[@]}"; do
  name=$(basename "$f" .json)
  printf '%s %s %s\n' "$name" "$(jq -r '.bytecode' "$f")" "$(jq -r '.deployedBytecode' "$f")"
done | sort > "$out"

echo "wrote $(wc -l < "$out" | tr -d ' ') contracts to $out"
