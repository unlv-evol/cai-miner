#!/usr/bin/env python3
"""Build the data for the GHAgentCI Explorer, a static web app over the dataset.

    python3 scripts/build_explorer.py out/full            # writes explorer/
    python3 -m http.server -d explorer 8000               # then open localhost:8000

Reads the merged mining output and the validation results, and writes:

* explorer/data/summary.json -- every aggregate the overview, security,
  actions and method views draw, computed twice: from all strong evidence, and
  from explicit calls only (``run`` evidence kept only for prompt-style calls
  such as ``claude -p``; name and installation matches dropped, see below);
* explorer/data/repos.json -- one row per agentic repository, for the browser;
* explorer/data/shards/NN.json -- per-repository detail (workflow histories,
  revisions, invocations), split into shards so a detail view loads ~1 MB;
* explorer/index.html -- the app (explorer/app.html) wrapped in a document, for
  local serving; app.html itself is what gets published as an artifact.

Agentic counts follow the paper (scripts/paper_stats.py): named agents, strong
evidence, nothing before ChatGPT's release. No author or committer names or
emails are written: whether the release publishes them is still open.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zlib
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paper_stats as ps

ROOT = Path(__file__).resolve().parents[1]
EXPLORER = ROOT / "explorer"
FRAME = ROOT / "data" / "seart" / "frame-2026-10-03.csv"
SHARED = ROOT / "manuscripts" / "shared"
SHARDS = 64

# Prompt-style CLI calls. Validation (paper, Table II) confirmed `claude -p`,
# `claude --print` and `codex exec`; `copilot -p` and `gemini -p` are the same
# form for their CLIs. Every other `run` pattern matches a name or an install
# command (`claude-code`, `@openai/codex`, `npm install -g ...`), which the
# validation found mostly does not invoke an agent.
EXPLICIT_RUN = {"claude -p", "claude --print", "codex exec", "copilot -p", "gemini -p"}
TOP_AGENTS = 4  # agents with their own series; the rest fold into "other"
STAR_BANDS = (
    (0, 10, "<10"),
    (10, 100, "10-99"),
    (100, 1000, "100-999"),
    (1000, 10000, "1k-9.9k"),
    (10000, None, "10k+"),
)


def explicit_only(step: dict) -> bool:
    return step["evidence_kind"] != "run" or step["pattern"] in EXPLICIT_RUN


def shard_of(repo: str) -> int:
    return zlib.crc32(repo.lower().encode()) % SHARDS


def month(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


def months_between(start: date, end: date) -> list[date]:
    out, cur = [], date(start.year, start.month, 1)
    while cur <= end:
        out.append(cur)
        cur = date(cur.year + (cur.month == 12), cur.month % 12 + 1, 1)
    return out


def r1(x: float) -> float:
    return round(x, 1)


# ---------------------------------------------------------------------------
# aggregates, computed per view


def ranked_agents(d: ps.Dataset) -> list[str]:
    repos = defaultdict(set)
    for key in d.agentic_histories:
        for r in d.histories[key]:
            for a in d.agents(r):
                repos[a].add(key[0])
    return sorted((a for a in repos if a != "unknown"), key=lambda a: (-len(repos[a]), a))


def series_of(agent: str, top: list[str]) -> str:
    return ps.DISPLAY.get(agent, agent) if agent in top else "other"


def adoption_over_time(d: ps.Dataset, top: list[str], end: date) -> dict:
    """Repositories invoking each agent at the end of each month, and new
    agentic repositories per month."""
    timelines = defaultdict(list)  # repo -> [(date, uid, agents)]
    for key in d.agentic_histories:
        for r in d.histories[key]:
            agents = set() if r["git_change_type"] == "Deleted" else d.agents(r)
            timelines[key[0]].append((ps.day(r["commit_date"]), key[1], agents))
    start = ps.plot_start(d, end)
    months = months_between(start, end)
    names = [ps.DISPLAY.get(a, a) for a in top] + ["other"]
    active = {n: [0] * len(months) for n in names}
    total = [0] * len(months)
    first_month = Counter()
    for repo, events in timelines.items():
        events.sort(key=lambda e: e[0])
        first = next((when for when, _, agents in events if agents), None)
        if first:
            first_month[month(first)] += 1
        state: dict[str, set] = {}
        i = 0
        for m_index, m in enumerate(months):
            cutoff = date(m.year + (m.month == 12), m.month % 12 + 1, 1)
            while i < len(events) and events[i][0] < cutoff:
                state[events[i][1]] = events[i][2]
                i += 1
            now = set().union(*state.values()) if state else set()
            if now:
                total[m_index] += 1
            for s in {series_of(a, top) for a in now}:
                active[s][m_index] += 1
    return {
        "months": [month(m) for m in months],
        "series": [{"name": n, "values": active[n]} for n in names if any(active[n])],
        "total": total,
        "new": [first_month.get(month(m), 0) for m in months],
    }


def wiring(d: ps.Dataset, first_run: date) -> list[dict]:
    return [
        {"quarter": q, **{k: c[k] for k in ps.WIRING}}
        for q, c in ps.wiring_by_quarter(d, first_run)
    ]


def survival(d: ps.Dataset, top: list[str], first_run: date, min_at_risk: int = 50) -> dict:
    lives = d.lifetimes(first_run)
    groups: dict[str, list] = defaultdict(list)
    for t, gone, agents in lives:
        for a in agents:
            groups[series_of(a, top[:3])].append((t, gone))
    month_days = 365.25 / 12
    curves = []
    for name, obs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        points = [[0.0, 100.0, 100.0, 100.0]]
        for t, s, lo, hi, n in ps.kaplan_meier_ci(obs):
            if n < min_at_risk:
                break
            points.append([round(t / month_days, 2), r1(100 * s), r1(100 * lo), r1(100 * hi)])
        curves.append({"name": name, "n": len(obs), "points": points})
    overall = ps.kaplan_meier([(t, g) for t, g, _ in lives])
    return {
        "curves": curves,
        "abandoned": sum(1 for _, g, _ in lives if g),
        "repos": len(lives),
        "after": {str(h): r1(100 * (1 - ps.survival_at(overall, h))) for h in (30, 91, 182, 365)},
    }


def frame_rates(d: ps.Dataset) -> dict:
    """Adoption among mined repositories by language, stars and creation year."""
    if not FRAME.exists():
        return {}
    frame = {r["name"]: r for r in ps.read(FRAME)}
    mined = [r["repository"] for r in d.repos if r["status"] in ("ok", "incomplete")]
    agentic = {k[0] for k in d.agentic_histories}

    def rate_by(key) -> list[dict]:
        tot, hit = Counter(), Counter()
        for repo in mined:
            f = frame.get(repo)
            if not f:
                continue
            k = key(f)
            if k is None:
                continue
            tot[k] += 1
            hit[k] += repo in agentic
        return [
            {"key": k, "mined": tot[k], "agentic": hit[k], "rate": r1(100 * hit[k] / tot[k])}
            for k in tot
        ]

    def band(f):
        stars = int(f["stargazers"] or 0)
        return next(
            label for lo, hi, label in STAR_BANDS if stars >= lo and (hi is None or stars < hi)
        )

    langs = sorted(rate_by(lambda f: f["mainLanguage"] or None), key=lambda x: -x["mined"])
    years = sorted(rate_by(lambda f: f["createdAt"][:4] or None), key=lambda x: x["key"])
    stars = rate_by(band)
    order = [label for _, _, label in STAR_BANDS]
    return {
        "languages": [x for x in langs if x["mined"] >= 1000][:16],
        "stars": sorted(stars, key=lambda x: order.index(x["key"])),
        "years": [x for x in years if x["mined"] >= 200],
    }


def actions(d: ps.Dataset) -> list[dict]:
    latest = {
        (r["repository"], r["uid"], r["commit_hash"]) for r in d.latest.values() if d.agents(r)
    }
    by = defaultdict(lambda: {"repos": set(), "workflows": set(), "pins": [], "agents": Counter()})
    for s in d.invocations:
        k = (s["repository"], s["uid"], s["commit_hash"])
        if k not in latest or s["evidence_kind"] != "uses" or not s["action"]:
            continue
        a = by[s["action"].lower()]
        a["repos"].add(s["repository"])
        a["workflows"].add(k)
        a["pins"].append(bool(re.fullmatch(r"[0-9a-f]{40}", s.get("action_version") or "")))
        a["agents"][s["agent"]] += 1
    rows = [
        {
            "action": name,
            "agent": ps.DISPLAY.get(v["agents"].most_common(1)[0][0], "?"),
            "repos": len(v["repos"]),
            "workflows": len(v["workflows"]),
            "pinned": r1(100 * sum(v["pins"]) / len(v["pins"])),
        }
        for name, v in by.items()
    ]
    return sorted(rows, key=lambda x: (-x["repos"], x["action"]))[:30]


def triggers(d: ps.Dataset) -> list[dict]:
    return [
        {
            "trigger": r["label"],
            "n": r["n"],
            "permissions": r1(r["permissions"]),
            "gated": r1(r["gated"]),
            "pinned": None if r["pinned"] is None else r1(r["pinned"]),
        }
        for r in ps.trigger_constraints(d)
    ]


def view(d: ps.Dataset, out: Path, first_run: date, last_run: date, keep=None) -> dict:
    top = ranked_agents(d)[:TOP_AGENTS]
    m = ps.macros(d, out, None)
    invocations = [
        s for s in d.invocations if keep is None or s["evidence_kind"] != "run" or keep(s)
    ]
    latest = [r for r in d.latest.values() if d.agents(r)]
    return {
        "totals": {
            "agentic_repos": len({k[0] for k in d.agentic_histories}),
            "still_agentic": len({r["repository"] for r in latest}),
            "histories": len(d.agentic_histories),
            "workflows_now": len(latest),
            "revisions": len(d.rows_in_histories()),
            "invocations": len(invocations),
            "ghaw_repos": len(
                {x["repository"] for x in d.manifests} & {k[0] for k in d.agentic_histories}
            ),
        },
        "agents": [{"name": ps.DISPLAY.get(a, a)} for a in top],
        "adoption": adoption_over_time(d, top, last_run),
        "wiring": wiring(d, first_run),
        "survival": survival(d, top, first_run),
        "triggers": triggers(d),
        "profiles": ps.agent_profiles(d),
        "rates": frame_rates(d),
        "tasks": {k: v for k, v in m.items() if k.startswith("pctTask")},
    }


# ---------------------------------------------------------------------------
# validation: read what scripts/score_validation.py generated


def validation() -> dict:
    macros = {}
    tex = SHARED / "numbers-validation.tex"
    if tex.exists():
        for name, value in re.findall(r"\\def\\(\w+)\{(.*)\}", tex.read_text()):
            macros[name] = value.replace("\\%", "").replace("{,}", ",")
    rows = []
    table = SHARED / "table-validation.tex"
    if table.exists():
        for line in table.read_text().splitlines():
            cells = [c.strip() for c in line.rstrip("\\ ").split("&")]
            if len(cells) == 6:
                label = re.sub(r"\\code\{(.*?)\}", r"\1", cells[0]).replace("\\_", "_")
                rows.append(
                    {
                        "kind": label,
                        "units": int(cells[1]),
                        "yes": int(cells[2]),
                        "maybe": int(cells[3]),
                        "no": int(cells[4]),
                        "precision": float(cells[5]),
                    }
                )
    keep = (
        "nSampled",
        "agreeOverall",
        "kappaOverall",
        "nRecallPool",
        "nMissed",
        "pctMissed",
        "accAgent",
        "nRecallRepos",
    )
    return {"rows": rows, **{k: macros[k] for k in keep if k in macros}}


# ---------------------------------------------------------------------------
# repositories and their detail


def repositories(d_all: ps.Dataset, d_exp: ps.Dataset) -> tuple[list[dict], dict[int, dict]]:
    frame = {r["name"]: r for r in ps.read(FRAME)} if FRAME.exists() else {}
    summary = {r["repository"]: r for r in d_all.repos}
    explicit = {k[0] for k in d_exp.agentic_histories}
    ghaw = {x["repository"] for x in d_all.manifests}
    by_key = defaultdict(list)
    for s in d_all.steps:  # weak evidence too, for the detail view
        if s["agent"] == ps.GENERIC:
            continue
        by_key[(s["repository"], s["uid"], s["commit_hash"])].append(s)

    per_repo = defaultdict(list)
    for key in d_all.agentic_histories:
        per_repo[key[0]].append(key)

    rows, shards = [], defaultdict(dict)
    for repo, keys in per_repo.items():
        files, ever, now, first, last = [], set(), set(), None, None

        # Path, then first revision, then uid: a path can hold several
        # histories (a file deleted and recreated), and their order must not
        # depend on the order of the input rows.
        def order(k: tuple) -> tuple:
            revs = d_all.histories[k]
            return (revs[-1]["file_path"], revs[0]["_order"][0], k[1])

        for key in sorted(keys, key=order):
            revs = d_all.histories[key]
            agentic_revs = [r for r in revs if d_all.agents(r)]
            ref = agentic_revs[-1]
            for r in agentic_revs:
                ever |= d_all.agents(r)
            when = [ps.day(r["commit_date"]) for r in agentic_revs]
            first = min([first, when[0]] if first else [when[0]])
            last = max([last, when[-1]] if last else [when[-1]])
            final = revs[-1]
            if final["git_change_type"] == "Deleted":
                status = "deleted"
            elif d_all.agents(final):
                status = "active"
                now |= d_all.agents(final)
            else:
                status = "agent removed"
            invs = [
                {
                    "agent": ps.DISPLAY.get(s["agent"], s["agent"]),
                    "kind": s["evidence_kind"],
                    "pattern": s["pattern"],
                    "scope": s["scope"],
                    "job": s["job_id"],
                    "step": s["step_index"],
                    "name": s["step_name"],
                    "action": s["action"],
                    "version": s["action_version"],
                    "tasks": s.get("tasks", ""),
                    "explicit": explicit_only(s),
                }
                for s in by_key.get((key[0], key[1], ref["commit_hash"]), [])
            ]
            files.append(
                {
                    "path": final["file_path"]
                    if final["git_change_type"] != "Deleted"
                    else ref["file_path"],
                    "paths": sorted({r["file_path"] for r in revs}),
                    "status": status,
                    "name": ref.get("workflow_name", ""),
                    "triggers": [t for t in (ref.get("triggers") or "").split("|") if t],
                    "permissions": (ref.get("permissions") or "").strip(),
                    "gated": ref.get("actor_gated") == "True",
                    "ref": ref["commit_hash"],
                    "revs": [
                        [
                            r["commit_date"][:10],
                            (r["git_change_type"] or "?")[0],
                            r["commit_hash"][:12],
                            sorted(ps.DISPLAY.get(a, a) for a in d_all.agents(r)),
                            sorted(d_all.kinds_at.get((key[0], key[1], r["commit_hash"]), set())),
                        ]
                        for r in revs
                    ],
                    "invocations": invs,
                }
            )
        f = frame.get(repo, {})
        s = summary.get(repo, {})
        row = {
            "repo": repo,
            "lang": f.get("mainLanguage") or "",
            "stars": int(f.get("stargazers") or 0),
            "created": (f.get("createdAt") or "")[:10],
            "commits": int(s.get("n_commits") or 0),
            "agents": sorted(ps.DISPLAY.get(a, a) for a in ever),
            "now": sorted(ps.DISPLAY.get(a, a) for a in now),
            "first": first.isoformat(),
            "last": last.isoformat(),
            "files": len(files),
            "active": sum(x["status"] == "active" for x in files),
            "ghaw": repo in ghaw,
            "explicit": repo in explicit,
            "shard": shard_of(repo),
        }
        rows.append(row)
        shards[row["shard"]][repo] = files
    rows.sort(key=lambda r: r["repo"].lower())
    return rows, shards


# ---------------------------------------------------------------------------


def write_json(path: Path, data) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    path.write_text(text, encoding="utf-8")
    return len(text.encode())


def write_index(explorer: Path) -> None:
    """index.html for local serving: the published fragment, in a document."""
    app = (explorer / "app.html").read_text(encoding="utf-8")
    (explorer / "index.html").write_text(
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        "<!-- Generated by scripts/build_explorer.py from app.html. Edit app.html. -->\n"
        "</head>\n<body>\n" + app + "\n</body>\n</html>\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("out", help="mining output directory (merged CSVs)")
    parser.add_argument("-o", "--explorer", default=str(EXPLORER), help="app directory")
    parser.add_argument(
        "--collected",
        nargs=2,
        metavar=("FIRST", "LAST"),
        type=date.fromisoformat,
        help="first and last day of mining, for input without the run's RUN.txt "
        "(such as the released tables)",
    )
    args = parser.parse_args(argv)
    out, explorer = Path(args.out), Path(args.explorer)

    print(
        "loading the dataset twice (all strong evidence, explicit calls only)...", file=sys.stderr
    )
    d_all = ps.Dataset(out, include_generic=False)
    d_exp = ps.Dataset(out, include_generic=False, keep=explicit_only)
    first_run, last_run = args.collected or ps.run_dates(out)

    summary = {
        "built": date.today().isoformat(),
        "collected": [first_run.isoformat(), last_run.isoformat()],
        "mined": sum(1 for r in d_all.repos if r["status"] in ("ok", "incomplete")),
        "generic_only": len(d_all.generic_repos),
        "explicit_patterns": sorted(EXPLICIT_RUN),
        "views": {
            "all": view(d_all, out, first_run, last_run),
            "explicit": view(d_exp, out, first_run, last_run, keep=explicit_only),
        },
        "actions": actions(d_all),
        "validation": validation(),
    }
    size = write_json(explorer / "data" / "summary.json", summary)
    rows, shards = repositories(d_all, d_exp)
    size += write_json(explorer / "data" / "repos.json", rows)
    for n in range(SHARDS):
        shard = dict(sorted(shards.get(n, {}).items()))  # independent of input order
        size += write_json(explorer / "data" / "shards" / f"{n:02d}.json", shard)
    if (explorer / "app.html").exists():
        write_index(explorer)
    print(
        f"wrote {len(rows)} repositories, {SHARDS} shards, {size / 1e6:.1f} MB of data "
        f"to {explorer}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
