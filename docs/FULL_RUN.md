# Full run on a Linux server

The MSR 2027 dataset run: 196,938 repositories from the SEART frame
(`data/seart/frame-2026-10-03.csv`, built by `scripts/frame_from_seart.py`),
mined with the frozen catalogue. The 500-repository dry run on 2026-10-03 (BENCHMARKS.md)
took about 1 s of wall time and 3.9 CPU-seconds per repository at 16 workers,
with 2.6% of repositories agentic.

## 1. Get the project onto the server

Clone the repository, which pins the exact code the dataset comes from by
commit hash (recorded in `RUN.txt`):

```bash
git clone https://github.com/unlv-evol/cai-miner.git ~/cai-miner
```

or copy an uncommitted working tree from the laptop:

```bash
rsync -av --exclude out/ --exclude .venv/ --exclude '__pycache__/' \
      --exclude 'manuscripts/msr/main.*' --exclude '.pytest_cache/' \
      ~/path/to/cai-miner/ server:cai-miner/
```

Required on the server: **bash 4+, git 2.30+ (2.45+ preferred), GNU coreutils
and [uv](https://docs.astral.sh/uv/)** (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
uv installs the pinned Python itself.

```bash
cd ~/cai-miner
uv sync --locked --all-groups   # .venv with cai-miner (editable) and the locked tools
. .venv/bin/activate            # mine.sh and preflight.sh call `python3 -m cai_miner`
uv run pytest -q                # expect all to pass
```

## 2. Preflight

Put the clones on a real disk, not `/tmp` if that is a tmpfs:

```bash
mkdir -p /data/cai-miner-work
./scripts/preflight.sh out/full /data/cai-miner-work
```

Every line must be PASS (or an understood WARN) and the last line
`preflight: ready`. It checks the tools, that `cai_miner` imports from this checkout,
the repository list and catalogue, free disk, the work directory's filesystem,
that GitHub is reachable, that git honours `GIT_NO_LAZY_FETCH`, and a
three-repository smoke run (`ok` / `excluded` / `clone-failed`).

## 3. Launch

Do not edit anything under `src/cai_miner/catalogues/` from here on: the catalogue is frozen, and
the validation sample only holds for the patterns that produced the data.
`RUN.txt` records its checksums.

```bash
tmux new -s cai-miner        # survives a dropped SSH session; reattach: tmux attach -t cai-miner
. .venv/bin/activate
WORK=/data/cai-miner-work ./scripts/mine.sh data/seart/repos-2026-10-03.txt out/full 32 \
    2>&1 | tee -a out/full.log
```

**Workers.** Start at 2 x cores (32 on a 16-core machine), capped around 64.
Extraction is CPU-bound, cloning is network-bound, and how much concurrency
github.com tolerates before throttling is unmeasured. Throttling shows up as a
burst of `clone-failed` in `out/full/failures.tsv`. If that happens, stop with
Ctrl-C, lower the count, and relaunch; the run resumes.

## 4. Monitor

```bash
find out/full/parts -name repositories.csv -exec cat {} + | grep -vc '^repository,'   # repositories done
cut -f2 out/full/failures.tsv | sort | uniq -c                     # failures by kind
tail out/full/errors.log                                           # cai-miner errors
du -sh /data/cai-miner-work out/full                                     # disk
```

The work directory should stay at a few hundred MB: each clone is deleted
after extraction. If it grows steadily, clones are being left behind.

## 5. Interruptions

Ctrl-C, `kill` or a reboot leave no clones behind and lose nothing finished.
Re-run the **same command** to resume: repositories already recorded under
`out/full/parts/` are skipped, and failures are retried.

## 6. Retry pass for timeouts

Giant repositories with oversized workflow files (like `clickhouse/clickhouse`)
can exceed the 900-second budget in the backfill fetch. A 1 MB blob cap leaves
nothing to backfill:

```bash
grep -P '\textract-failed$|\tclone-failed$' out/full/failures.tsv | cut -f1 | sort -u > out/retry.txt
CAP=1m TIMEOUT=3600 WORK=/data/cai-miner-work ./scripts/mine.sh out/retry.txt out/full 8
```

Same output directory, so the results merge in. Whatever still fails keeps a
`repositories.csv` row with its failure as status: it stays in the denominator.
Disabled repositories (13 in the frame) will always be `clone-failed`.

## 7. Recall subset (validation/PLAN.md, C5)

1,000 random repositories, re-mined keeping every workflow revision. This can
run at the same time as the full run, in a second tmux window:

```bash
python3 - <<'EOF'
import random
names = [l.strip() for l in open("data/seart/repos-2026-10-03.txt") if l.strip() and not l.startswith("#")]
random.seed(20261017)
open("out/recall.txt", "w").write("\n".join(random.sample(names, 1000)) + "\n")
EOF
MINER_ARGS=--keep-all WORK=/data/cai-miner-work ./scripts/mine.sh out/recall.txt out/recall 16
```

## 8. Bring it back

```bash
# from the laptop
rsync -av server:cai-miner/out/full/ ~/path/to/cai-miner/out/full/ \
      --exclude parts/
rsync -av server:cai-miner/out/recall/ ~/path/to/cai-miner/out/recall/ --exclude parts/
```

Keep `out/full/parts/` on the server until the run is final; it is what resume
reads. Then draw the validation samples (validation/PLAN.md, "Running it").

Before release, settle the open decision on author and committer emails in
`revisions.csv` (publish them, or hash them).
