"""scripts/build_release.py: the released tables, as the paper counts them."""

from __future__ import annotations

import csv
import gzip
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_release.py"
spec = importlib.util.spec_from_file_location("build_release", SCRIPT)
build_release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_release)

from test_paper_stats import _revision, _step, _write

from cai_miner.cli import REVISION_FIELDS, STEP_FIELDS, SUMMARY_FIELDS


def _read(path: Path) -> list[dict]:
    with gzip.open(path, "rt", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture
def run(tmp_path):
    """a/claude: agentic (strong Claude) plus a weak key; g/generic: only a
    generic_ai action; p/old: a 2021 match before ChatGPT; z/none: nothing."""
    out = tmp_path / "out"
    out.mkdir()
    _write(
        out / "repositories.csv",
        SUMMARY_FIELDS,
        [
            {"repository": r, "status": "ok", "n_agentic_files": "9", "agents": "stale"}
            for r in ("a/claude", "g/generic", "p/old", "z/none")
        ],
    )
    _write(
        out / "revisions.csv",
        REVISION_FIELDS,
        [
            _revision(
                "a/claude",
                "f1",
                "c2",
                "2026-03-01T10:00:00",
                content_sha256="bbb",
                author_email="Dev@Example.org",
                committer_email="noreply@github.com",
                author_name="Dev",
            ),
            _revision(
                "a/claude",
                "f1",
                "c1",
                "2026-01-05T10:00:00",
                "Added",
                content_sha256="aaa",
                author_email="dev@example.org",
                author_name="dev@example.org",
            ),
            _revision(
                "g/generic", "f1", "c3", "2026-02-01T10:00:00", "Added", content_sha256="ggg"
            ),
            _revision("p/old", "f1", "c4", "2021-05-01T10:00:00", "Added"),
        ],
    )
    _write(
        out / "steps.csv",
        STEP_FIELDS,
        [
            _step("a/claude", "f1", "c1", "2026-01-05T10:00:00", "claude"),
            _step("a/claude", "f1", "c2", "2026-03-01T10:00:00", "claude"),
            _step("a/claude", "f1", "c2", "2026-03-01T10:00:00", "claude", kind="env"),
            _step("g/generic", "f1", "c3", "2026-02-01T10:00:00", "generic_ai"),
            _step("g/generic", "f1", "c3", "2026-02-01T10:00:00", "codex", kind="env"),
            _step("p/old", "f1", "c4", "2021-05-01T10:00:00", "unknown", kind="ghaw"),
        ],
    )
    _write(
        out / "ghaw_manifests.csv",
        ["repository", "uid", "commit_hash", "commit_date", "artifact_kind"],
        [],
    )
    (out / "content").mkdir()
    for sha in ("aaa", "bbb", "ggg"):  # ggg: the generic history's content
        (out / "content" / f"{sha}.yml").write_text(f"name: {sha}\n")
    return out


def test_release_holds_what_the_paper_counts(run, tmp_path):
    release = tmp_path / "release"
    counts = build_release.build(run, release, b"\x00" * 32)
    assert counts == {
        "repositories": 4,
        "revisions": 2,
        "steps": 3,
        "ghaw_manifests": 0,
        "content": 2,
    }
    repos = {r["repository"]: r for r in _read(release / "repositories.csv.gz")}
    assert repos["a/claude"]["n_agentic_files"] == "1" and repos["a/claude"]["agents"] == "claude"
    assert repos["a/claude"]["first_agentic_date"] == "2026-01-05T10:00:00"
    for other in ("g/generic", "p/old", "z/none"):  # kept as denominators, not agentic
        assert repos[other]["n_agentic_files"] == "0" and repos[other]["agents"] == ""
    steps = _read(release / "steps.csv.gz")
    assert {s["repository"] for s in steps} == {"a/claude"}  # the generic history's weak key is out
    assert (release / "SHA256SUMS").read_text().count(".gz") == 5
    import tarfile

    with tarfile.open(release / "content.tar.gz") as tar:
        names = tar.getnames()
        assert names == ["content/aaa.yml", "content/bbb.yml"]  # only the release's revisions
        assert tar.extractfile("content/aaa.yml").read() == b"name: aaa\n"
        assert {m.mtime for m in tar.getmembers()} == {0}


def test_emails_are_pseudonymised_consistently(run, tmp_path):
    release = tmp_path / "release"
    build_release.build(run, release, b"\x01" * 32)
    revs = {r["commit_hash"]: r for r in _read(release / "revisions.csv.gz")}
    assert revs["c2"]["author_name"] == "Dev"  # names are kept
    a, b = revs["c2"]["author_email"], revs["c1"]["author_email"]
    assert a == b and len(a) == 64 and "@" not in a  # case-insensitive, same person
    assert revs["c2"]["committer_email"] != a
    assert revs["c1"]["author_name"] == a  # an address used as a name is hashed too
    text = gzip.decompress((release / "revisions.csv.gz").read_bytes()).decode()
    assert "example.org" not in text and "github.com" not in text
    assert revs["c2"]["agentic"] == "True" and revs["c2"]["strong_agents"] == "claude"


def test_rebuild_is_byte_identical(run, tmp_path):
    salt = b"\x02" * 32
    build_release.build(run, tmp_path / "one", salt)
    build_release.build(run, tmp_path / "two", salt)
    assert (tmp_path / "one" / "SHA256SUMS").read_text() == (
        tmp_path / "two" / "SHA256SUMS"
    ).read_text()
