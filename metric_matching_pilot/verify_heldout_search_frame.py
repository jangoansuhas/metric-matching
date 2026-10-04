#!/usr/bin/env python3
"""Read-only byte and metadata integrity check for a captured search frame."""

import argparse
import hashlib
import json
from pathlib import Path


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def checked_raw(directory: Path, response: dict) -> dict:
    for kind in ("body", "headers"):
        rel = Path(response[f"{kind}_path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Unsafe raw response path")
        raw = (directory / rel).read_bytes()
        if (digest(raw) != response[f"{kind}_sha256"]
                or len(raw) != response[f"{kind}_bytes"]):
            raise ValueError("Raw response checksum/size mismatch")
        if kind == "body":
            body = raw
    return json.loads(body)


def verify(directory: Path) -> tuple[int, int]:
    raw = (directory / "manifest.json").read_bytes()
    saved = (directory / "manifest.sha256").read_text(encoding="utf-8").split()[0]
    manifest = json.loads(raw)
    if digest(raw) != saved or manifest["status"] != "finalized":
        raise ValueError("Manifest digest or status mismatch")
    base = directory.parent.parent
    for kind in ("precommit", "development_snapshot", "capture_script"):
        name = manifest.get(f"{kind}_file") or {
            "capture_script": "capture_heldout_search_frame.py"}[kind]
        if digest((base / name).read_bytes()) != manifest[f"{kind}_sha256"]:
            raise ValueError(f"Referenced {kind} changed")
    queries = ["dbt metric", "dbt semantic model", "rill metrics"]
    if manifest["fixed_queries_in_order"] != queries or manifest["fixed_parameters"] != {
            "sort": "updated", "order": "desc", "per_page": 30, "pages_per_query": [1]}:
        raise ValueError("Search request parameters changed")
    rows = []
    for i, (page, query) in enumerate(zip(manifest["pages"], queries, strict=True), 1):
        data = checked_raw(directory, page["response"])
        if (page["query"] != query or page["page"] != 1
                or page["response"]["http_status"] != 200
                or data["incomplete_results"] is not False
                or page["incomplete_results"] is not False
                or len(data["items"]) != page["item_count"]
                or data["total_count"] != page["total_count"]):
            raise ValueError("Search page metadata changed")
        if not page["response"]["request_target"].startswith("/search/repositories?"):
            raise ValueError("Unexpected search request path")
        for rank, item in enumerate(data["items"], 1):
            rows.append((i, query, rank, item["id"],
                         (item["owner"]["login"] + "/" + item["name"]).lower(),
                         item["default_branch"]))
    claimed = [(r["query_index"], r["query"], r["rank_on_page"], r["repository_id"],
                r["normalized_owner_repo"], r["default_branch"])
               for r in manifest["ranked_results"]]
    if claimed != rows or len({r[3] for r in rows}) != manifest["distinct_repositories"]:
        raise ValueError("Ranked results or distinct repository count changed")
    refs = manifest["refs"]
    by_id = {r["repository_id"]: r for r in refs}
    if len(by_id) != len(refs) or set(by_id) != {r[3] for r in rows}:
        raise ValueError("HEAD records do not cover the search frame")
    for repo_id, record in by_id.items():
        data = checked_raw(directory, record["response"])
        if record["status"] != "ok" or data["object"]["sha"] != record["head_sha"]:
            raise ValueError(f"Unpinned or mismatched HEAD metadata: {repo_id}")
        if data["ref"] != record["ref"] or record["requested_branch"] not in {
                r[5] for r in rows if r[3] == repo_id}:
            raise ValueError(f"HEAD branch mismatch: {repo_id}")
    if manifest["unavailable_ref_count"] != 0:
        raise ValueError("Unavailable HEADs cannot be treated as pinned")
    return len(rows), len(by_id)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    occurrences, repositories = verify(args.directory)
    print(f"Read-only metadata frame verification passed: {occurrences} ranked results, "
          f"{repositories} pinned distinct repositories; no source inspected")


if __name__ == "__main__":
    main()
