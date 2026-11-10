"""Create the GHAgentCI Zenodo record as an unpublished draft.

    ZENODO_TOKEN=... uv run python zenodo/upload.py --sandbox   # rehearse on sandbox.zenodo.org
    ZENODO_TOKEN=... uv run python zenodo/upload.py             # the real record

Uploads every file staged in out/zenodo/ (see zenodo/build.sh) with the
metadata in zenodo/metadata.json and the description in zenodo/description.html,
and prints the draft's link and its reserved DOI. It never publishes: review the
draft on the website and press Publish there. Publishing cannot be undone; files
of a published record can only be replaced by a new version.

The token needs the deposit:write scope; leave deposit:actions unticked, so
the token cannot publish. Create one under Account > Applications > Personal access tokens; the sandbox
has its own accounts and tokens.

Pass --draft ID to fill an existing draft instead of creating one, for example
to resume after an interrupted upload; files already present with the same
checksum are skipped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "zenodo"
STAGE = ROOT / "out" / "zenodo"


class Zenodo:
    def __init__(self, base: str, token: str) -> None:
        self.base = base
        self.token = token

    def request(self, method: str, url: str, body: object = None, data=None, headers=None) -> dict:
        if not url.startswith("http"):
            url = self.base + url
        heads = {"Authorization": f"Bearer {self.token}", **(headers or {})}
        if body is not None:
            data = json.dumps(body).encode()
            heads["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=heads)
        try:
            with urllib.request.urlopen(req, timeout=3600) as response:
                payload = response.read()
        except urllib.error.HTTPError as error:
            raise SystemExit(
                f"{method} {url}: {error.code} {error.read().decode()[:2000]}"
            ) from None
        return json.loads(payload) if payload else {}


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Progress:
    """A file-like reader that reports how much of a large upload has gone."""

    def __init__(self, path: Path) -> None:
        self.handle = path.open("rb")
        self.size = path.stat().st_size
        self.sent = 0
        self.name = path.name
        self.shown = -1

    def read(self, n: int = -1) -> bytes:
        chunk = self.handle.read(n if n > 0 else 1 << 20)
        self.sent += len(chunk)
        pct = 100 * self.sent // max(self.size, 1)
        if pct != self.shown and pct % 5 == 0:
            print(f"\r  {self.name}: {pct}%", end="", file=sys.stderr, flush=True)
            self.shown = pct
        return chunk

    def __len__(self) -> int:
        return self.size


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--sandbox", action="store_true", help="use sandbox.zenodo.org")
    parser.add_argument("--draft", help="fill this existing draft instead of creating one")
    parser.add_argument("--stage", default=str(STAGE), help="directory of files to upload")
    args = parser.parse_args(argv)

    token = os.environ.get("ZENODO_TOKEN")
    if not token:
        raise SystemExit("set ZENODO_TOKEN to a personal access token with deposit:write")
    stage = Path(args.stage)
    files = sorted(p for p in stage.iterdir() if p.is_file() and not p.name.startswith("."))
    if not files:
        raise SystemExit(f"{stage}: nothing to upload; run zenodo/build.sh first")

    base = "https://sandbox.zenodo.org/api" if args.sandbox else "https://zenodo.org/api"
    api = Zenodo(base, token)

    metadata = json.loads((HERE / "metadata.json").read_text(encoding="utf-8"))
    metadata["description"] = (HERE / "description.html").read_text(encoding="utf-8")

    if args.draft:
        draft = api.request("GET", f"/deposit/depositions/{args.draft}")
    else:
        draft = api.request("POST", "/deposit/depositions", body={})
    draft = api.request("PUT", draft["links"]["self"], body={"metadata": metadata})
    bucket = draft["links"]["bucket"]
    present = {f["filename"]: f["checksum"] for f in draft.get("files", [])}

    for path in files:
        checksum = md5(path)
        if present.get(path.name) == checksum:
            print(f"  {path.name}: already uploaded", file=sys.stderr)
            continue
        api.request(
            "PUT",
            f"{bucket}/{path.name}",
            data=Progress(path),
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": str(path.stat().st_size),
            },
        )
        print(f"\r  {path.name}: uploaded (md5 {checksum})", file=sys.stderr)

    draft = api.request("GET", draft["links"]["self"])
    doi = draft["metadata"].get("prereserve_doi", {}).get("doi", "(none)")
    print(f"draft:        {draft['links']['html']}")
    print(f"reserved DOI: {doi}")
    print("Review the draft on the website, then press Publish there.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
