# GHAgentCI replication package

This archive rebuilds GHAgentCI from scratch and regenerates the paper's
numbers, figures and tables. It is a snapshot of the
[cai-miner](https://github.com/unlv-evol/cai-miner) repository at the version
that produced the dataset, plus the logs of the mining run.

| path | contents |
| ---- | -------- |
| `src/cai_miner/` | the mining tool, cai-miner 0.1.0 (developed as `awe`) |
| `src/cai_miner/catalogues/` | the frozen detector catalogue the dataset was mined with |
| `data/seart/` | the SEART export (`results-2026-10-03.csv.gz`), the sampling frame derived from it, and the list of repositories mined |
| `scripts/` | sampling frame, mining, release, validation and paper scripts |
| `run-logs/` | `RUN.txt` of the main and recall runs (environment, catalogue checksums, code changes during the run), retry lists and failures |
| `validation/` | samples, both coders' labels, adjudication, the coding guide and the validation plan |
| `tests/` | tests of the tool and of the scripts |
| `docs/` | tool documentation; `docs/DATASET.md` is the dataset README |
| `explorer/`, `site/` | source of the interactive dataset explorer and the dataset website |
| `notebooks/` | Jupyter notebooks that load the released tables and run simple analyses |

## Setup

Requires [uv](https://docs.astral.sh/uv/), git 2.30+ and, to re-mine, bash 4+
and GNU coreutils.

```bash
uv sync --locked --all-groups
uv run pytest -q
```

## Regenerate the paper's numbers from the released tables

The released tables are the dataset exactly as the paper counts it, so the
paper's statistics can be rebuilt from them without re-mining. Download the four
`*.csv.gz` tables from the Zenodo record next to this package, then:

```bash
mkdir -p release
for t in repositories revisions steps ghaw_manifests; do
    gunzip -c "$t.csv.gz" > "release/$t.csv"
done
cp run-logs/full-RUN.txt release/RUN.txt   # start of the mining run
touch -t 202610051200 release/*.csv        # its end, which is read from file times
uv run python scripts/paper_stats.py release --tex numbers.tex --figures figures
```

This reproduces the paper's numbers, figures and per-agent table. Four macros
differ by design, because the release already omits the rows the paper filters
out: the counts of generic-only repositories (`nGenericRepos`) and of
pre-ChatGPT matches (`nPreRelease`, `nPreReleaseHistories`) are zero, and
`nGhawManifests` lacks the three pre-ChatGPT manifests.

## Re-mine from scratch

`docs/FULL_RUN.md` documents the full run: preflight checks, launch,
monitoring, retries and merge. In short:

```bash
./scripts/preflight.sh out/full /data/work
WORK=/data/work ./scripts/mine.sh data/seart/repos-2026-10-03.txt out/full 32
uv run python scripts/build_release.py out/full      # writes out/release/
```

A re-run sees each repository's history as of the day it is cloned, so it
will differ from GHAgentCI by whatever was pushed, rewritten or deleted since
October 2026. `build_release.py` hashes author and committer emails with a
private salt, which is not distributed; a re-run with a new salt hashes them
differently.
