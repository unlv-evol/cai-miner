# Output reference

`cai-miner -o OUT/` writes four CSV files, and `--content-dir` adds a content
store. Without `-o`, agent invocations (the `steps.csv` rows) are printed to
standard output.

List-valued columns are `|`-joined throughout. Dates are ISO 8601 with offset.

## What gets emitted

By default only the histories of files that are agentic **at some point** are
emitted, but their *entire* history comes with them, including revisions from
before the agent was introduced and after it was removed. This keeps adoption
and abandonment observable without storing every CI workflow revision ever
made. `--keep-all` emits every workflow revision instead.

Repository-level denominators are recorded regardless, so the proportion of a
repository's workflows that are agentic remains computable.

## `revisions.csv`: one row per touch of a matched file

`repository`, `uid`, `commit_hash`, `author_name`, `author_email`,
`committer_name`, `committer_email`, `authored_date`, `commit_date`,
`file_path`, `previous_file_path`, `file_hash`, `previous_file_hash`,
`content_sha256`, `git_change_type`, `symbolic_link`, `previous_symbolic_link`,
`parse_ok`, `workflow_name`, `triggers`, `n_jobs`, `n_steps`, `permissions`,
`agents`, `strong_agents`, `n_evidence`, `agentic`, `actor_gated`

`uid` identifies a logical file across content changes **and renames**. A file
that is deleted and later recreated at the same path receives a new `uid`.

`actor_gated` is true when the workflow restricts who can trigger it (for
example by checking `github.actor` or the author association).

## `steps.csv`: one row per agent invocation

`repository`, `uid`, `commit_hash`, `commit_date`, `file_path`,
`content_sha256`, `parse_ok`, `agent`, `scope`, `evidence_kind`,
`evidence_kinds`, `n_evidence`, `pattern`, `job_id`, `step_index`, `step_name`,
`action`, `action_version`, `triggers`, `tasks`

Evidence items are collapsed to one row per invocation, so counting rows counts
invocations. A step that both `uses:` an agent action and binds that agent's
credential is one invocation carrying two evidence items, not two rows.

`scope` is `step` when the evidence is attached to a specific step, or `file`
when it describes the revision as a whole: a reserved filename, a reserved job
id, a workflow-level credential, a gh-aw manifest. `evidence_kind` names the
most decisive item (ranked `ghaw`, `uses`, `run`, `path`, `job`, `url`, `env`),
`evidence_kinds` lists all of them, and `n_evidence` says how many were
collapsed.

`tasks` holds purpose labels (`review`, `triage`, `implement`, `test`, `docs`,
`security`, `scheduled`, `on_demand`) inferred from workflow triggers and from
workflow, job and step names.

## `ghaw_manifests.csv`: one row per gh-aw artifact revision

`repository`, `uid`, `commit_hash`, `commit_date`, `file_path`,
`content_sha256`, `artifact_kind`, `parse_ok`, `agent_id`, `engine_version`,
`schema_version`, `compiler_version`, `model`, `strict`, `n_tools`, `tools`,
`n_mcp_tools`, `mcp_tools`, `n_safe_outputs`, `safe_outputs`, `n_secrets`,
`secrets`, `n_actions`, `n_containers`, `n_imports`, `imports`, `sandboxed`,
`network`, `permissions`, `n_evals`, `timeout_minutes`, `max_turns`,
`frontmatter_keys`

`artifact_kind` is `source` (the authored Markdown) or `lock` (the compiled
workflow). See [GitHub Agentic Workflows](ghaw.md).

## `repositories.csv`: one row per repository

`repository`, `n_commits`, `n_workflow_files`, `n_workflow_revisions`,
`n_agentic_files`, `n_agentic_revisions`, `agents`, `first_agentic_date`,
`last_agentic_date`, `n_blobs_requested`, `n_blobs_read`, `n_blobs_missing`, `status`

Written even when a repository contains no agentic workflows, and also when
one fails outright (`status = error`), so that adoption rates have an honest
denominator. A repository that silently vanishes from this file is
indistinguishable from one that was never sampled.

`status` is `ok`, `incomplete` (some blobs never arrived, so detection is
under-counted for that repository) or `error` (traversal failed). On a partial
clone an unfetched blob is simply absent, which otherwise looks exactly like a
repository with no agentic workflows; the counters make the difference
visible. A clean run has `n_blobs_missing == 0` for every repository.

## Content store

With `--content-dir DIR`, every distinct workflow revision that is emitted is
written once as `DIR/<sha256>.yml`, keyed by the `content_sha256` column.
Writes are atomic, so several `cai-miner` processes can share one store.

## Degraded parsing

Workflow revisions mid-history frequently fail to parse as YAML. When that
happens the file is scanned as plain text instead, `parse_ok` is `false`, and at
most one evidence item is reported per agent (patterns overlap across kinds:
`claude-code` occurs inside `anthropics/claude-code-action`). Filter on
`parse_ok` if you need structural fields such as `job_id`.

## Traversal semantics

History is walked with `--first-parent`, so only the mainline of each
repository is considered; commits that only ever existed on merged side
branches are not visited. Rename detection uses git's default similarity
threshold via `-M`. File modes are read from the raw log output, so symbolic
links are flagged rather than silently treated as regular files.
