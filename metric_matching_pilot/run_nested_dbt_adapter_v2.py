#!/usr/bin/env python3
"""Version 2 compiled-metric provenance adapter with an explicit dbt project subdirectory.

This is a separately versioned coverage tool. Version 1 is unchanged. The subdirectory
is fixed from source-screen evidence, not chosen by parse success or metric output.

For one repo + commit:
  1. verify the commit and export it with `git archive` into a fresh directory;
  2. write a local DuckDB profile (no credentials, no remote warehouse);
  3. run `dbt deps` and `dbt parse --no-partial-parse` under a scrubbed environment;
  4. for every metric in the fresh semantic manifest, record the declared binding chain
     (metric -> input measures -> semantic model -> dbt model) from the fresh artifacts,
     plus text-located YAML line spans;
  5. run `mf query --metrics <m> --explain` (retrying with `--group-by metric_time` on failure)
     and save the generated SQL;
  6. write provenance.json / provenance.csv, logs and SHA256SUMS (excluding itself).

Limitations inherited from v1: YAML line spans are text located for top-level
legacy metrics; model-colocated spans may be null. Manifest resources are joined
by name and must be checked for ambiguity before making pair decisions. A
successful `--explain` is SQL-generation coverage, not value execution.

Usage:
  run_nested_dbt_adapter_v2.py --repo /path/to/clone --commit <sha> \
    --project-subdir dbt --source-inventory /path/to/frozen_inventory.json \
    --out /path/to/new_dir --venv /path/to/venv

The inventory is JSON: {"commit": "<40-hex>", "project_subdir": "dbt",
"declarations": [{"id": "<stable source ID>", "name": "<metric>",
"file": "dbt/models/path.yml"}, ...]}. `file` is repository-root relative.
"""
import argparse, csv, hashlib, json, os, re, shutil, subprocess, sys, time, zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def checked_subdir(value):
    """Accept a named, relative project path; a sole '.' means the archive root."""
    if value == ".":
        return Path(".")
    if not value or value.startswith("/") or "\\" in value:
        raise ValueError("project-subdir must be a relative POSIX directory or '.'")
    parts = value.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ValueError("project-subdir cannot contain empty, dot, or parent components")
    return Path(*PurePosixPath(value).parts)


ANSI = re.compile(r"\x1b\[[0-9;]*m")


class Runner:
    """Runs commands with `env -i`-equivalent environment and logs everything."""

    def __init__(self, out, venv):
        self.out, self.logs = out, out / "logs"
        self.logs.mkdir(parents=True, exist_ok=True)
        (out / "home").mkdir(exist_ok=True)
        self.env = {
            "HOME": str(out / "home"),
            "PATH": f"{venv}/bin:/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "DBT_PROFILES_DIR": str(out / "profiles"),
            "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
            "DO_NOT_TRACK": "1",
        }
        self.commands = []

    def run(self, tag, cmd, cwd, timeout=600):
        start_utc, t0 = utc(), time.time()
        try:
            p = subprocess.run(cmd, cwd=cwd, env=self.env, capture_output=True, text=True, timeout=timeout)
            rc, so, se = p.returncode, p.stdout, p.stderr
        except subprocess.TimeoutExpired as e:
            rc, so, se = "timeout", (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), f"TIMEOUT after {timeout}s"
        except OSError as e:
            rc, so, se = 127, "", f"Could not launch command: {e}"
        elapsed = round(time.time() - t0, 2)
        (self.logs / f"{tag}.stdout").write_text(so)
        (self.logs / f"{tag}.stderr").write_text(se)
        rec = {"tag": tag, "cmd": " ".join(cmd), "cwd": str(cwd), "exit": rc, "elapsed_s": elapsed, "start_utc": start_utc}
        (self.logs / f"{tag}.exit").write_text(json.dumps(rec) + "\n")
        self.commands.append(rec)
        return rc, ANSI.sub("", so), se


def yaml_span(path, top_key, name, parent=None):
    """Text-locate `- name: <name>` under top-level `top_key:` (optionally inside the list item
    `- name: <parent>` and its `measures:` key). Returns (start, end) 1-based lines or None.
    Heuristic: YAML line numbers are not in dbt artifacts, so this is labelled text-located."""
    if not path.exists():
        return None
    lines = path.read_text().splitlines()
    ind = lambda s: len(s) - len(s.lstrip(" "))

    def block(lo, hi, key_re):
        for i in range(lo, hi):
            if re.match(key_re, lines[i]):
                base = ind(lines[i])
                j = i + 1
                while j < hi and (not lines[j].strip() or lines[j].lstrip().startswith("#") or ind(lines[j]) > base
                                  or (ind(lines[j]) == base and lines[j].lstrip().startswith("- "))):
                    j += 1
                return i, j
        return None

    top = block(0, len(lines), rf"^{top_key}:\s*$")
    if not top:
        return None
    lo, hi = top
    if parent:
        item = find_item(lines, lo + 1, hi, parent)
        if not item:
            return None
        mb = block(item[0], item[1], r"^\s*measures:\s*$")
        if not mb:
            return None
        lo, hi = mb
    found = find_item(lines, lo + 1, hi, name)
    if not found:
        return None
    s, e = found
    while e - 1 > s and (not lines[e - 1].strip() or lines[e - 1].lstrip().startswith("#")):
        e -= 1
    return s + 1, e


def find_item(lines, lo, hi, name):
    ind = lambda s: len(s) - len(s.lstrip(" "))
    # Only the immediate list level is eligible. A nested input-metric reference
    # can have the same name as another top-level declaration.
    item_indents = [ind(lines[i]) for i in range(lo, hi)
                    if re.match(r"^\s*-\s*name:\s*", lines[i])]
    if not item_indents:
        return None
    item_indent = min(item_indents)
    for i in range(lo, hi):
        m = re.match(rf"^(\s*)-\s*name:\s*['\"]?{re.escape(name)}['\"]?\s*$", lines[i])
        if m and ind(lines[i]) == item_indent:
            base = ind(lines[i])
            j = i + 1
            while j < hi and not (lines[j].strip() and not lines[j].lstrip().startswith("#") and
                                  (ind(lines[j]) < base or (ind(lines[j]) == base and lines[j].lstrip().startswith("- ")))):
                j += 1
            return i, j
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--venv", required=True)
    ap.add_argument("--project-subdir", default=".", help="screen-verified relative path to dbt_project.yml directory")
    ap.add_argument("--source-inventory", required=True, help="frozen, independently checked source-declaration inventory JSON")
    a = ap.parse_args()
    if not re.fullmatch(r"[0-9a-fA-F]{40}", a.commit):
        ap.error("--commit must be the complete, pinned 40-hex commit SHA")
    a.commit = a.commit.lower()
    try:
        subdir = checked_subdir(a.project_subdir)
    except ValueError as e:
        ap.error(str(e))
    try:
        inventory_path = Path(a.source_inventory).resolve(strict=True)
        inventory = json.loads(inventory_path.read_text())
        declarations = inventory["declarations"]
        if inventory["commit"].lower() != a.commit or inventory["project_subdir"] != str(subdir):
            raise ValueError("inventory commit or project subdirectory differs from invocation")
        if not isinstance(declarations, list) or not declarations:
            raise ValueError("inventory must contain at least one declaration")
        ids = [d["id"] for d in declarations]
        if len(set(ids)) != len(ids) or any(
                not all(isinstance(d[k], str) and d[k] for k in ("id", "name", "file"))
                for d in declarations):
            raise ValueError("source declarations need distinct IDs and nonempty name/file")
        for d in declarations:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", d["name"]):
                raise ValueError("metric name must be a safe dbt identifier")
            path = PurePosixPath(d["file"])
            if path.is_absolute() or any(p in ("", ".", "..") for p in d["file"].split("/")):
                raise ValueError("inventory file path must be a clean repository-relative path")
            if subdir != Path(".") and not Path(*path.parts).is_relative_to(subdir):
                raise ValueError("inventory file lies outside the selected dbt project")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as e:
        ap.error(f"invalid --source-inventory: {e}")
    a.repo = str(Path(a.repo).resolve())
    a.venv = str(Path(a.venv).resolve())
    out = Path(a.out).resolve()
    if out.exists():
        sys.exit(f"--out {out} exists; use a fresh directory")
    out.mkdir(parents=True)
    proj = out / "project"
    R = Runner(out, a.venv)
    meta = {"run_start_utc": utc(), "repo": a.repo, "commit": a.commit,
            "project_subdir": str(subdir), "adapter_script_sha256": sha256(__file__),
            "source_inventory_sha256": sha256(inventory_path),
            "source_declaration_count": len(declarations),
            "source_declarations": declarations}

    # 1. verify commit and export
    t = subprocess.run(["git", "-C", a.repo, "cat-file", "-t", a.commit], capture_output=True, text=True)
    if t.stdout.strip() != "commit":
        (out / "FAILED.txt").write_text(f"commit {a.commit} not found in {a.repo}: {t.stderr}")
        sys.exit("commit not found; stopping")
    resolved = subprocess.run(["git", "-C", a.repo, "rev-parse", "--verify", f"{a.commit}^{{commit}}"],
                              capture_output=True, text=True)
    if resolved.returncode != 0 or resolved.stdout.strip().lower() != a.commit:
        (out / "FAILED.txt").write_text("pinned commit did not resolve exactly\n")
        sys.exit("pinned commit mismatch; stopping")
    meta["remote_url"] = subprocess.run(["git", "-C", a.repo, "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
    proj.mkdir()
    archive_cmd = ["git", "-C", a.repo, "archive", "--format=tar", a.commit]
    tar = subprocess.run(archive_cmd, capture_output=True, check=True).stdout
    meta["archive_tar_sha256"] = hashlib.sha256(tar).hexdigest()
    subprocess.run(["tar", "-x", "-C", str(proj)], input=tar, check=True)
    listing = subprocess.run(["tar", "-t"], input=tar, capture_output=True, check=True).stdout.decode()
    (R.logs / "git_archive_filelist.txt").write_text(listing)
    (R.logs / "git_archive.exit").write_text(json.dumps({
        "cmd": " ".join(archive_cmd) + f" | tar -x -C {proj}", "exit": 0, "start_utc": utc(),
        "tar_sha256": meta["archive_tar_sha256"], "tar_entries": len(listing.splitlines())}) + "\n")
    inputs = out / "inputs"
    inputs.mkdir()
    shutil.copy(inventory_path, inputs / "source_inventory.json")
    project_dir = proj / subdir
    component = project_dir
    symlinked_subdir = False
    while component != proj:
        symlinked_subdir |= component.is_symlink()
        component = component.parent
    if not project_dir.resolve().is_relative_to(proj.resolve()) or symlinked_subdir:
        meta["failure_stage"] = "project path escapes archive or uses symlink"
        finish(out, meta, R, [], a)
        sys.exit(meta["failure_stage"])
    if not (project_dir / "dbt_project.yml").is_file() or (project_dir / "dbt_project.yml").is_symlink():
        meta["failure_stage"] = "screen-verified dbt_project.yml missing at project-subdir"
        finish(out, meta, R, [], a)
        sys.exit(meta["failure_stage"])
    for d in declarations:
        source_file = proj / d["file"]
        if not source_file.resolve().is_relative_to(project_dir.resolve()) or not source_file.is_file() or source_file.is_symlink():
            meta["failure_stage"] = f"source inventory file missing or outside project: {d['file']}"
            finish(out, meta, R, [], a)
            sys.exit(meta["failure_stage"])
    meta["source_files_checked"] = True
    meta["export_had_target_dir"] = (project_dir / "target").exists()
    # Remove archived build output in this *fresh export*; a parse failure must not
    # be mistaken for successful reuse of a tracked target/semantic_manifest.json.
    if (project_dir / "target").is_symlink():
        (project_dir / "target").unlink()
    elif (project_dir / "target").exists():
        shutil.rmtree(project_dir / "target")
    meta["archived_target_removed_before_parse"] = meta["export_had_target_dir"]
    # dbt v1.12 supports this override; point dbt and local MetricFlow at the
    # same fresh conventional target even if dbt_project.yml chooses another.
    R.env["DBT_ENGINE_TARGET_PATH"] = str(project_dir / "target")
    for f in ("dbt_project.yml", "packages.yml", "package-lock.yml", "dependencies.yml"):
        if (project_dir / f).exists():
            shutil.copy(project_dir / f, inputs / f"{f}.original")
            meta[f"sha256_{f}"] = sha256(project_dir / f)

    # 2. local DuckDB profile named after the project's `profile:` key
    m = re.search(r"^profile:\s*['\"]?([\w-]+)", (project_dir / "dbt_project.yml").read_text(), re.M)
    profile = m.group(1) if m else "default"
    (out / "profiles").mkdir()
    (out / "profiles" / "profiles.yml").write_text(
        f"{profile}:\n  target: dev\n  outputs:\n    dev:\n      type: duckdb\n      path: {out}/dev.duckdb\n      threads: 1\n")
    shutil.copy(out / "profiles" / "profiles.yml", inputs / "profiles.yml")
    meta["profile_name"] = profile
    meta["clean_env"] = R.env

    # environment record
    R.run("00_python_version", [f"{a.venv}/bin/python", "--version"], out)
    R.run("00_dbt_version", ["dbt", "--version"], out)
    R.run("00_mf_version", ["mf", "--version"], out)
    R.run("00_pip_freeze", [f"{a.venv}/bin/python", "-m", "pip", "freeze"], out)
    meta["os"] = Path("/etc/os-release").read_text().splitlines()[0] if Path("/etc/os-release").exists() else "unknown"
    meta["uname"] = " ".join(os.uname())

    dbt_args = ["--project-dir", str(project_dir), "--profiles-dir", str(out / "profiles")]
    # 3. deps + parse
    has_deps = any((project_dir / f).exists() for f in ("packages.yml", "dependencies.yml"))
    if has_deps:
        rc, so, _ = R.run("01_dbt_deps", ["dbt", "deps", *dbt_args], out, timeout=600)
        meta["deps_exit"] = rc
        if (project_dir / "package-lock.yml").exists():
            shutil.copy(project_dir / "package-lock.yml", inputs / "package-lock.yml.after_deps")
            meta["sha256_package-lock.yml_after_deps"] = sha256(project_dir / "package-lock.yml")
        meta["deps_installed_lines"] = re.findall(r"Install(?:ing|ed from) [^\n]+", so)
        if rc != 0:
            meta["failure_stage"] = "dbt deps"
            finish(out, meta, R, [], a)
            sys.exit("dbt deps failed; inspect run_metadata.json and logs")
    rc, so, se = R.run("02_dbt_parse", ["dbt", "parse", "--no-partial-parse",
                                     "--target-path", str(project_dir / "target"), *dbt_args], out, timeout=600)
    meta["parse_exit"] = rc
    arts = out / "manifests"
    arts.mkdir()
    if rc != 0 or not all((project_dir / "target" / f).is_file() for f in ("manifest.json", "semantic_manifest.json")):
        meta["failure_stage"] = "dbt parse"
        finish(out, meta, R, [], a)
        sys.exit("dbt parse failed; inspect run_metadata.json and logs")
    for f in ("manifest.json", "semantic_manifest.json"):
        shutil.copy(project_dir / "target" / f, arts / f)
        meta[f"sha256_{f}_after_parse"] = sha256(arts / f)
    man = json.load(open(arts / "manifest.json"))
    sm = json.load(open(arts / "semantic_manifest.json"))
    meta["manifest_metadata"] = {k: man["metadata"].get(k) for k in ("dbt_version", "generated_at", "invocation_id", "adapter_type", "project_name")}

    # 4. binding chain per metric
    measure_owners = {}
    for s in sm["semantic_models"]:
        for me in s.get("measures", []):
            measure_owners.setdefault(me["name"], []).append((s, me))
    project_name = man["metadata"]["project_name"]
    man_metrics = list(man["metrics"].values())
    man_sms = list(man["semantic_models"].values())
    sqldir = out / "generated_sql"
    sqldir.mkdir()
    rows = []
    for i, source in enumerate(declarations):
        name = source["name"]
        source_file = str(Path(source["file"]).relative_to(subdir))
        duplicate_source_location = sum(d["name"] == name and d["file"] == source["file"]
                                        for d in declarations) != 1
        semantic_matches = [m for m in sm["metrics"] if m["name"] == name]
        all_manifest_matches = [m for m in man_metrics if m["name"] == name]
        manifest_matches = [m for m in all_manifest_matches if m.get("package_name") == project_name
                            and m.get("original_file_path") == source_file]
        if duplicate_source_location or len(semantic_matches) != 1 or len(manifest_matches) != 1 or len(all_manifest_matches) != 1:
            rows.append({"source_id": source["id"], "metric": name, "declared_file": source_file,
                         "type": None, "declared_span_text_located": None,
                         "manifest_depends_on": [], "input_measures": [], "explain_attempts": [],
                         "binding_status": "ambiguous_or_missing", "compiled_sql_status": "not_attempted",
                         "candidate_counts": {"duplicate_source_location": duplicate_source_location,
                                              "semantic": len(semantic_matches),
                                              "manifest_owned_at_source": len(manifest_matches),
                                              "manifest_any_package": len(all_manifest_matches)}})
            continue
        met, mn = semantic_matches[0], manifest_matches[0]
        tp = met["type_params"]
        decl_file = mn["original_file_path"]
        span = yaml_span(project_dir / decl_file, "metrics", name) if decl_file else None
        measures = []
        for im in tp.get("input_measures") or []:
            owners = measure_owners.get(im["name"], [])
            entry = {"measure": im["name"], "filter": im.get("filter"), "fill_nulls_with": im.get("fill_nulls_with"),
                     "join_to_timespine": im.get("join_to_timespine"), "owner_count": len(owners), "owners": []}
            for s, me in owners:
                candidates = [v for v in man_sms if v["name"] == s["name"]]
                verified = len(candidates) == 1 and candidates[0].get("package_name") == project_name
                msn = candidates[0] if verified else {}
                f = msn.get("original_file_path")
                entry["owners"].append({
                    "semantic_model": s["name"], "semantic_model_file": f,
                    "manifest_owner_status": "unique_project_owned" if verified else "ambiguous_or_dependency_owned",
                    "semantic_model_span": yaml_span(project_dir / f, "semantic_models", s["name"]) if f else None,
                    "measure_span": yaml_span(project_dir / f, "semantic_models", me["name"], parent=s["name"]) if f else None,
                    "agg": me.get("agg"), "expr": me.get("expr"), "agg_time_dimension": me.get("agg_time_dimension") or (s.get("defaults") or {}).get("agg_time_dimension"),
                    "non_additive_dimension": me.get("non_additive_dimension"),
                    "node_relation": (s.get("node_relation") or {}).get("relation_name"),
                    "model_node": (msn.get("depends_on") or {}).get("nodes"),
                })
            measures.append(entry)
        rec = {
            "source_id": source["id"], "metric": name, "type": met["type"], "description": met.get("description"),
            "declared_file": decl_file, "declared_span_text_located": span,
            "manifest_metric_unique_id": mn["unique_id"],
            "binding_status": "verified" if (measures or not tp.get("metrics")) and all(
                m["owner_count"] == 1 and all(o["manifest_owner_status"] == "unique_project_owned" for o in m["owners"])
                for m in measures) else "needs_review",
            "metric_filter": met.get("filter"), "type_params_expr": tp.get("expr"),
            "numerator": (tp.get("numerator") or {}).get("name") if tp.get("numerator") else None,
            "denominator": (tp.get("denominator") or {}).get("name") if tp.get("denominator") else None,
            "input_metrics": [{"name": x["name"], "alias": x.get("alias"), "offset_window": x.get("offset_window"),
                               "filter": x.get("filter")} for x in tp.get("metrics") or []],
            "cumulative_type_params": tp.get("cumulative_type_params"),
            "manifest_depends_on": (mn.get("depends_on") or {}).get("nodes"),
            "input_measures": measures,
        }
        # 5. mf explain
        attempts = []
        for j, extra in enumerate(([], ["--group-by", "metric_time"])):
            tag = f"10_mf_explain_{i:02d}_{name}" + ("" if not extra else "_metric_time")
            rc, so, se = R.run(tag, ["mf", "query", "--metrics", name, *extra, "--explain"], project_dir, timeout=300)
            mm = re.search(r"^[ \t]*(SELECT|WITH)\b", so, re.I | re.M)
            ok = bool(mm) and rc == 0 and "ERROR" not in so[:mm.start()]
            att = {"group_by": extra[1] if extra else None, "exit": rc, "sql_found": bool(mm), "log_tag": tag}
            if ok:
                sqlf = sqldir / f"{name}{'' if not extra else '__metric_time'}.sql"
                sqlf.write_text(so[mm.start():].strip() + "\n")
                att["sql_file"] = str(sqlf.relative_to(out))
                att["sql_sha256"] = sha256(sqlf)
            else:
                err = [l for l in (so + "\n" + ANSI.sub("", se)).splitlines() if l.strip() and "Initiating" not in l]
                k = next((n for n, l in enumerate(err) if "ERROR" in l), max(len(err) - 8, 0))
                att["error_message"] = err[k:k + 10]
            attempts.append(att)
            if ok:
                break
        rec["explain_attempts"] = attempts
        rec["compiled_sql_status"] = ("verified_ungrouped" if attempts[0].get("sql_file")
                                      else "verified_metric_time_only" if len(attempts) > 1 and attempts[1].get("sql_file")
                                      else "failed")
        rows.append(rec)
    for f in ("manifest.json", "semantic_manifest.json"):
        meta[f"sha256_{f}_after_explain"] = sha256(project_dir / "target" / f)
    # warehouse inventory after explain: shows whether any relation was created or needed
    db = out / "dev.duckdb"
    meta["duckdb_exists_after_explain"] = db.exists()
    if db.exists():
        meta["duckdb_sha256"], meta["duckdb_bytes"] = sha256(db), db.stat().st_size
        R.run("20_duckdb_inventory", [f"{a.venv}/bin/python", "-c",
              "import duckdb,json,sys; c=duckdb.connect(sys.argv[1], read_only=True); "
              "print(json.dumps(c.execute('select table_catalog, table_schema, table_name, table_type "
              "from information_schema.tables order by 1,2,3').fetchall()))", str(db)], out)
    finish(out, meta, R, rows, a)


def finish(out, meta, R, rows, a):
    meta["run_end_utc"] = utc()
    meta["commands"] = R.commands
    (out / "run_metadata.json").write_text(json.dumps(meta, indent=1))
    (out / "provenance.json").write_text(json.dumps(rows, indent=1))
    with open(out / "provenance.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "type", "declared_file", "declared_lines", "input_measures", "owner_semantic_models",
                    "all_measures_single_owner", "manifest_depends_on", "compiled_sql_status", "sql_file", "sql_sha256"])
        for r in rows:
            ok = next((x for x in r["explain_attempts"] if x.get("sql_file")), {})
            w.writerow([r["metric"], r["type"], r["declared_file"],
                        "-".join(map(str, r["declared_span_text_located"])) if r["declared_span_text_located"] else "",
                        ";".join(m["measure"] for m in r["input_measures"]),
                        ";".join(sorted({o["semantic_model"] for m in r["input_measures"] for o in m["owners"]})),
                        all(m["owner_count"] == 1 for m in r["input_measures"]),
                        ";".join(r["manifest_depends_on"] or []), r["compiled_sql_status"],
                        ok.get("sql_file", ""), ok.get("sql_sha256", "")])
    # bundle: copy adapter script and write SHA256SUMS excluding itself
    shutil.copy(__file__, out / "inputs" / "run_nested_dbt_adapter_v2.py")
    for d in ("project/logs" if a.project_subdir == "." else f"project/{a.project_subdir}/logs",):
        if (out / d).exists():
            shutil.copytree(out / d, out / "logs" / "dbt_project_logs", dirs_exist_ok=True)
    include = ["run_metadata.json", "provenance.json", "provenance.csv", "inputs", "logs", "manifests", "generated_sql", "report.md", "dev.duckdb"]
    files = sorted(p for inc in include for p in ([out / inc] if (out / inc).is_file() else (out / inc).rglob("*"))
                   if p.is_file())
    sums = "".join(f"{sha256(p)}  ./{p.relative_to(out)}\n" for p in files)
    (out / "SHA256SUMS").write_text(sums)
    print(json.dumps({"out": str(out), "files": len(files)}))


if __name__ == "__main__":
    main()
