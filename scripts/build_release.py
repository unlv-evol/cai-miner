#!/usr/bin/env python3
"""Write the GHAgentCI release files: the dataset exactly as the paper counts it.

    python3 scripts/build_release.py out/full            # writes out/release/

Writes four gzip-compressed CSV tables and a checksum file:

* repositories.csv.gz   -- every repository of the frame, agentic or not, with
                           its mining status; the agentic columns recomputed
                           to the paper's definition;
* revisions.csv.gz      -- every revision of the agentic workflow histories;
* steps.csv.gz          -- every invocation in those histories, weak included;
* ghaw_manifests.csv.gz -- every gh-aw artifact revision in those histories;
* content.tar.gz        -- the content of every revision in revisions.csv.gz,
                           once per distinct content, as content/<sha256>.yml
                           (the revision's content_sha256);
* SHA256SUMS.

"As the paper counts it" (scripts/paper_stats.py, Dataset): named agents only
(the generic_ai group is left out), a history is agentic when a revision
carries strong evidence, and nothing before ChatGPT's release counts.

Author and committer emails are replaced by a salted SHA-256, so that one
person's commits can still be grouped without publishing addresses; names are
kept as git records them. The salt is read from --salt-file, created on first
use; keep it private and stable, or hashes change between builds and become
reversible by anyone who can guess an address.

The gzip streams carry no timestamp or file name, so a rebuild from the same
input writes byte-identical files.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import os
import re
import secrets
import sys
import tarfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_stats as ps

ROOT = Path(__file__).resolve().parents[1]
EMAIL_COLUMNS = ("author_email", "committer_email")
NAME_COLUMNS = ("author_name", "committer_name")
# An address inside a free-text field: some people set git's user.name to
# their email, which would otherwise publish it in the name column.
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def read_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return next(csv.reader(handle))


def salt_from(path: Path) -> bytes:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_hex(32) + "\n", encoding="utf-8")
        path.chmod(0o600)
        print(f"created a new salt in {path}; keep it private", file=sys.stderr)
    return bytes.fromhex(path.read_text(encoding="utf-8").strip())


def pseudonym(email: str, salt: bytes) -> str:
    """Salted SHA-256 of the normalised address; empty stays empty."""
    email = (email or "").strip().lower()
    return hashlib.sha256(salt + email.encode()).hexdigest() if email else ""


def write_gz(path: Path, fields: list[str], rows) -> int:
    """Deterministic gzip: no mtime and no file name in the header."""
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    count = 0
    for row in rows:
        writer.writerow({f: row.get(f, "") for f in fields})
        count += 1
    with path.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz:
        gz.write(buffer.getvalue().encode("utf-8"))
    return count


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_content(path: Path, store: Path, needed: set[str]) -> int:
    """content.tar.gz: one entry per distinct revision content, in name order,
    with fixed metadata so that a rebuild is byte-identical."""
    # List the store once: globbing it per content is quadratic (~10^5 files).
    stored = {name.split(".", 1)[0]: store / name for name in os.listdir(store)}
    missing = sorted(needed - stored.keys())
    if missing:
        raise SystemExit(
            f"{store}: no stored content for {len(missing)} revision(s), e.g. {missing[0]}"
        )
    files = {sha: stored[sha] for sha in needed}
    with (
        path.open("wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz,
        tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as tar,
    ):
        for sha in sorted(files):
            data = files[sha].read_bytes()
            info = tarfile.TarInfo(f"content/{files[sha].name}")
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(data))
    return len(files)


def build(out: Path, release: Path, salt: bytes, with_content: bool = True) -> dict[str, int]:
    d = ps.Dataset(out, include_generic=False)
    histories = d.agentic_histories
    in_dataset = lambda r: (r["repository"], r["uid"]) in histories
    release.mkdir(parents=True, exist_ok=True)

    # Evidence per revision, after the paper's filters.
    named_at: dict[tuple, set] = defaultdict(set)
    evidence_at: dict[tuple, int] = defaultdict(int)
    for s in d.invocations:
        key = (s["repository"], s["uid"], s["commit_hash"])
        named_at[key].add(s["agent"])
        evidence_at[key] += int(s.get("n_evidence") or 1)

    def revision(r: dict) -> dict:
        key = (r["repository"], r["uid"], r["commit_hash"])
        strong = d.agents(r)
        row = dict(r)
        for column in EMAIL_COLUMNS:
            row[column] = pseudonym(r.get(column, ""), salt)
        for column in NAME_COLUMNS:
            row[column] = EMAIL.sub(lambda m: pseudonym(m.group(0), salt), r.get(column, "") or "")
        row["agents"] = "|".join(sorted(named_at.get(key, set())))
        row["strong_agents"] = "|".join(sorted(strong))
        row["n_evidence"] = str(evidence_at.get(key, 0))
        row["agentic"] = "True" if strong else "False"
        return row

    # Repositories: the frame's denominators, agentic columns per the paper.
    per_repo = defaultdict(lambda: {"files": 0, "revisions": 0, "agents": set(), "dates": []})
    for key in histories:
        p = per_repo[key[0]]
        p["files"] += 1
        for r in d.histories[key]:
            agents = d.agents(r)
            if agents:
                p["revisions"] += 1
                p["agents"] |= agents
                p["dates"].append(r["commit_date"])

    def repository(r: dict) -> dict:
        row = dict(r)
        p = per_repo.get(r["repository"])
        row["n_agentic_files"] = str(p["files"]) if p else "0"
        row["n_agentic_revisions"] = str(p["revisions"]) if p else "0"
        row["agents"] = "|".join(sorted(p["agents"])) if p else ""
        dates = sorted(p["dates"], key=ps.instant) if p else []
        row["first_agentic_date"] = dates[0] if dates else ""
        row["last_agentic_date"] = dates[-1] if dates else ""
        return row

    counts = {}
    counts["repositories"] = write_gz(
        release / "repositories.csv.gz",
        read_header(out / "repositories.csv"),
        (repository(r) for r in d.repos),
    )
    counts["revisions"] = write_gz(
        release / "revisions.csv.gz",
        read_header(out / "revisions.csv"),
        (revision(r) for r in d.revisions if in_dataset(r)),
    )
    counts["steps"] = write_gz(
        release / "steps.csv.gz", read_header(out / "steps.csv"), d.invocations
    )
    counts["ghaw_manifests"] = write_gz(
        release / "ghaw_manifests.csv.gz",
        read_header(out / "ghaw_manifests.csv"),
        (m for m in d.manifests if in_dataset(m) and m["commit_date"][:10] >= ps.CUTOFF),
    )

    if with_content:
        needed = {r["content_sha256"] for r in d.revisions if in_dataset(r) and r["content_sha256"]}
        counts["content"] = write_content(release / "content.tar.gz", out / "content", needed)

    sums = [
        f"{file_digest(p)}  {p.name}"
        for p in sorted([*release.glob("*.csv.gz"), *release.glob("*.tar.gz")])
    ]
    (release / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("out", help="mining output directory (merged CSVs)")
    parser.add_argument("-o", "--release", default=str(ROOT / "out" / "release"))
    parser.add_argument(
        "--no-content",
        action="store_true",
        help="skip content.tar.gz (the tables alone take seconds)",
    )
    parser.add_argument(
        "--salt-file",
        default=str(ROOT / "out" / "release-email-salt.txt"),
        help="private salt for email pseudonyms; created if missing",
    )
    args = parser.parse_args(argv)
    counts = build(
        Path(args.out),
        Path(args.release),
        salt_from(Path(args.salt_file)),
        with_content=not args.no_content,
    )
    for name, n in counts.items():
        label = "content.tar.gz" if name == "content" else name + ".csv.gz"
        print(f"  {label:<24}{n:>9,} {'files' if name == 'content' else 'rows'}", file=sys.stderr)
    print(f"wrote {args.release}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
