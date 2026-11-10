"""scripts/build_explorer.py: the data behind the GHAgentCI Explorer."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_explorer.py"
spec = importlib.util.spec_from_file_location("build_explorer", SCRIPT)
build_explorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_explorer)

from test_paper_stats import _revision, _step, _write

from cai_miner.cli import REVISION_FIELDS, STEP_FIELDS, SUMMARY_FIELDS


@pytest.fixture
def run(tmp_path):
    """Two Claude repositories: one invokes it explicitly (`claude -p`), the
    other only installs it (`claude-code`), plus a non-agentic repository."""
    out = tmp_path / "out"
    out.mkdir()
    _write(
        out / "repositories.csv",
        SUMMARY_FIELDS,
        [
            {"repository": r, "status": "ok", "n_commits": "400"}
            for r in ("a/explicit", "b/install", "c/none")
        ],
    )
    _write(
        out / "revisions.csv",
        REVISION_FIELDS,
        [
            _revision(
                "a/explicit",
                "f1",
                "c2",
                "2026-03-01T10:00:00",
                file_path=".github/workflows/ai.yml",
                triggers="issue_comment",
                actor_gated="True",
            ),
            _revision(
                "a/explicit",
                "f1",
                "c1",
                "2026-01-05T10:00:00",
                "Added",
                file_path=".github/workflows/ai.yml",
            ),
            _revision(
                "b/install",
                "f1",
                "c3",
                "2026-02-01T10:00:00",
                "Added",
                file_path=".github/workflows/x.yml",
            ),
        ],
    )
    _write(
        out / "steps.csv",
        STEP_FIELDS,
        [
            dict(
                _step("a/explicit", "f1", "c1", "2026-01-05T10:00:00", "claude", kind="run"),
                pattern="claude -p",
            ),
            dict(
                _step("a/explicit", "f1", "c2", "2026-03-01T10:00:00", "claude", kind="run"),
                pattern="claude -p",
                job_id="review",
                step_index="2",
                step_name="Ask Claude",
                scope="step",
            ),
            dict(
                _step("b/install", "f1", "c3", "2026-02-01T10:00:00", "claude", kind="run"),
                pattern="claude-code",
            ),
        ],
    )
    return out


def test_build_writes_both_views_and_marks_install_only_repositories(run, tmp_path):
    explorer = tmp_path / "explorer"
    assert build_explorer.main([str(run), "-o", str(explorer)]) == 0
    summary = json.loads((explorer / "data" / "summary.json").read_text())
    assert summary["views"]["all"]["totals"]["agentic_repos"] == 2
    assert (
        summary["views"]["explicit"]["totals"]["agentic_repos"] == 1
    )  # the install match drops out
    repos = {r["repo"]: r for r in json.loads((explorer / "data" / "repos.json").read_text())}
    assert repos["a/explicit"]["explicit"] and not repos["b/install"]["explicit"]
    assert "c/none" not in repos
    shard = json.loads(
        (explorer / "data" / "shards" / f"{repos['a/explicit']['shard']:02d}.json").read_text()
    )
    [workflow] = shard["a/explicit"]
    assert (
        workflow["status"] == "active"
        and workflow["gated"]
        and workflow["triggers"] == ["issue_comment"]
    )
    assert [r[1] for r in workflow["revs"]] == ["A", "M"]  # chronological
    assert (
        workflow["invocations"][0]["pattern"] == "claude -p"
        and workflow["invocations"][0]["explicit"]
    )
    assert len(list((explorer / "data" / "shards").glob("*.json"))) == build_explorer.SHARDS


def test_no_author_names_or_emails_reach_the_app(run, tmp_path):
    explorer = tmp_path / "explorer"
    build_explorer.main([str(run), "-o", str(explorer)])
    for path in (explorer / "data").rglob("*.json"):
        text = path.read_text()
        assert (
            "author" not in text
            and "committer" not in text
            and "@" not in text.replace("@anthropic", "")
        )


def test_explicit_patterns_are_prompt_style_calls():
    assert build_explorer.explicit_only({"evidence_kind": "run", "pattern": "claude -p"})
    assert not build_explorer.explicit_only({"evidence_kind": "run", "pattern": "claude-code"})
    assert not build_explorer.explicit_only(
        {"evidence_kind": "run", "pattern": "npm install -g @openai/codex"}
    )
    assert build_explorer.explicit_only(
        {"evidence_kind": "uses", "pattern": "anthropics/claude-code-action"}
    )
