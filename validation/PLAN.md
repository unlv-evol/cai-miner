# Validation sampling plan

Status: samples drawn, coding not started (revised 2026-10-27).

## What we need to claim

| # | Claim in the paper | Measured by | Paper macro |
|---|---|---|---|
| C1 | An invocation in `steps.csv` is a real coding-agent invocation | **Precision**, per evidence stratum and overall | `\precisionOverall`, `\precStrong`, `\precWeak` |
| C2 | Strong-only classification is the right default | Precision of weak-only invocations vs. strong | `\precWeak` vs `\precStrong` |
| C3 | The `agent` label is right | Agent accuracy on the same sample | new: `\accAgent` |
| C4 | Coders agree on what an invocation is | Cohen's κ and raw agreement on Q1 | `\kappaOverall` |
| C5 | We do not miss many agentic workflows | **Recall check** on a keyword pool (catalogue diff dropped, see C5) | new: `\nMissed`, `\pctMissed` |
| ~~C6~~ | ~~`tasks` and `actor_gated` are usable filters~~ | Dropped 2026-10-27 to simplify coding, as in the paper's first version; both stay documented as heuristics | -- |
| C7 | The `generic_ai` group (1,091 unattributed Marketplace actions) does or does not belong in the agentic counts | Its own precision, against a pre-set threshold | `\precGeneric`, `\precGenericLow` |

C1–C4 are the core of the paper, and comparable dataset papers report exactly
this kind of figure. C5 is what reviewers will ask about a *content-based*
detector: a path-based extractor cannot miss files by construction, but this
one can.

## Prerequisites (all met)

1. **Final run with the fixed grouping code.** Done 2026-10-05: 196,938
   repositories, 196,253 mined (`out/full/RUN.txt`). The precision and
   calibration samples were drawn from its final `steps.csv`.
2. **Frozen catalogue.** `catalogue.toml`, the merge of `default.toml`
   and `marketplace.toml`, frozen 2026-10-03 before mining; its checksum is in
   `RUN.txt`.
3. **Recall subset.** 1,000 random frame repositories re-mined with
   `--keep-all` into `out/recall` (997 mined, 3 clone failures).

## Sampling unit

One **distinct invocation**: a row of `steps.csv`, deduplicated on
`(content_sha256, agent, job_id, step_index)`.

- *Why deduplicate:* a step is repeated in every later revision of its file,
  and identical template files recur across repositories. Without
  deduplication the sample would be dominated by a few long-lived files, and
  coders would label the same YAML many times.
- *Cap:* at most **2 units per repository per stratum**, so that no single
  project, such as a monorepo with 40 agent workflows, dominates a stratum.
- *What coders see:* the workflow at that commit via a GitHub permalink,
  `https://github.com/<repo>/blob/<commit_hash>/<file_path>`, scrolled to
  `job_id` / `step_index`. File-scope units (`scope = file`) are judged on the
  whole file.

## Strata

The strata are mutually exclusive and assigned in this order:

| Stratum | Rule | Why it is separate |
|---|---|---|
| **X** generic | `agent = generic_ai` | Unattributed third-party actions: a mix of coding agents and LLM utilities. Decides C7. Reported separately, **not** in the overall figure. |
| **P** parse-failed | `parse_ok = false` | Classified by the coarser text scan. Expected to be the weakest. |
| **G** gh-aw | `evidence_kind = ghaw` | Exact by construction. A small sample confirms it. |
| **U** uses | `evidence_kind = uses` | Bulk of the dataset. |
| **R** run | `evidence_kind = run` | Shell substrings: highest false-positive risk among strong kinds (echo, comments, unrelated tools named `codex`/`aider`). |
| **F** path | `evidence_kind = path` | Copilot reserved filename. Checks the "reserved name" argument. |
| **W** weak-only | `evidence_kind ∈ {job, url, env}` | Justifies excluding weak evidence (C2). Reported separately, **not** in the overall figure. |

Within each stratum, sort the units by `agent` and draw **systematically**
from a random start, so that every agent present in the stratum appears in
proportion to its size.

## Sample size

**Revised 2026-10-29 (option A): named-agent target n = 384** across strata P,
G, U, R and F, the ones behind the overall precision figure. That is a nominal
±5% margin at **95%** confidence for an unknown proportion
(z² · 0.25 / e² = 1.96² · 0.25 / 0.05² ≈ 384), the usual standard in software
engineering validation. Strata W and X keep 96 units each, for **576** units in
total. (The weighted estimate's actual interval is what the scorer reports;
with unequal weights it can be somewhat wider than the nominal margin.)

*Why the change.* The first draw targeted 664 named-agent units (±5% at 99%),
856 in total, about 17.5 coding hours per coder. With
coding not yet started and the paper due on 10 November, the sample was
reduced before any unit was coded, so no answer could influence it. At the
expected precision (≥ 0.9), n ≈ 384 still gives about ±3%.

*What was kept.* W stays at 96 because it is the only evidence that excluding
weak evidence is justified (C2). X stays at 96 because the fold-in rule for
`generic_ai` (lower Wilson bound ≥ 0.90) is nearly unreachable with fewer units:
at n = 50, two errors already fail it. Recall stays at 200 units.

**Allocation:**
1. The 384 named-agent units go to P, G, U, R and F in proportion to their
   distinct-unit counts, with a minimum of **30** per stratum, so that the rare
   strata (P, F) are still represented; largest remainders settle rounding
   (`allocate_proportional` in `scripts/sample_validation.py`).
2. W and X get 96 each and take no share of the 384.

**How it was drawn.** The 856-unit sample of 2026-10-04 was drawn first (floors
of 96, systematic within stratum, per-repository cap of 2). The 576-unit sample keeps, within each named
stratum, a seeded random subset of the units already drawn for it
(`sample_validation.py subsample`, seed 20261029), so it is still a random
sample of each stratum and still honours the cap. W and X are unchanged. Unit
ids and the shuffled order are those of the first draw, so ids have gaps.

**As drawn** (`precision_strata.csv`): 576 units from 459 repositories.

| Stratum | distinct units | first draw | sampled |
|---|---|---|---|
| X generic | 5,793 | 96 | 96 |
| P parse-failed | 750 | 97 | 30 |
| G gh-aw | 31,971 | 139 | 80 |
| U uses | 51,266 | 165 | 128 |
| R run | 46,679 | 159 | 116 |
| F path | 6,077 | 104 | 30 |
| W weak-only | 20,066 | 96 | 96 |

The named-agent strata P, G, U, R and F hold 384 units, as targeted.

**Overall precision** (strata P, G, U, R, F only) is the population-weighted
combination, because proportional allocation would starve the rare strata:

```
p̂ = Σ_h W_h · p̂_h,   W_h = N_h / N
Var(p̂) = Σ_h W_h² · p̂_h (1 − p̂_h) / n_h · (1 − n_h / N_h)
```

Report the overall figure with a 95% interval, and each stratum with a 95%
Wilson interval. Wilson behaves at proportions near 1, where the normal
approximation does not.

## Codebook

Two coders (`\nCoders = 2`) label every unit independently. A unit has two
questions. (Q3 task and Q4 gating were dropped on 2026-10-27, before any unit
was coded, to reduce the coding effort.)

**Q1 Invocation.** *Does this step (or, for file scope, this workflow) invoke a
coding agent when the workflow runs?*

- **Yes:** it runs an LLM-based agent or assistant that acts on the repository
  or its activity. This means reading code or diffs and producing reviews,
  comments, labels, commits or pull requests. Includes the Copilot
  coding-agent setup workflow and gh-aw workflows.
- **Maybe:** an LLM is called, but it is unclear whether it is agentic. Examples
  are a single prompt that summarises release notes, or an agent step that is
  hard-disabled (`if: false`) or only runs in dry-run mode.
- **No:** no agent runs. Examples are a credential feeding a test suite, the
  pattern appearing in an `echo`, comment or docs path, an unrelated tool with
  a colliding name, or a step that only installs an agent and never calls it.

**Q2 Agent.** *Which agent is it?* Write exactly one of these values; the
scorer compares them literally (ignoring case) with the detector's `agent`:

| value | when |
|---|---|
| `claude`, `codex`, `copilot`, `gemini`, `cursor`, `aider`, `devin`, `pr_agent`, `coderabbit`, `goose`, `opencode`, `openhands` | the vendor's agent, directly or through a wrapper action |
| `generic_ai` | a third-party AI action not tied to one of the vendors above |
| `unknown` | a gh-aw file that does not name its engine |
| `other` | a coding agent not in this list |
| `unclear` | cannot be determined from the workflow |

Answer Q2 only when Q1 is yes or maybe.

Only Q1 needs adjudication. Q2 is coded once by each coder and reported as
agreement with the detector's `agent`.

### Procedure

1. **Calibration.** Before independent coding starts, both coders jointly code
   the **30 units** of `calibration_sheet.csv`, drawn from repositories outside
   the precision sample, and refine the definitions above. These units are not
   counted. Settle the open Q1 question below here.
2. **Independent coding.** Each coder fills their own sheet
   (`precision_sheet_A.csv` or `_B.csv`, and the matching `recall_sheet_*`)
   without seeing the other's. The sheets carry only what is needed to find
   the invocation; the detector's columns (`evidence_kind`, `pattern`, `agent`,
   `tasks`) stay in `precision_sample.csv`, which coders do not open until both
   are done.
3. **Agreement.** Compute Cohen's κ on Q1 (three categories) overall and per
   stratum, plus raw agreement.
4. **Adjudication.** Disagreements are resolved by discussion. The adjudicated
   label is final.
5. **Precision** = Yes / n, reported both **strict** (Maybe counts as wrong)
   and **lenient** (Maybe counts as right). The paper uses strict.

## C5: recall check

Recall cannot be estimated by random sampling of non-agentic workflows. If
agentic files are around 1% of workflow files, a sample big enough to find any
misses would need thousands of labels. Instead, use two targeted checks that
bound it.

1. **Keyword pool.** Re-mine a random **1,000 repositories** from the frame
   with `--keep-all --content-dir`. Keep the latest revision of each
   *non-agentic* workflow file that matches a broad, deliberately
   over-inclusive regex:
   `claude|anthropic|codex|openai|copilot|gemini|cursor|aider|devin|coderabbit|llm|gpt|ai[-_ ]review|agent`.
   Label a random **200** of those with Q1 (and Q2). As drawn: the 997 mined
   repositories hold 772 with workflow files, whose keyword pool has 341 files;
   200 were sampled (`recall_sample.csv`). Report the share that are real
   invocations, with a Wilson interval, as missed agentic workflows *within
   the keyword pool*. That is a lower bound on misses, and it is stated as
   such.
2. ~~**Catalogue diff.**~~ **Dropped 2026-10-04.** The plan was to run the
   merged Marketplace catalogue over the same 1,000 repositories and count the
   invocations it finds that `default.toml` does not, as misses by
   construction. That assumed the full run would use `default.toml` alone. It
   used the merged `catalogue.toml` instead (decided 2026-10-03, see
   "Open decisions"), so the Marketplace patterns are already part of the
   detector and the diff would no longer measure anything it missed. Recall
   rests on the keyword pool alone, and the paper states it as a lower bound.

Each missed case found is also a catalogue bug report. Fix the pattern, record
it in the paper's limitations, and do not re-draw the precision sample.

## Decision rules

These are set now, so the outcome cannot steer them.

- **Strong stratum precision, lower bound of the 95% interval < 0.90:**
  inspect its false positives and tighten or drop the offending patterns.
  Re-run, then draw a **fresh** sample for that stratum and report both
  rounds.
- **W (weak-only) precision ≥ the strong strata:** the strong-only default is
  not justified. Revisit `--include-weak` before publishing.
- **X (generic_ai), lower bound of the 95% Wilson interval ≥ 0.90:** fold the
  generic group into the agentic counts and headline figures. Below 0.90, keep
  it out of them and report it as a separate figure ("a further N repositories
  use other AI-assisted actions"). Either way it stays in the released data,
  labelled `agent = generic_ai`. The scorer prints which branch applies.
- **κ < 0.6 on Q1:** the codebook is ambiguous. Re-calibrate on the
  disagreements, then have both coders re-code the whole sample.

## Outputs

Released with the dataset:

| File | Content |
|---|---|
| `precision_sample.csv` | Sampled units with stratum, permalink and the detector's columns |
| `precision_strata.csv` | Per stratum: rows, distinct units, units available under the cap, sampled, weight |
| `precision_sheet_A.csv`, `_B.csv` | Each coder's answers (blank sheets carry no detector columns) |
| `precision_adjudication.csv` | Q1 disagreements, with the agreed `q1_final` and rationale |
| `calibration_sample.csv`, `calibration_sheet.csv` | The 30 calibration units and the joint sheet; not counted |
| `labeling/` | The package sent to coders: one workbook and the coding guide per coder, and the shared calibration workbook (source of the guide: `labeling_src/guide.tex`) |
| `recall_sample.csv`, `recall_pool_size.csv`, `recall_sheet_*.csv`, `recall_adjudication.csv` | The same for the keyword pool |
| `PLAN.md` | This plan, as followed |

### Running it

```bash
# 1. draw (seeded; default seed 20261017) -- done 2026-10-04, do not redraw
python3 scripts/sample_validation.py precision out/full/steps.csv --revisions out/full/revisions.csv -o validation/
# reduce the named-agent strata to 384 units (95% confidence), keeping W and X -- done 2026-10-29
python3 scripts/sample_validation.py subsample --archive <backup-dir> -o validation/
python3 scripts/sample_validation.py recall out/recall/revisions.csv --content-dir out/recall/content -o validation/
# calibration: 30 units from repositories outside the precision sample (seed 20261016),
# one joint sheet; coded together before independent coding and not counted
python3 scripts/sample_validation.py calibration out/full/steps.csv --exclude validation/precision_sample.csv -o validation/

# 2. coders fill their workbook from the labelling package (validation/labeling/,
#    see its ORGANISER-README.md), then each returned workbook is imported back:
python3 scripts/labeling.py build -o validation/labeling        # done 2026-10-29
python3 scripts/labeling.py import validation/returned/GHAgentCI-labeling-coder-A.xlsx --coder A
python3 scripts/labeling.py import validation/returned/GHAgentCI-labeling-coder-B.xlsx --coder B
python3 scripts/labeling.py import validation/returned/GHAgentCI-calibration.xlsx --calibration

# 3. score; exits 1 and writes *_adjudication.csv while Q1 disagreements are open
python3 scripts/score_validation.py -d validation/

# 4. fill q1_final in the adjudication sheet(s), score again, rebuild the paper
python3 scripts/score_validation.py -d validation/ && make -C manuscripts/msr
```

The scorer writes `manuscripts/shared/numbers-validation.tex`, which the paper
loads after `numbers.tex`. Until coding and adjudication are complete it
reports agreement but withholds precision, so half-resolved labels cannot reach
the paper. It prints a per-stratum table with strict and lenient precision,
Wilson intervals and per-stratum κ.

## Schedule (paper due 10 Nov 2026 AoE)

Revised 2026-10-27; the original plan had coding done by 28 October.

| By | Step |
|---|---|
| 28 Oct | Second coder confirmed; calibration (30 units, jointly); Q1 open question settled |
| 3 Nov | Independent coding done: 576 precision + 200 recall units per coder |
| 4 Nov | Scoring, adjudication of Q1 disagreements, final scoring |
| 5 Nov | Abstract registered (does not depend on validation figures) |
| 6 Nov | Validation figures in the paper (`make -C manuscripts/msr`) |
| 10 Nov | Paper submitted |

About 806 units (576 precision, 200 recall, 30 calibration) at roughly one
minute each with two questions is about 13 hours per coder: about two and a
half hours a day per coder until 3 November.

## Open decisions

- Second coder: who? Needed before calibration on 28 October.
- ~~Catalogue for the full run~~ Decided 2026-10-03: `catalogue.toml`,
  the frozen merge of `default.toml` and `marketplace.toml`.
- Should Q1 count a plain LLM inference call (e.g., `actions/ai-inference`
  summarising an issue) as **Yes** or **Maybe**? This changes Copilot's numbers
  more than any other agent's. Settle it during calibration, before
  independent coding.
