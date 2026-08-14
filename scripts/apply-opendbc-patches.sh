#!/usr/bin/env bash
# Apply local opendbc patches to the opendbc_repo submodule.
#
# Lets this branch track stock comma openpilot (and stock comma opendbc) while
# still carrying local opendbc fixes, without re-pointing the submodule at a
# fork and re-pinning a SHA on every branch.
#
# opendbc is installed editable from opendbc_repo, so patching the source here
# takes effect with no reinstall. The generated DBCs are gitignored and are
# regenerated below, since the patches touch generator sources.
#
# Runs from system/manager/build.py before scons, and is safe to run by hand.
#
# Fails loudly if a patch does not apply. That is deliberate: a silently
# skipped patch means driving stock behavior while believing the fix is in.

set -euo pipefail

BASEDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATCH_DIR="$BASEDIR/.github/patches/opendbc"
TARGET="$BASEDIR/opendbc_repo"

if [ ! -d "$TARGET/opendbc" ]; then
  echo "opendbc-patches: '$TARGET' is not a populated opendbc checkout" >&2
  echo "opendbc-patches: run 'git submodule update --init opendbc_repo' first" >&2
  exit 1
fi

shopt -s nullglob
patches=("$PATCH_DIR"/*.patch)
if [ ${#patches[@]} -eq 0 ]; then
  echo "opendbc-patches: no patches in $PATCH_DIR, nothing to do"
  exit 0
fi

applied_any=0
for p in "${patches[@]}"; do
  name="$(basename "$p")"

  # Already applied (rebuild without a clean submodule) -> not an error.
  if git -C "$TARGET" apply --reverse --check "$p" 2>/dev/null; then
    echo "opendbc-patches: already applied: $name"
    continue
  fi

  if ! git -C "$TARGET" apply --check "$p" 2>/dev/null; then
    echo "" >&2
    echo "opendbc-patches: ERROR: patch does not apply: $name" >&2
    echo "" >&2
    echo "Upstream opendbc has changed the code this patch touches." >&2
    echo "Refresh it against the pinned opendbc before building:" >&2
    echo "  cd opendbc_repo && git apply --3way $p" >&2
    echo "  # resolve, then re-export over $p" >&2
    echo "" >&2
    exit 1
  fi

  git -C "$TARGET" apply "$p"
  applied_any=1
  echo "opendbc-patches: applied: $name"
done

if [ "$applied_any" -eq 1 ]; then
  echo "opendbc-patches: regenerating DBCs..."
  PYTHONPATH="$TARGET" python3 "$TARGET/opendbc/dbc/generator/generator.py"
fi

echo "opendbc-patches: ok"
