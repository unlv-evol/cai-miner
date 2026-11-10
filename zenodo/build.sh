#!/usr/bin/env bash
# Stage the GHAgentCI Zenodo upload in out/zenodo/.
#
#   zenodo/build.sh            # after scripts/build_release.py has written out/release/
#
# The record holds the five release files, the sampling frame, a dataset README
# and a replication package. Everything is staged as a flat directory, so the
# upload is "every file in out/zenodo/".
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RELEASE="$ROOT/out/release"
STAGE="$ROOT/out/zenodo"
FRAME="$ROOT/data/seart/frame-2026-10-03.csv"

for f in repositories revisions steps ghaw_manifests; do
    [ -f "$RELEASE/$f.csv.gz" ] || { echo "missing $RELEASE/$f.csv.gz; run scripts/build_release.py" >&2; exit 1; }
done
[ -f "$RELEASE/content.tar.gz" ] || { echo "missing $RELEASE/content.tar.gz" >&2; exit 1; }

rm -rf "$STAGE"
mkdir -p "$STAGE"

# 1. The dataset, as built by scripts/build_release.py. Hard links: the content
#    archive is 800 MB and does not need a second copy.
for f in repositories.csv.gz revisions.csv.gz steps.csv.gz ghaw_manifests.csv.gz content.tar.gz; do
    ln "$RELEASE/$f" "$STAGE/$f" 2>/dev/null || cp "$RELEASE/$f" "$STAGE/$f"
done

# 2. The sampling frame. -n keeps gzip from storing a name and time stamp, so a
#    rebuild is byte-identical.
gzip -9 -n -c "$FRAME" > "$STAGE/frame-2026-10-03.csv.gz"

# 3. The dataset README.
cp "$ROOT/docs/DATASET.md" "$STAGE/README.md"

# 4. The replication package: the tool at the version that mined the data, the
#    run logs, the scripts behind the paper, and the validation material.
#    Excluded on purpose: the raw mining output (it carries unhashed author
#    emails), the email-hashing salt, and the coders' original workbooks (their
#    labels are in validation/*_sheet_*.csv).
WORK="$(mktemp -d "${TMPDIR:-/tmp}/ghagentci-replication.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
PKG="$WORK/replication"
mkdir -p "$PKG/run-logs"

(cd "$ROOT" && tar cf - \
    --exclude '__pycache__' --exclude '.DS_Store' --exclude '~$*' \
    README.md LICENSE CITATION.cff CHANGELOG.md CONTRIBUTING.md BENCHMARKS.md \
    pyproject.toml uv.lock .python-version \
    src tests scripts docs zenodo/build.sh \
    data/seart \
    validation/PLAN.md validation/*.csv \
    validation/labeling/GHAgentCI-coding-guide.pdf validation/labeling/ORGANISER-README.md \
    validation/labeling_src/guide.tex \
    explorer/app.html explorer/README.md \
  ) | (cd "$PKG" && tar xf -)

cp "$ROOT/out/full/RUN.txt" "$PKG/run-logs/full-RUN.txt"
cp "$ROOT/out/recall/RUN.txt" "$PKG/run-logs/recall-RUN.txt"
for f in full.log full-retry-clone.log full-retry-extract.log recall.log \
         retry.txt retry2.txt retry-clone.txt retry-extract.txt merge-only.txt recall.txt; do
    [ -f "$ROOT/out/$f" ] && cp "$ROOT/out/$f" "$PKG/run-logs/$f"
done
cp "$ROOT/out/full/failures.tsv" "$PKG/run-logs/full-failures.tsv"
cp "$ROOT/zenodo/REPLICATION.md" "$PKG/REPLICATION.md"

# Sorted, owner-free and dated to the release, so a rebuild is byte-identical.
COPYFILE_DISABLE=1 tar -C "$WORK" -cf - --uid 0 --gid 0 --uname '' --gname '' \
    $( [ "$(uname)" = Darwin ] || echo --sort=name --mtime=2026-11-09 ) replication \
  | gzip -9 -n > "$STAGE/replication.tar.gz"

# 5. Checksums for everything in the record.
(cd "$STAGE" && shasum -a 256 -- *.gz README.md > SHA256SUMS)

echo "staged in $STAGE:" >&2
ls -l "$STAGE" >&2
