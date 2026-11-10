# Changelog

All notable changes to cai-miner are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-11-10

First public release. This is the version GHAgentCI was mined with; until then
the tool was developed under the working name `awe`.

### Added

- `cai-miner` command (also `python -m cai_miner`) that walks the first-parent
  history of each workflow file in local git clones and detects coding-agent
  invocations in every revision.
- Tiered evidence: `uses`, `run`, `path` and `ghaw` are strong; `job`, `url`
  and `env` are weak and only count with `--include-weak`.
- Exact detection of GitHub Agentic Workflows from the compiler header, and
  full parsing of their manifests into `ghaw_manifests.csv`.
- Outputs `repositories.csv`, `revisions.csv`, `steps.csv` and
  `ghaw_manifests.csv`, plus an optional content-addressed store of every
  distinct workflow revision.
- Bundled, frozen detector catalogues (`catalogue.toml`, `default.toml`,
  `marketplace.toml`); `catalogue.toml` is the default.
- Blob accounting and bulk backfill for partial clones, so incomplete
  repositories are reported rather than silently under-counted.

[Unreleased]: https://github.com/unlv-evol/cai-miner/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/unlv-evol/cai-miner/releases/tag/v0.1.0
