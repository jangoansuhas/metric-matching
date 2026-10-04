#!/usr/bin/env python3
"""Capture the predeclared public GitHub repository-search frame, metadata only.

No code, README, tree, blob, metric definition, or repository archive is fetched.
The script intentionally uses anonymous REST requests and never reads a token.
"""

from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
from urllib.parse import quote, urlencode, urlsplit


ROOT = Path(__file__).resolve().parent
API = "https://api.github.com"
API_VERSION = "2022-11-28"
QUERIES = ("dbt metric", "dbt semantic model", "rill metrics")
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
TERMINAL_REFS = {"ok", "unavailable"}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def serialized(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".capture-", delete=False) as file:
        temporary = Path(file.name)
        file.write(data)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary, path)


def save_state(directory: Path, state: dict) -> None:
    state["updated_at_utc"] = utc_now()
    atomic_write(directory / "status.json", serialized(state))
    lines = [
        "# Held-out search capture report",
        "",
        f"- Attempt: `{state['attempt_id']}`",
        f"- Status: **{state['status']}**",
        f"- Started UTC: {state['started_at_utc']}",
        f"- Updated UTC: {state['updated_at_utc']}",
        f"- Precommit SHA-256: `{state['precommit_sha256']}`",
        f"- Development snapshot SHA-256: `{state['development_snapshot_sha256']}`",
        f"- Capture script SHA-256: `{state['script_sha256']}`",
        f"- Captured search pages: {len(state['pages'])}/3",
        f"- Terminal HEAD records: {sum(v['status'] in TERMINAL_REFS for v in state['refs'].values())}/{state.get('distinct_repositories', '?')}",
        f"- HEAD HTTP attempts: {len(state['ref_attempts'])}",
        f"- Interrupted raw ref artifacts: {len(state.get('interrupted_artifacts', []))}",
        "",
    ]
    if state.get("next_retry_at_utc"):
        lines += [f"Next retry after UTC: {state['next_retry_at_utc']}", ""]
    if state.get("failure"):
        lines += [f"Failure or pause: {state['failure']}", ""]
    if state["pages"]:
        lines += ["| Query | HTTP | Items / total | Incomplete | Body SHA-256 |", "| --- | ---: | ---: | --- | --- |"]
        for page in state["pages"]:
            lines.append(
                f"| `{page['query']}` | {page['response']['http_status']} | "
                f"{page.get('item_count', '?')} / {page.get('total_count', '?')} | "
                f"{page.get('incomplete_results', '?')} | `{page['response']['body_sha256']}` |"
            )
        lines.append("")
    if state.get("manifest_sha256"):
        lines += [f"Manifest SHA-256: `{state['manifest_sha256']}`", ""]
    if state["status"] not in ("finalized", "finalized_with_unavailable_refs"):
        lines += ["**This is an incomplete attempt, not a frozen manifest.**", ""]
    else:
        missing = sum(v["status"] == "unavailable" for v in state["refs"].values())
        lines += [f"Recorded unavailable HEADs: {missing}. These rows are not pinned projects.", ""]
    lines += [
        "The search ranks and HEAD refs were observed at separate times; this is not an atomic GitHub snapshot.",
        "Repository source remains unopened by this capture.",
        "",
    ]
    atomic_write(directory / "report.md", "\n".join(lines).encode("utf-8"))


def load_precommit(path: Path) -> tuple[dict, str, str]:
    raw = path.read_bytes()
    spec = json.loads(raw)
    fixed = spec.get("fixed_request_parameters", {})
    if (
        spec.get("schema_version") != 1
        or spec.get("queries_in_order") != list(QUERIES)
        or fixed.get("endpoint") != "GET /search/repositories"
        or fixed.get("sort") != "updated"
        or fixed.get("order") != "desc"
        or fixed.get("per_page") != 30
        or fixed.get("pages_per_query") != [1]
    ):
        raise ValueError("precommit differs from the fixed three-query, page-one design")
    snapshot = path.parent / spec["development_snapshot_file"]
    return spec, sha(raw), sha(snapshot.read_bytes())


def target_for_query(query: str) -> str:
    return "/search/repositories?" + urlencode(
        [("q", query), ("sort", "updated"), ("order", "desc"), ("per_page", "30"), ("page", "1")]
    )


def parse_headers(raw: bytes) -> tuple[int | None, dict[str, str]]:
    # curl may include a proxy CONNECT header and one or more redirect headers.
    blocks = [b for b in raw.replace(b"\r\n", b"\n").split(b"\n\n") if b.startswith(b"HTTP/")]
    if not blocks:
        return None, {}
    lines = blocks[-1].decode("iso-8859-1", errors="replace").splitlines()
    match = re.match(r"HTTP/\S+\s+(\d{3})", lines[0])
    headers = {}
    for line in lines[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.lower().strip()] = value.strip()
    return (int(match.group(1)) if match else None), headers


def checked_effective_url(value: str, expected_kind: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.netloc != "api.github.com" or parsed.username or parsed.password:
        raise ValueError("unexpected redirect target; refused to follow a non-API URL")
    if expected_kind == "search" and parsed.path != "/search/repositories":
        raise ValueError("search redirected away from repository metadata")
    if expected_kind == "ref" and not re.fullmatch(r"/repos/[^/]+/[^/]+/git/ref/heads/.+", parsed.path):
        raise ValueError("ref redirected away from Git reference metadata")
    return parsed.path + (("?" + parsed.query) if parsed.query else "")


def request(directory: Path, stem: str, target: str, kind: str) -> tuple[dict, bytes]:
    """Stage curl bytes privately, then atomically publish a completed response."""
    if not target.startswith("/") or "@" in target or "#" in target:
        raise ValueError("invalid metadata-only request target")
    url = API + target
    body_path = directory / (stem + ".body.bin")
    header_path = directory / (stem + ".headers.bin")
    if body_path.exists() or header_path.exists():
        raise FileExistsError("capture artifact already exists; will not overwrite raw evidence")
    body_path.parent.mkdir(parents=True, exist_ok=True)
    staging = directory / "inflight"
    staging.mkdir(exist_ok=True)
    staging_name = Path(stem).name + "-" + secrets.token_hex(4)
    temporary_body = staging / (staging_name + ".body.bin")
    temporary_headers = staging / (staging_name + ".headers.bin")
    started = utc_now()
    proc = subprocess.run(
        [
            "curl", "--disable", "--silent", "--show-error",
            "--proto", "=https", "--connect-timeout", "10",
            "--max-time", "25", "--max-filesize", "5000000", "--header", "Accept: application/vnd.github+json",
            "--header", f"X-GitHub-Api-Version: {API_VERSION}", "--header", "Cache-Control: no-cache",
            "--dump-header", str(temporary_headers), "--output", str(temporary_body),
            "--write-out", "%{http_code}\n%{url_effective}\n%{num_redirects}\n", url,
        ],
        capture_output=True,
        check=False,
    )
    completed = utc_now()
    if not temporary_body.exists():
        atomic_write(temporary_body, b"")
    if not temporary_headers.exists():
        atomic_write(temporary_headers, b"")
    raw_body = temporary_body.read_bytes()
    raw_headers = temporary_headers.read_bytes()
    # Never expose a partially written final artifact. The attempt lock prevents
    # another invocation from writing this stem while these renames complete.
    os.replace(temporary_body, body_path)
    os.replace(temporary_headers, header_path)
    http_status, headers = parse_headers(raw_headers)
    fields = proc.stdout.decode("utf-8", errors="replace").splitlines()
    effective_target = None
    redirect_error = None
    if len(fields) >= 2 and fields[1]:
        try:
            effective_target = checked_effective_url(fields[1], kind)
        except ValueError as exc:
            redirect_error = str(exc)
    response = {
        "request_target": target,
        "effective_target": effective_target,
        "started_at_utc": started,
        "completed_at_utc": completed,
        "server_date": headers.get("date"),
        "http_status": http_status,
        "curl_exit_code": proc.returncode,
        "redirect_count": int(fields[2]) if len(fields) >= 3 and fields[2].isdigit() else None,
        "redirect_error": redirect_error,
        "body_path": str(body_path.relative_to(directory)),
        "body_sha256": sha(raw_body),
        "body_bytes": len(raw_body),
        "headers_path": str(header_path.relative_to(directory)),
        "headers_sha256": sha(raw_headers),
        "headers_bytes": len(raw_headers),
        "etag": headers.get("etag"),
        "link": headers.get("link"),
        "x_github_request_id": headers.get("x-github-request-id"),
        "x_ratelimit_limit": headers.get("x-ratelimit-limit"),
        "x_ratelimit_remaining": headers.get("x-ratelimit-remaining"),
        "x_ratelimit_reset": headers.get("x-ratelimit-reset"),
        "retry_after": headers.get("retry-after"),
    }
    # Redirects are deliberately not followed: the capture only requests known API paths.
    # stderr is deliberately not logged: a proxy/curl diagnostic could contain credentials.
    return response, raw_body


def valid_response(response: dict) -> bool:
    try:
        email.utils.parsedate_to_datetime(response["server_date"])
    except (TypeError, ValueError, IndexError):
        return False
    return response["curl_exit_code"] == 0 and response["http_status"] == 200 and not response["redirect_error"]


def page_rows(raw: bytes, query: str, query_index: int) -> tuple[dict, list[dict]]:
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("incomplete_results") is not False:
        raise ValueError("search results are incomplete or malformed")
    total = data.get("total_count")
    items = data.get("items")
    if type(total) is not int or total < 0 or not isinstance(items, list) or len(items) != min(total, 30):
        raise ValueError("page item count does not match the fixed bound and total_count")
    rows = []
    seen = set()
    for rank, item in enumerate(items, 1):
        if not isinstance(item, dict) or not isinstance(item.get("owner"), dict):
            raise ValueError("invalid repository metadata")
        repo_id = item.get("id")
        owner = item["owner"].get("login")
        name = item.get("name")
        branch = item.get("default_branch")
        if (type(repo_id) is not int or repo_id <= 0 or repo_id in seen
                or not all(isinstance(v, str) and v for v in (owner, name, branch))
                or item.get("private") is not False):
            raise ValueError("missing, duplicate, or non-public repository metadata")
        seen.add(repo_id)
        rows.append({
            "query": query,
            "query_index": query_index,
            "page": 1,
            "rank_on_page": rank,
            "rank_in_query": rank,
            "repository_id": repo_id,
            "full_name": item.get("full_name"),
            "normalized_owner_repo": (owner + "/" + name).lower(),
            "owner": owner,
            "name": name,
            "html_url": item.get("html_url"),
            "default_branch": branch,
            "private": item.get("private"),
            "fork": item.get("fork"),
            "is_template": item.get("is_template"),
            "mirror_url": item.get("mirror_url"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "pushed_at": item.get("pushed_at"),
        })
    return {"total_count": total, "item_count": len(items), "incomplete_results": False}, rows


def verified_raw(directory: Path, response: dict) -> bytes:
    body = (directory / response["body_path"]).read_bytes()
    headers = (directory / response["headers_path"]).read_bytes()
    if sha(body) != response["body_sha256"] or sha(headers) != response["headers_sha256"]:
        raise ValueError("saved raw response failed SHA-256 verification")
    return body


def ranked_rows(directory: Path, state: dict) -> list[dict]:
    if len(state["pages"]) != 3:
        raise ValueError("all three search pages are required before collecting refs")
    rows = []
    for index, (query, page) in enumerate(zip(QUERIES, state["pages"], strict=True), 1):
        if page["query"] != query or not valid_response(page["response"]):
            raise ValueError("search page does not match the predeclared query order")
        summary, page_items = page_rows(verified_raw(directory, page["response"]), query, index)
        if any(page.get(key) != val for key, val in summary.items()):
            raise ValueError("search page summary differs from saved raw response")
        rows.extend(page_items)
    return rows


def distinct_rows(rows: list[dict]) -> list[dict]:
    first = {}
    for row in rows:
        previous = first.setdefault(row["repository_id"], row)
        if previous["default_branch"] != row["default_branch"] or previous["normalized_owner_repo"] != row["normalized_owner_repo"]:
            raise ValueError("same repository ID has conflicting branch or name across search pages")
    return list(first.values())


def capture_pages(directory: Path, state: dict) -> bool:
    for index, query in enumerate(QUERIES, 1):
        try:
            response, raw = request(directory, f"pages/search_{index:02d}", target_for_query(query), "search")
        except OSError as exc:
            state["status"] = "search_failed"
            state["failure"] = f"search page {index} transport failed ({type(exc).__name__}); start a new entire attempt"
            save_state(directory, state)
            return False
        record = {"query": query, "page": 1, "response": response}
        state["pages"].append(record)
        try:
            if not valid_response(response):
                raise ValueError(f"HTTP {response['http_status']} or missing server date/complete transport")
            summary, _ = page_rows(raw, query, index)
            record.update(summary)
        except (ValueError, json.JSONDecodeError) as exc:
            state["status"] = "search_failed"
            state["failure"] = f"search page {index} failed: {exc}; start a new entire attempt"
            save_state(directory, state)
            return False
        save_state(directory, state)
    try:
        unique = distinct_rows(ranked_rows(directory, state))
    except ValueError as exc:
        state["status"] = "search_failed"
        state["failure"] = f"search frame validation failed: {exc}; start a new entire attempt"
        save_state(directory, state)
        return False
    state["distinct_repositories"] = len(unique)
    state["result_occurrences"] = sum(p["item_count"] for p in state["pages"])
    state["status"] = "refs_pending"
    save_state(directory, state)
    return True


def ref_target(row: dict) -> str:
    return ("/repos/" + quote(row["owner"], safe="") + "/" + quote(row["name"], safe="")
            + "/git/ref/heads/" + quote(row["default_branch"], safe="/"))


def retry_time(response: dict) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    values = []
    if response.get("x_ratelimit_reset", "").isdigit():
        values.append(dt.datetime.fromtimestamp(int(response["x_ratelimit_reset"]), dt.timezone.utc) + dt.timedelta(seconds=2))
    if response.get("retry_after", "").isdigit():
        values.append(now + dt.timedelta(seconds=int(response["retry_after"])))
    return max([now + dt.timedelta(seconds=60), *values]).isoformat(timespec="seconds").replace("+00:00", "Z")


def record_interrupted_artifacts(directory: Path, state: dict) -> None:
    """Keep bytes from a killed in-flight curl, without mistaking them for a ref."""
    known = {r["response"]["body_path"] for r in state["ref_attempts"]}
    known |= {r["response"]["headers_path"] for r in state["ref_attempts"]}
    known |= {name for artifact in state.get("interrupted_artifacts", []) for name in artifact["paths"]}
    stems = set()
    for file in (directory / "refs").glob("repo_*.*.bin"):
        relative = str(file.relative_to(directory))
        if relative not in known:
            stems.add(relative.removesuffix(".body.bin").removesuffix(".headers.bin"))
    for stem in sorted(stems):
        paths = {}
        for suffix in ("body.bin", "headers.bin"):
            file = directory / f"{stem}.{suffix}"
            if file.exists():
                relative = str(file.relative_to(directory))
                raw = file.read_bytes()
                paths[relative] = {"sha256": sha(raw), "bytes": len(raw)}
        state.setdefault("interrupted_artifacts", []).append({
            "status": "interrupted_before_response_record",
            "observed_at_utc": utc_now(),
            "paths": paths,
        })
    for file in sorted((directory / "inflight").glob("*.bin")):
        relative = str(file.relative_to(directory))
        if relative not in known:
            raw = file.read_bytes()
            state.setdefault("interrupted_artifacts", []).append({
                "status": "interrupted_before_atomic_raw_commit",
                "observed_at_utc": utc_now(),
                "paths": {relative: {"sha256": sha(raw), "bytes": len(raw)}},
            })
    if stems or any((directory / "inflight").glob("*.bin")):
        save_state(directory, state)


def capture_refs(directory: Path, state: dict, max_refs: int | None) -> bool:
    rows = distinct_rows(ranked_rows(directory, state))
    if state["distinct_repositories"] != len(rows):
        raise ValueError("distinct repository count changed on resume")
    new_terminal = 0
    for row in rows:
        repo_id = str(row["repository_id"])
        current = state["refs"].get(repo_id)
        if current and current["status"] in TERMINAL_REFS:
            raw = verified_raw(directory, current["response"])
            if current["status"] == "ok" and json.loads(raw)["object"]["sha"] != current["head_sha"]:
                raise ValueError("recorded SHA differs from saved raw ref response")
            continue
        # A resume creates a new raw attempt file; no response is ever overwritten.
        attempt_number = 1
        while any((directory / f"refs/repo_{repo_id}_{attempt_number:02d}.{suffix}").exists()
                  for suffix in ("body.bin", "headers.bin")):
            attempt_number += 1
        stem = f"refs/repo_{repo_id}_{attempt_number:02d}"
        try:
            response, raw = request(directory, stem, ref_target(row), "ref")
        except OSError as exc:
            state["status"] = "refs_pending"
            state["failure"] = f"HEAD transport failed for repository ID {repo_id} ({type(exc).__name__}); use --resume"
            save_state(directory, state)
            return False
        record = {"repository_id": row["repository_id"], "requested_branch": row["default_branch"], "response": response}
        status = response["http_status"]
        try:
            if valid_response(response):
                data = json.loads(raw)
                obj = data.get("object", {})
                expected = "refs/heads/" + row["default_branch"]
                if data.get("ref") != expected or obj.get("type") != "commit" or not SHA_RE.fullmatch(obj.get("sha", "")):
                    raise ValueError("HEAD response is not the requested branch commit")
                record.update(status="ok", ref=data["ref"], head_sha=obj["sha"])
            elif status in (404, 409) and response["curl_exit_code"] == 0 and response["server_date"]:
                record.update(status="unavailable", reason=f"HTTP {status}; no pinned HEAD")
            else:
                record.update(status="pending", reason=f"HTTP {status}; curl exit {response['curl_exit_code']}")
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            record.update(status="pending", reason=f"invalid ref metadata: {exc}")
        state["refs"][repo_id] = record
        state["ref_attempts"].append(record)
        if record["status"] == "pending":
            if status in (403, 429) or response.get("x_ratelimit_remaining") == "0":
                state["status"] = "rate_limited"
                state["next_retry_at_utc"] = retry_time(response)
            else:
                state["status"] = "refs_pending"
            state["failure"] = f"HEAD for repository ID {repo_id} pending: {record['reason']}; use --resume"
            save_state(directory, state)
            return False
        state["status"] = "refs_pending"
        state["failure"] = None
        save_state(directory, state)
        new_terminal += 1
        complete = sum(v["status"] in TERMINAL_REFS for v in state["refs"].values())
        if complete % 10 == 0 or complete == len(rows):
            print(f"HEAD metadata recorded: {complete}/{len(rows)}", flush=True)
        if response.get("x_ratelimit_remaining") == "0" and complete < len(rows):
            state["status"] = "rate_limited"
            state["next_retry_at_utc"] = retry_time(response)
            state["failure"] = "anonymous core rate limit exhausted; use --resume after reset"
            save_state(directory, state)
            return False
        if max_refs is not None and new_terminal >= max_refs and complete < len(rows):
            state["failure"] = f"paused after {max_refs} new HEAD records; use --resume"
            save_state(directory, state)
            return False
    return True


def finalize(directory: Path, state: dict) -> None:
    rows = ranked_rows(directory, state)
    distinct = distinct_rows(rows)
    if set(state["refs"]) != {str(row["repository_id"]) for row in distinct}:
        raise ValueError("missing HEAD records; manifest cannot be finalized")
    refs = []
    for row in distinct:
        record = state["refs"][str(row["repository_id"])]
        if record["status"] not in TERMINAL_REFS:
            raise ValueError("pending HEAD record; manifest cannot be finalized")
        verified_raw(directory, record["response"])
        refs.append(record)
    unavailable = sum(ref["status"] == "unavailable" for ref in refs)
    status = "finalized_with_unavailable_refs" if unavailable else "finalized"
    manifest = {
        "schema_version": 1,
        "status": status,
        "attempt_id": state["attempt_id"],
        "started_at_utc": state["started_at_utc"],
        "finalized_at_utc": utc_now(),
        "precommit_file": state["precommit_file"],
        "precommit_sha256": state["precommit_sha256"],
        "development_snapshot_file": state["development_snapshot_file"],
        "development_snapshot_sha256": state["development_snapshot_sha256"],
        "capture_script_sha256": state["script_sha256"],
        "capture_script_snapshot_path": "capture_script_snapshot.py",
        "authentication": "anonymous; no GitHub token used",
        "api_version": API_VERSION,
        "fixed_queries_in_order": list(QUERIES),
        "fixed_parameters": {"sort": "updated", "order": "desc", "per_page": 30, "pages_per_query": [1]},
        "pages": state["pages"],
        "ranked_results": rows,
        "distinct_repositories": len(distinct),
        "refs": refs,
        "ref_attempts": state["ref_attempts"],
        "interrupted_artifacts": state.get("interrupted_artifacts", []),
        "unavailable_ref_count": unavailable,
        "time_scope": "Per-response observation times; not an atomic GitHub as-of snapshot.",
    }
    content = serialized(manifest)
    atomic_write(directory / "manifest.json", content)
    atomic_write(directory / "manifest.sha256", (sha(content) + "  manifest.json\n").encode())
    state["status"] = status
    state["manifest_sha256"] = sha(content)
    state["failure"] = None
    state["next_retry_at_utc"] = None
    save_state(directory, state)


def choose_resume(output: Path, attempt: str | None) -> Path:
    if attempt:
        directory = output / attempt
        if not directory.is_dir() or Path(attempt).name != attempt:
            raise ValueError("--attempt must be an existing attempt ID in the capture directory")
        return directory
    candidates = []
    for file in output.glob("attempt-*/status.json"):
        data = json.loads(file.read_bytes())
        if data.get("status") in ("refs_pending", "rate_limited") and len(data.get("pages", [])) == 3:
            candidates.append(file.parent)
    if len(candidates) != 1:
        raise ValueError(f"--resume found {len(candidates)} resumable attempts; specify --attempt if needed")
    return candidates[0]


def run_locked(directory: Path, args: argparse.Namespace, precommit: Path, spec: dict,
               precommit_hash: str, snapshot_hash: str) -> int:
    script_bytes = Path(__file__).read_bytes()
    script_hash = sha(script_bytes)
    if args.resume:
        state = json.loads((directory / "status.json").read_bytes())
        if state["precommit_sha256"] != precommit_hash or state["development_snapshot_sha256"] != snapshot_hash:
            raise ValueError("precommit/development snapshot hash changed; refusing to resume")
        if state.get("script_sha256") != script_hash:
            raise ValueError("capture script hash changed; start a new full search attempt")
        if sha((directory / "capture_script_snapshot.py").read_bytes()) != script_hash:
            raise ValueError("saved capture script snapshot differs from the running script")
        if state["status"] not in ("refs_pending", "rate_limited"):
            raise ValueError("only completed search pages with pending HEADs can be resumed")
        record_interrupted_artifacts(directory, state)
        if state.get("next_retry_at_utc"):
            when = dt.datetime.fromisoformat(state["next_retry_at_utc"].replace("Z", "+00:00"))
            if dt.datetime.now(dt.timezone.utc) < when:
                print(f"Rate limited; resume after {state['next_retry_at_utc']}. Attempt: {directory}")
                return 3
        state["next_retry_at_utc"] = None
        state["failure"] = None
        save_state(directory, state)
    else:
        attempt_id = directory.name
        atomic_write(directory / "capture_script_snapshot.py", script_bytes)
        state = {
            "schema_version": 1,
            "attempt_id": attempt_id,
            "status": "capturing_pages",
            "started_at_utc": utc_now(),
            "precommit_file": str(precommit),
            "precommit_sha256": precommit_hash,
            "development_snapshot_file": str((precommit.parent / spec["development_snapshot_file"]).resolve()),
            "development_snapshot_sha256": snapshot_hash,
            "script_sha256": script_hash,
            "authentication": "anonymous",
            "pages": [],
            "refs": {},
            "ref_attempts": [],
            "interrupted_artifacts": [],
            "failure": None,
            "next_retry_at_utc": None,
        }
        save_state(directory, state)
        if not capture_pages(directory, state):
            print(f"Search attempt failed; start a new whole attempt. Report: {directory / 'report.md'}")
            return 2
    try:
        if capture_refs(directory, state, args.max_refs):
            # Include partial staging files that appeared during the final batch.
            record_interrupted_artifacts(directory, state)
            finalize(directory, state)
            print(f"Manifest {state['status']}: {directory / 'manifest.json'}")
            print(f"Report: {directory / 'report.md'}")
            return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        state["status"] = "integrity_failed"
        state["failure"] = f"saved capture failed validation ({type(exc).__name__}); start a new entire attempt"
        save_state(directory, state)
        print(f"Integrity failure; no manifest. Report: {directory / 'report.md'}")
        return 2
    print(f"Attempt incomplete ({state['status']}); report: {directory / 'report.md'}")
    return 3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--precommit", type=Path, default=ROOT / "heldout_search_precommit.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "heldout_search_capture")
    parser.add_argument("--resume", action="store_true", help="resume pending HEADs only; never resume search pages")
    parser.add_argument("--attempt", help="attempt ID to resume if several are pending")
    parser.add_argument("--max-refs", type=int, help="pause after this many new HEAD records; no sleep")
    args = parser.parse_args()
    if args.max_refs is not None and args.max_refs < 1:
        parser.error("--max-refs must be positive")
    if args.attempt and not args.resume:
        parser.error("--attempt requires --resume")
    precommit = args.precommit.resolve()
    output = args.output_dir.resolve()
    spec, precommit_hash, snapshot_hash = load_precommit(precommit)
    if args.resume:
        directory = choose_resume(output, args.attempt)
    else:
        output.mkdir(parents=True, exist_ok=True)
        attempt_id = "attempt-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(4)
        directory = output / attempt_id
        directory.mkdir()
    # Prevent simultaneous invocations from writing the same raw response path/state.
    with (directory / "capture.lock").open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run_locked(directory, args, precommit, spec, precommit_hash, snapshot_hash)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        # Do not echo request URLs or curl diagnostics, which might contain auth material.
        print(f"Capture stopped: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
