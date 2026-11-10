# Cloning repositories for cai-miner

`cai-miner` reads local clones; it never talks to the GitHub API. How you clone
decides how long a run takes and how much disk it needs. Measured numbers are
in [BENCHMARKS.md](../BENCHMARKS.md).

## Recommended: a size-capped blob filter

```bash
git clone --filter=blob:limit=64k --no-checkout --single-branch \
    https://github.com/OWNER/NAME.git
```

A size cap fetches everything `cai-miner` reads in a single server-built
packfile while leaving large blobs behind. `--no-checkout` skips the working
tree, which the tool does not need. Both caps below produce byte-identical
output; the choice is a time and bandwidth trade:

| repository | class | cap | total | disk |
| ---------- | ----- | --- | ----- | ---- |
| vite | ordinary | **64k** | **5 s** | **31 MB** |
| vite | | 1m | 7 s | 66 MB |
| langchain | large | **64k** | **18 s** | **108 MB** |
| langchain | | 1m | 33 s | 300 MB |
| godot | large | **64k** | **42 s** | **454 MB** |
| godot | | 1m | 71 s | 1176 MB |
| amplihack | gh-aw adopter | 64k | 41 s | 48 MB |
| amplihack | | **1m** | **16 s** | 196 MB |

`64k` wins everywhere except on gh-aw adopters, whose compiled workflows reach
240 kB and so have to be backfilled, and a backfill costs a full fetch
negotiation per repository however few objects it needs. Since gh-aw adopters
are about 1% of repositories, prefer `1m` only for a gh-aw-heavy list.

A workflow file larger than the cap is not lost: `cai-miner` detects which
blobs are absent locally (without network access, by running `git cat-file`
under `GIT_NO_LAZY_FETCH`) and bulk-fetches exactly those. The blob-accounting
columns in `repositories.csv` make the outcome checkable.

## Strategies to avoid

| strategy | vite | uv |
| -------- | ---- | -- |
| blobless (`--filter=blob:none`) + prefetch | 210 s | >300 s (timeout) |
| full clone, no filter | 13 s | 72 s |

On a blobless clone, `git cat-file` backfills missing blobs one network round
trip at a time, and requesting the object ids up front does not fix it:
`git fetch <oids>` costs server-side resolution against the whole repository,
roughly independent of how many ids you ask for. `cai-miner` still detects a
partial clone and prefetches in bulk as a fallback (disable with
`--no-prefetch`), but a `blob:limit` clone is faster and simpler.

## Sizing a large run

With a capped clone, **extraction, not cloning, is the bottleneck** on large
repositories: most CPU time goes to YAML parsing. Extraction parallelises
across repositories (run several `cai-miner` processes on disjoint lists,
sharing one `--content-dir`), while clone bandwidth does not. Size a large run
on cores rather than network.
