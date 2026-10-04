#!/usr/bin/env python3
"""Audit dbt MODEL artifacts against pinned Git blobs and a dbt manifest.

This checks file and metadata provenance only. A manifest's generated_at is a
separate, unauthenticated build event; neither a compiled expression lineage
nor metric equivalence is inferred. No dbt or SQL execution is performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath


DEFAULT_JSON = Path(__file__).with_name("generic_compiled_provenance_report.json")
DEFAULT_MD = Path(__file__).with_name("generic_compiled_provenance_report.md")
SHA_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *args], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=False)


def safe_relative(value: object) -> str | None:
    """Accept only portable, unambiguous paths confined to a project root."""
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return None
    path = PurePosixPath(value)
    if (path.is_absolute() or any(part in (".", "..") for part in value.split("/"))
            or any(part in ("", ".", "..") for part in value.split("/"))):
        return None
    return value


def within_repo(repo: Path, value: object) -> tuple[Path | None, str | None]:
    relative = safe_relative(value)
    if relative is None:
        return None, "invalid_or_escaping_relative_path"
    path = repo / relative
    try:
        path.resolve().relative_to(repo)
    except ValueError:
        return None, "path_resolves_outside_repo"
    return path, None


def git_blob(repo: Path, commit: str, value: object) -> dict:
    """Read from immutable Git tree, not mutable source files in the worktree."""
    if not SHA_RE.fullmatch(commit):
        return {"status": "invalid_commit_pin"}
    relative = safe_relative(value)
    if relative is None:
        return {"status": "unsafe_path"}
    listing = git(repo, "ls-tree", "-z", commit, "--", relative)
    if listing.returncode != 0:
        return {"status": "git_tree_unavailable"}
    rows = [entry for entry in listing.stdout.split(b"\0") if entry]
    matches = []
    for entry in rows:
        try:
            info, path = entry.split(b"\t", 1)
            mode, kind, oid = info.decode("ascii").split(" ")
            if path == relative.encode("utf-8"):
                matches.append((mode, kind, oid))
        except (ValueError, UnicodeDecodeError):
            return {"status": "git_tree_unreadable"}
    if len(matches) != 1:
        return {"status": "missing_pinned_blob"}
    mode, kind, oid = matches[0]
    if kind != "blob" or mode not in ("100644", "100755"):
        return {"status": "not_regular_pinned_file", "git_mode": mode}
    shown = git(repo, "show", f"{commit}:{relative}")
    if shown.returncode != 0:
        return {"status": "pinned_blob_unreadable", "git_oid": oid}
    return {"status": "pinned_blob_read", "git_oid": oid, "git_mode": mode,
            "sha256": sha256(shown.stdout), "bytes": len(shown.stdout),
            "data": shown.stdout}


def equality(actual: bytes | None, claimed: bytes | None) -> str:
    if actual is None or claimed is None:
        return "unavailable"
    if actual == claimed:
        return "exact"
    if actual == claimed + b"\n":
        return "one_trailing_lf_only"
    if actual.strip() == claimed.strip():
        return "strip_only"
    return "different"


def file_evidence(repo: Path, value: object) -> dict:
    path, error = within_repo(repo, value)
    if error:
        return {"status": error}
    assert path is not None
    if path.is_symlink() or not path.is_file():
        return {"status": "missing_or_symlink_file"}
    data = path.read_bytes()
    return {"status": "file_read", "sha256": sha256(data), "bytes": len(data), "data": data}


def public_evidence(evidence: dict) -> dict:
    return {key: value for key, value in evidence.items() if key != "data"}


def unique_json(raw: bytes) -> dict:
    def no_duplicate(pairs: list[tuple[str, object]]) -> dict:
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON key: {key}")
            value[key] = item
        return value
    result = json.loads(raw, object_pairs_hook=no_duplicate)
    if not isinstance(result, dict):
        raise ValueError("manifest root is not an object")
    return result


def config_name(pinned: dict) -> str | None:
    if pinned.get("status") != "pinned_blob_read":
        return None
    try:
        text = pinned["data"].decode("utf-8")
    except UnicodeDecodeError:
        return None
    names = re.findall(r"^name:\s*['\"]?([A-Za-z_][A-Za-z_0-9-]*)['\"]?\s*(?:#.*)?$", text, re.M)
    return names[0] if len(names) == 1 else None


def validate_node(repo: Path, commit: str, node_id: str, node: dict,
                  global_reasons: list[str]) -> dict:
    reasons = list(global_reasons)
    source_path = node.get("original_file_path")
    compiled_path = node.get("compiled_path")
    pinned = git_blob(repo, commit, source_path)
    working = file_evidence(repo, source_path)
    compiled = file_evidence(repo, compiled_path)
    raw = node.get("raw_code")
    raw_bytes = raw.encode("utf-8") if isinstance(raw, str) else None
    compiled_code = node.get("compiled_code")
    compiled_bytes = compiled_code.encode("utf-8") if isinstance(compiled_code, str) else None
    source_raw = equality(pinned.get("data"), raw_bytes)
    compiled_match = equality(compiled.get("data"), compiled_bytes)
    working_match = equality(pinned.get("data"), working.get("data"))

    checksum = node.get("checksum") or {}
    checksum_name = checksum.get("name") if isinstance(checksum, dict) else None
    checksum_value = checksum.get("checksum") if isinstance(checksum, dict) else None
    checksum_status = "unavailable"
    checksum_raw_status = "unavailable"
    if checksum_name == "sha256" and isinstance(checksum_value, str) and pinned.get("data") is not None:
        checksum_status = "exact" if sha256(pinned["data"]) == checksum_value else "different"
        if raw_bytes is not None:
            checksum_raw_status = "exact" if sha256(raw_bytes) == checksum_value else "different"
    elif checksum_name is not None:
        checksum_status = "unsupported_or_unavailable"
        checksum_raw_status = "unsupported_or_unavailable"
    if node.get("unique_id") != node_id:
        reasons.append("manifest_unique_id_mismatch")
    if node.get("language", "sql") != "sql":
        reasons.append("non_sql_model")
    if node.get("compiled") is not True:
        reasons.append("manifest_node_not_marked_compiled")
    if pinned.get("status") != "pinned_blob_read":
        reasons.append("source_" + pinned["status"])
    if source_raw not in ("exact", "one_trailing_lf_only"):
        reasons.append("manifest_raw_code_" + source_raw + "_vs_pinned_blob")
    # dbt may hash its normalized raw_code rather than source file bytes.
    # Record checksum-versus-blob without equating the two; verify raw_code's
    # checksum and an explicitly documented source -> raw_code transformation.
    if checksum_raw_status != "exact":
        reasons.append("manifest_source_checksum_" + checksum_raw_status + "_vs_raw_code")
    if compiled.get("status") != "file_read":
        reasons.append("compiled_" + compiled["status"])
    if compiled_match != "exact":
        reasons.append("manifest_compiled_code_" + compiled_match + "_vs_file")
    if working_match != "exact":
        reasons.append("working_source_" + working_match + "_vs_pinned_blob")
    source_mapping = ("exact" if source_raw == "exact" and checksum_raw_status == "exact" else
                      "one_trailing_lf_only" if source_raw == "one_trailing_lf_only" and checksum_raw_status == "exact" else
                      "needs_review")
    return {
        "node_id": node_id, "status": "needs_review" if reasons else "model_artifact_checks_pass",
        "reasons": sorted(set(reasons)), "source_path": source_path,
        "compiled_path": compiled_path, "pinned_source": public_evidence(pinned),
        "working_source": public_evidence(working), "compiled_file": public_evidence(compiled),
        "manifest_raw_code_sha256": sha256(raw_bytes) if raw_bytes is not None else None,
        "manifest_source_checksum": {"name": checksum_name, "value": checksum_value,
                                     "versus_pinned_blob": checksum_status,
                                     "versus_manifest_raw_code": checksum_raw_status},
        "pinned_blob_vs_manifest_raw_code": source_raw,
        "source_mapping_alignment": source_mapping,
        "source_mapping_policy": "exact bytes or pinned blob = manifest raw_code UTF-8 + one LF; "
                                 "manifest sha256 checksum must equal raw_code hash",
        "working_file_vs_pinned_blob": working_match,
        "manifest_compiled_code_sha256": sha256(compiled_bytes) if compiled_bytes is not None else None,
        "compiled_file_vs_manifest_compiled_code": compiled_match,
        "metric_expression_lineage": "metric_expression_unverified", "semantic_equivalence": "not_evaluated",
    }


def validate_case(root: str, manifest_path: str, commit: str, project: str,
                  dbt_version: str) -> dict:
    repo = Path(root).resolve()
    reasons = []
    info = {"repo_root": root, "manifest_path": manifest_path,
            "expected_commit": commit, "expected_project": project,
            "expected_dbt_version": dbt_version}
    if not SHA_RE.fullmatch(commit):
        reasons.append("expected_commit_not_full_sha")
    top = git(repo, "rev-parse", "--show-toplevel")
    head = git(repo, "rev-parse", "--verify", "HEAD^{commit}")
    actual_head = head.stdout.decode("ascii", errors="replace").strip() if head.returncode == 0 else None
    info.update({"git_root_matches_input": top.returncode == 0 and Path(top.stdout.decode().strip()).resolve() == repo,
                 "checked_out_commit": actual_head, "checked_out_commit_matches_pin": actual_head == commit})
    if not info["git_root_matches_input"]:
        reasons.append("repo_root_not_git_toplevel")
    if actual_head != commit:
        reasons.append("checked_out_commit_mismatch")
    pinned_config = git_blob(repo, commit, "dbt_project.yml")
    declared_name = config_name(pinned_config)
    info["pinned_project_config"] = {**public_evidence(pinned_config), "declared_name": declared_name}
    if declared_name != project:
        reasons.append("pinned_project_config_name_unverified_or_mismatch")

    mpath, error = within_repo(repo, manifest_path)
    if error or mpath is None or mpath.is_symlink() or not mpath.is_file():
        info.update({"status": "needs_review", "reasons": sorted(set(reasons + ["manifest_unavailable_or_unsafe"])),
                     "universe": "unknown", "nodes": [], "coverage": {"models_enumerated": 0}})
        return info
    raw_manifest = mpath.read_bytes()
    info["manifest_file"] = {"sha256": sha256(raw_manifest), "bytes": len(raw_manifest)}
    try:
        manifest = unique_json(raw_manifest)
    except (ValueError, UnicodeDecodeError) as exc:
        info.update({"status": "needs_review", "reasons": sorted(set(reasons + ["manifest_invalid_json"])),
                     "manifest_error": str(exc), "universe": "unknown", "nodes": [],
                     "coverage": {"models_enumerated": 0}})
        return info
    meta = manifest.get("metadata") or {}
    if not isinstance(meta, dict):
        meta = {}
    generation = meta.get("generated_at")
    try:
        if not isinstance(generation, str) or datetime.fromisoformat(generation.replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("missing timezone")
    except ValueError:
        reasons.append("manifest_generation_time_unverified")
    info["manifest_metadata"] = {
        "project_name": meta.get("project_name"), "dbt_version": meta.get("dbt_version"),
        "dbt_schema_version": meta.get("dbt_schema_version"),
    }
    info["build_event"] = {"generated_at": generation, "invocation_id": meta.get("invocation_id"),
                           "commit_attested_by_build": False,
                           "note": "Manifest generation and checked-out Git commit are separate events."}
    if meta.get("project_name") != project:
        reasons.append("manifest_project_name_mismatch")
    if meta.get("dbt_version") != dbt_version:
        reasons.append("manifest_dbt_version_mismatch")
    if not isinstance(meta.get("dbt_schema_version"), str):
        reasons.append("manifest_schema_version_missing")
    nodes = manifest.get("nodes")
    if not isinstance(nodes, dict):
        info.update({"status": "needs_review", "reasons": sorted(set(reasons + ["manifest_nodes_unavailable"])),
                     "universe": "unknown", "nodes": [], "coverage": {"models_enumerated": 0}})
        return info
    models = []
    for key, node in sorted(nodes.items()):
        if not isinstance(node, dict) or node.get("resource_type") != "model":
            continue
        model = validate_node(repo, commit, key, node, reasons)
        if node.get("package_name") != project:
            model["status"] = "needs_review"
            model["reasons"] = sorted(set(model["reasons"] + ["model_package_differs_from_project"]))
        models.append(model)
    counts = Counter(node["status"] for node in models)
    info.update({
        "status": "needs_review" if reasons or counts["needs_review"] else "model_artifact_checks_pass",
        "reasons": sorted(set(reasons)), "universe": "all_manifest_model_nodes",
        "coverage": {
            "models_enumerated": len(models),
            "model_artifact_checks_pass": counts["model_artifact_checks_pass"],
            "needs_review": counts["needs_review"],
            "pinned_source_blobs_read": sum(n["pinned_source"]["status"] == "pinned_blob_read" for n in models),
            "pinned_blob_and_compiled_file_exact_manifest_code": sum(
                n["pinned_source"]["status"] == "pinned_blob_read" and
                n["compiled_file_vs_manifest_compiled_code"] == "exact" for n in models),
            "manifest_source_checksums_equal_pinned_blob": sum(n["manifest_source_checksum"]["versus_pinned_blob"] == "exact" for n in models),
            "manifest_source_checksums_equal_raw_code": sum(n["manifest_source_checksum"]["versus_manifest_raw_code"] == "exact" for n in models),
            "manifest_raw_code_exact_pinned_blob": sum(n["pinned_blob_vs_manifest_raw_code"] == "exact" for n in models),
            "manifest_raw_code_one_trailing_lf_only_pinned_blob": sum(n["pinned_blob_vs_manifest_raw_code"] == "one_trailing_lf_only" for n in models),
            "manifest_raw_code_strip_only_pinned_blob": sum(n["pinned_blob_vs_manifest_raw_code"] == "strip_only" for n in models),
            "source_mapping_needs_review": sum(n["source_mapping_alignment"] == "needs_review" for n in models),
            "compiled_files_exact_manifest_code": sum(n["compiled_file_vs_manifest_compiled_code"] == "exact" for n in models),
            "compiled_files_strip_only_manifest_code": sum(n["compiled_file_vs_manifest_compiled_code"] == "strip_only" for n in models),
        }, "nodes": models,
    })
    return info


def make_report(specs: list[list[str]]) -> dict:
    cases = [validate_case(*spec) for spec in specs]
    return {"schema": "generic_compiled_model_provenance_v1", "scope": "development_only",
            "cases": cases, "metric_expression_lineage": "metric_expression_unverified",
            "semantic_equivalence": "not_evaluated",
            "limitation": "A compiled MODEL artifact check is not a compiled metric-expression lineage pass; "
                          "manifest generation has no authenticated Git commit attestation."}


def render_md(report: dict) -> bytes:
    lines = ["# Compiled dbt MODEL provenance audit (development only)", "",
             "Source is anchored to a pinned Git blob. Compiled file equality is checked against "
             "manifest `compiled_code` as exact bytes; whitespace-only agreement is reported separately. "
             "Source alignment distinguishes exact bytes, one trailing LF, other strip-only agreement, and differences. "
             "A dbt manifest checksum can hash normalized `raw_code`; it is checked against both raw_code and "
             "the pinned blob without assuming it is a hash of source file bytes. "
             "Manifest generation is a distinct build event without an attested commit. "
             "A MODEL artifact pass does **not** establish metric-expression lineage or semantic equivalence.", "",
             "| Repository | Commit matches | Project / dbt | Models | Pinned blobs | Compiled exact | "
             "Raw exact / +LF / strip | Checksum = blob / raw | Mapping review | Node review |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for case in report["cases"]:
        c = case["coverage"]
        m = case.get("manifest_metadata", {})
        lines.append(f"| `{case['repo_root']}` | {case['checked_out_commit_matches_pin']} | "
                     f"`{m.get('project_name')}` / `{m.get('dbt_version')}` | "
                     f"{c['models_enumerated']} | {c.get('pinned_source_blobs_read', 0)} | "
                     f"{c.get('compiled_files_exact_manifest_code', 0)} | "
                     f"{c.get('manifest_raw_code_exact_pinned_blob', 0)} / "
                     f"{c.get('manifest_raw_code_one_trailing_lf_only_pinned_blob', 0)} / "
                     f"{c.get('manifest_raw_code_strip_only_pinned_blob', 0)} | "
                     f"{c.get('manifest_source_checksums_equal_pinned_blob', 0)} / "
                     f"{c.get('manifest_source_checksums_equal_raw_code', 0)} | "
                     f"{c.get('source_mapping_needs_review', 0)} | {c.get('needs_review', 0)} |")
    lines += ["", "## Review reasons", ""]
    for case in report["cases"]:
        counts = Counter(reason for node in case["nodes"] for reason in node["reasons"])
        lines += [f"### `{case['repo_root']}`", "",
                  f"Pinned commit: `{case['expected_commit']}`; manifest SHA-256: "
                  f"`{case.get('manifest_file', {}).get('sha256', 'unavailable')}`. "
                  f"Manifest generated at `{case.get('build_event', {}).get('generated_at', 'unknown')}` "
                  "(a separate, unauthenticated build event).", ""]
        if case["reasons"]:
            lines.append("Case-level: " + ", ".join(f"`{x}`" for x in case["reasons"]) + ".")
        for reason, count in sorted(counts.items()):
            lines.append(f"- `{reason}`: {count} model(s).")
        if not counts:
            lines.append("- No node-level check failures.")
        lines.append("")
    lines += ["No newly selected or held-out repository source was read. "
              "See the JSON report for every MODEL node, its paths, artifact hashes, "
              "comparison status and review reasons.", ""]
    return ("\n".join(lines)).encode("utf-8")


def self_test() -> None:
    """Ephemeral tracked model: exact, compiled tamper, unsafe path and checksum tamper."""
    with tempfile.TemporaryDirectory(prefix="dbt-model-provenance-") as temp:
        repo = Path(temp) / "repo"
        (repo / "models").mkdir(parents=True)
        (repo / "target/compiled/demo/models").mkdir(parents=True)
        (repo / "dbt_project.yml").write_text("name: 'demo'\n", encoding="utf-8")
        source = b"select 1 as amount\n"
        compiled = b"select 1 as amount\n"
        (repo / "models/model.sql").write_bytes(source)
        for cmd in (("init", "-q"), ("add", "dbt_project.yml", "models/model.sql"),
                    ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                     "commit", "-qm", "test")):
            if git(repo, *cmd).returncode:
                raise AssertionError("fixture git creation failed")
        commit = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
        compiled_path = repo / "target/compiled/demo/models/model.sql"
        compiled_path.write_bytes(compiled)
        model = {"unique_id": "model.demo.model", "resource_type": "model", "language": "sql",
                 "package_name": "demo", "compiled": True, "original_file_path": "models/model.sql",
                 "compiled_path": "target/compiled/demo/models/model.sql", "raw_code": source.decode(),
                 "checksum": {"name": "sha256", "checksum": sha256(source)},
                 "compiled_code": compiled.decode()}
        manifest_path = repo / "target/manifest.json"
        def case() -> dict:
            manifest_path.write_text(json.dumps({"metadata": {
                "project_name": "demo", "dbt_version": "1.11.6", "dbt_schema_version": "v12",
                "generated_at": "2026-09-28T00:00:00Z", "invocation_id": "fixture"},
                "nodes": {model["unique_id"]: model}}), encoding="utf-8")
            return validate_case(str(repo), "target/manifest.json", commit, "demo", "1.11.6")
        assert case()["coverage"]["model_artifact_checks_pass"] == 1
        model["raw_code"] = source.decode().removesuffix("\n")
        model["checksum"]["checksum"] = sha256(model["raw_code"].encode())
        aligned = case()["nodes"][0]
        assert aligned["status"] == "model_artifact_checks_pass"
        assert aligned["source_mapping_alignment"] == "one_trailing_lf_only"
        assert aligned["manifest_source_checksum"]["versus_pinned_blob"] == "different"
        compiled_path.write_bytes(b"select 2 as amount\n")
        assert "manifest_compiled_code_different_vs_file" in case()["nodes"][0]["reasons"]
        compiled_path.write_bytes(compiled + b"\n")
        assert case()["nodes"][0]["compiled_file_vs_manifest_compiled_code"] == "one_trailing_lf_only"
        compiled_path.write_bytes(b" \n" + compiled + b"\n")
        assert case()["nodes"][0]["compiled_file_vs_manifest_compiled_code"] == "strip_only"
        compiled_path.write_bytes(compiled)
        model["raw_code"] = " " + source.decode().removesuffix("\n")
        model["checksum"]["checksum"] = sha256(model["raw_code"].encode())
        assert case()["nodes"][0]["source_mapping_alignment"] == "needs_review"
        model["raw_code"] = source.decode().removesuffix("\n")
        model["checksum"]["checksum"] = sha256(model["raw_code"].encode())
        model["compiled_path"] = "../../outside.sql"
        assert "compiled_invalid_or_escaping_relative_path" in case()["nodes"][0]["reasons"]
        model["compiled_path"] = "target/compiled/demo/models/model.sql"
        model["checksum"]["checksum"] = "0" * 64
        assert "manifest_source_checksum_different_vs_raw_code" in case()["nodes"][0]["reasons"]
        model["checksum"]["checksum"] = sha256(model["raw_code"].encode())
        (repo / "models/model.sql").write_bytes(b"select 9 as amount\n")
        assert "working_source_different_vs_pinned_blob" in case()["nodes"][0]["reasons"]
        assert case()["nodes"][0]["pinned_source"]["sha256"] == sha256(source)
    print("OK: exact and +LF mappings, compiled tamper, strip-only, unsafe path, checksum and mutable source controls")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", nargs=5, action="append", metavar=("REPO", "MANIFEST_REL", "FULL_COMMIT", "PROJECT", "DBT_VERSION"),
                        help="Repeat for each already inspected development project")
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD)
    parser.add_argument("--check", action="store_true", help="Compare reports without writing")
    parser.add_argument("--self-test", action="store_true", help="Run ephemeral controlled boundaries")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        if not args.case:
            return 0
    if not args.case:
        parser.error("provide one or more --case arguments, or --self-test")
    report = make_report(args.case)
    json_bytes = (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    md_bytes = render_md(report)
    if args.check:
        for path, expected in ((args.json_output, json_bytes), (args.md_output, md_bytes)):
            if not path.is_file() or path.read_bytes() != expected:
                print(f"FAIL: stale or missing report: {path}", file=sys.stderr)
                return 1
        print("OK: both provenance reports exactly match regenerated bytes (read-only)")
    else:
        args.json_output.write_bytes(json_bytes)
        args.md_output.write_bytes(md_bytes)
        print(f"Wrote {args.json_output} and {args.md_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
