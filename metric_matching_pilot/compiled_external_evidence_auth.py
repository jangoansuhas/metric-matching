"""Authenticate signed assertions about supplemental I1 semantic evidence.

The trust anchors are supplied by the caller, separately from the packet and
claims: a known SHA256 digest of the exact packet bytes, an allowlist of
absolute local artifact roots, and a reviewer registry curated out of band.
Each registry entry pins an Ed25519 public key, a human or automated identity
type, and the producers from whom that reviewer is independent. A name,
timestamp, or ``verified_by`` inside a claim alone has no authority. Do not
derive the expected digest or registry from the claim, artifact, or packet.

``authenticate_semantic_evidence`` checks exact packet bytes, pair/card/SQL
bindings, local artifact bytes, and a signature over the entire claim. It
returns only authenticated signed assertions, not baseline card additions.
The signature authenticates who approved the assertion and its artifact digest;
it does not establish the assertion's semantic truth. Do not translate this
output into ``status=verified`` or pass it to the baseline as a semantic fact
without a separate content-verification process.

Each input record has exactly ``field``, ``value``, ``kind``, ``artifact``
(``root_id``, normalized relative ``locator``, ``sha256``), ``binding`` (from
``binding_for``), and ``provenance`` (``producer_id``, ``reviewer_id``,
``reviewer_type``, ``review_method``, ``reviewed_at``, and base64
``signature_ed25519``). The reviewer signs ``review_signing_payload(record)``.
The trusted registry maps reviewer IDs to ``public_key_ed25519`` (raw 32-byte
key), ``reviewer_type``, and ``independent_of_producers``. The only result
payload is ``authenticated_signed_assertions`` with the original signed
records, including their packet/pair/card/SQL bindings. Text fields accept
nonempty strings; join cardinality and the two policy fields have narrow
object schemas. Other shapes are unsupported and rejected, not interpreted.

Assumptions/limits: trusted packet digest custody, root custody, public-key
enrollment and reviewer independence are established outside this module.
The meaning of an execution log and the signed semantic claim's truth remain
unverified. A signed time is not trusted time, and a registry's human type does
not prove a human acted. This module does not guard against compromised keys or
malicious concurrent in-place file mutation. It binds the source commit string
but does not validate the Git object or certify the packet's origin. The
returned envelope is an in-process result, not a standalone signed document;
reauthenticate original records before trusting a stored copy. Requires
``cryptography`` for Ed25519.
"""

from __future__ import annotations

import base64
import binascii
from datetime import datetime
import hashlib
import json
import os
from pathlib import PurePosixPath
import re
import stat
from typing import Any, Mapping


SCHEMA_VERSION = "compiled_external_signed_assertions_v2"
MAX_PACKET_BYTES = 16 * 1024 * 1024
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
SEMANTIC_FIELDS = frozenset({
    "grain", "units", "snapshot_state", "join_cardinality",
    "missing_group_rule", "null_policy", "population", "time_rule", "time_zone",
})
TEXT_FIELDS = SEMANTIC_FIELDS - {"join_cardinality", "missing_group_rule", "null_policy"}
SCOPES = frozenset({"ungrouped", "metric_time"})
METHOD_FOR_KIND = {
    "independent_review": ("human", "manual_artifact_review"),
    "executed_constraint_check": ("automated", "automated_constraint_check"),
}
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
_ROOT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*\Z")
_ACTOR_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._@-]*\Z")
_SIGNING_DOMAIN = b"metric-matching-signed-assertion-v2\0"


class EvidenceRejected(ValueError):
    """No evidence envelope was authenticated."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise EvidenceRejected(reason)


def _keys(value: Any, expected: set[str], name: str) -> None:
    _require(isinstance(value, dict) and set(value) == expected,
             f"invalid {name} schema")


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise EvidenceRejected("non-JSON claim or packet value") from exc


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def _bad_constant(value: str) -> None:
    raise EvidenceRejected(f"non-JSON number: {value}")


def _checked_card(card: Any, metric_id: str, scope: str) -> str:
    """Check the baseline's required card shape and exact SQL bytes on either side."""
    required = {"metric_id", "sql_scope", "compiled_sql", "compiled_sql_sha256",
                "name", "type", "source_status", "numeric_eligibility_status",
                "manifest_depends_on", "input_measures", "source_models"}
    _require(isinstance(card, dict) and required <= set(card),
             "incomplete pair card structure")
    _require(card["metric_id"] == metric_id and card["sql_scope"] == scope,
             "pair card identity or scope mismatch")
    for key in ("name", "type", "source_status", "numeric_eligibility_status"):
        _require(type(card[key]) is str and bool(card[key].strip()),
                 f"pair card {key} missing or malformed")
    deps, measures, models = (card[key] for key in
                              ("manifest_depends_on", "input_measures", "source_models"))
    _require(type(deps) is list and all(type(d) is str and bool(d) for d in deps)
             and type(measures) is list and all(type(m) is dict for m in measures)
             and type(models) is list and all(type(m) is dict
                                             and type(m.get("node")) is str
                                             and bool(m["node"]) for m in models),
             "pair card lineage structure malformed")
    sql = card["compiled_sql"]
    _require(type(sql) is str and bool(sql), "pair card has no compiled SQL")
    try:
        sql_hash = _hash(sql.encode("utf-8"))
    except UnicodeError as exc:
        raise EvidenceRejected("compiled SQL is not UTF-8 encodable") from exc
    claimed_hash = card["compiled_sql_sha256"]
    _require(type(claimed_hash) is str and bool(_DIGEST.fullmatch(claimed_hash))
             and claimed_hash == sql_hash, "pair card compiled SQL hash mismatch")
    _require("semantic_prerequisite_verifications" not in card,
             "pair card already carries unauthenticated semantic assertions")
    return sql_hash


def _packet_context(packet_bytes: bytes, pair_id: str, metric_id: str,
                    expected_packet_sha256: str) -> tuple[dict[str, str], dict[str, Any]]:
    _require(isinstance(packet_bytes, bytes) and 0 < len(packet_bytes) <= MAX_PACKET_BYTES,
             "packet must be bounded exact JSON bytes")
    _require(isinstance(expected_packet_sha256, str)
             and bool(_DIGEST.fullmatch(expected_packet_sha256)),
             "expected packet SHA256 must be a pinned lowercase digest")
    packet_hash = _hash(packet_bytes)
    _require(packet_hash == expected_packet_sha256,
             "packet SHA256 mismatch against trusted digest")
    try:
        packet = json.loads(packet_bytes, object_pairs_hook=_unique_object,
                            parse_constant=_bad_constant)
    except (ValueError, UnicodeError) as exc:
        raise EvidenceRejected("invalid packet JSON") from exc
    _require(isinstance(packet, dict), "packet must be an object")
    version = packet.get("packet_version")
    _require(isinstance(version, str) and bool(version), "missing packet version")
    commit = packet.get("source_commit")
    if "source_commit" in packet:
        _require(isinstance(commit, str) and bool(_COMMIT.fullmatch(commit)),
                 "source commit string must be a full hash; Git object is not verified")
    _require(isinstance(pair_id, str) and bool(pair_id)
             and isinstance(metric_id, str) and bool(metric_id), "missing pair/card identity")
    pairs, cards = packet.get("pairs"), packet.get("cards")
    _require(isinstance(pairs, list) and isinstance(cards, list), "missing pairs/cards")
    selected_pairs = [p for p in pairs if isinstance(p, dict) and p.get("pair_id") == pair_id]
    _require(len(selected_pairs) == 1, "pair not unique in packet")
    pair = selected_pairs[0]
    _keys(pair, {"a", "b", "pair_id", "scope_compatible", "target_scope"}, "pair")
    a, b = pair.get("a"), pair.get("b")
    _require(type(a) is str and type(b) is str and bool(a) and bool(b)
             and "||" not in a and "||" not in b and a != b
             and pair_id == "||".join(sorted((a, b))) and metric_id in (a, b),
             "pair/card identity mismatch")
    scope = pair["target_scope"]
    _require(pair["scope_compatible"] is True and type(scope) is str
             and scope in SCOPES, "pair scope mismatch or unsupported")
    matching = {identity: [c for c in cards if isinstance(c, dict)
                           and c.get("metric_id") == identity] for identity in (a, b)}
    _require(all(len(matches) == 1 for matches in matching.values()),
             "pair cards missing or duplicated")
    hashes = {identity: _checked_card(matching[identity][0], identity, scope)
              for identity in (a, b)}
    card = matching[metric_id][0]
    other_id = b if metric_id == a else a
    binding = {
        "packet_sha256": packet_hash, "packet_version": version,
        "pair_id": pair_id, "pair_sha256": _hash(_canonical(pair)),
        "metric_id": metric_id, "card_sha256": _hash(_canonical(card)),
        "compiled_sql_sha256": hashes[metric_id],
        "paired_metric_id": other_id,
        "paired_card_sha256": _hash(_canonical(matching[other_id][0])),
        "paired_compiled_sql_sha256": hashes[other_id],
    }
    if commit is not None:
        binding["source_commit"] = commit
    return binding, card


def binding_for(packet_bytes: bytes, pair_id: str, metric_id: str, *,
                expected_packet_sha256: str) -> dict[str, str]:
    """Return claim binding after the pinned packet digest check; NOT evidence authentication."""
    return _packet_context(packet_bytes, pair_id, metric_id, expected_packet_sha256)[0]


def review_signing_payload(record: Mapping[str, Any]) -> bytes:
    """Domain-separated canonical bytes reviewed and signed by the reviewer.

    Excludes only ``provenance.signature_ed25519``. The reviewer must inspect
    the artifact and exact claim before signing; this function does not do so.
    """
    _require(isinstance(record, Mapping), "record must be a mapping")
    unsigned = dict(record)
    provenance = unsigned.get("provenance")
    _require(isinstance(provenance, Mapping), "missing reviewer provenance")
    unsigned["provenance"] = dict(provenance)
    unsigned["provenance"].pop("signature_ed25519", None)
    return _SIGNING_DOMAIN + _canonical(unsigned)


def _relative(locator: Any) -> list[str]:
    _require(isinstance(locator, str) and bool(locator) and "\\" not in locator
             and "\x00" not in locator and "%" not in locator and ":" not in locator,
             "unsafe artifact locator")
    parts = locator.split("/")
    _require(not locator.startswith("/") and all(p not in ("", ".", "..") for p in parts)
             and PurePosixPath(locator).as_posix() == locator,
             "artifact locator must be a normalized relative path")
    return parts


def _root_parts(root: Any) -> list[str]:
    try:
        path = os.fspath(root)
    except TypeError as exc:
        raise EvidenceRejected("artifact root is not a path") from exc
    _require(isinstance(path, str) and path.startswith("/") and path != "/"
             and "\\" not in path and "\x00" not in path,
             "allowlisted artifact root must be an absolute local directory")
    parts = path[1:].split("/")
    _require(all(part not in ("", ".", "..") for part in parts)
             and PurePosixPath(path).as_posix() == path,
             "artifact root must be normalized")
    return parts


def _artifact_digest(root: Any, locator: str) -> str:
    root_parts = _root_parts(root)
    parts = _relative(locator)
    _require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY"),
             "platform cannot reject symlinks safely")
    dir_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    file_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
    directory = None
    file_fd = None
    try:
        directory = os.open("/", dir_flags)
        for part in root_parts + parts[:-1]:
            next_fd = os.open(part, dir_flags, dir_fd=directory)
            os.close(directory)
            directory = next_fd
        file_fd = os.open(parts[-1], file_flags, dir_fd=directory)
        before = os.fstat(file_fd)
        _require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= MAX_ARTIFACT_BYTES,
                 "artifact must be a bounded nonempty regular file")
        digest = hashlib.sha256()
        count = 0
        while chunk := os.read(file_fd, 64 * 1024):
            count += len(chunk)
            _require(count <= MAX_ARTIFACT_BYTES, "artifact exceeds size limit")
            digest.update(chunk)
        after = os.fstat(file_fd)
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        _require(count == before.st_size and all(getattr(before, k) == getattr(after, k)
                                                 for k in fields),
                 "artifact changed during read")
        return digest.hexdigest()
    except OSError as exc:
        raise EvidenceRejected("artifact unavailable or unsafe") from exc
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if directory is not None:
            os.close(directory)


def _text(value: Any) -> bool:
    return (type(value) is str and 0 < len(value) <= 1024
            and value == value.strip()
            and not any(ord(char) < 32 or ord(char) == 127 for char in value)
            and value.casefold() not in {
                "unknown", "unverified", "not_certified", "not_applicable", "none",
            })


def _valid_semantic_value(field: str, value: Any) -> bool:
    """Validate shape only; no schema here establishes semantic correctness."""
    if field in TEXT_FIELDS:
        return _text(value)
    if field == "join_cardinality":
        return (type(value) is dict
                and set(value) == {"safe_for_comparison", "relationship"}
                and value["safe_for_comparison"] is True
                and type(value["relationship"]) is str
                and value["relationship"] in {
                    "no_join", "one_to_one", "many_to_one", "preaggregated_one_row",
                })
    if field in {"missing_group_rule", "null_policy"}:
        return type(value) is dict and set(value) == {"policy"} and _text(value["policy"])
    return False


def _verify_record(record: Any, binding: dict[str, str], card: dict[str, Any],
                   roots: Mapping[str, Any], reviewers: Mapping[str, Any]) -> dict[str, Any]:
    _keys(record, {"field", "value", "kind", "artifact", "binding", "provenance"}, "record")
    field = record["field"]
    _require(isinstance(field, str) and field in SEMANTIC_FIELDS, "unsupported semantic field")
    value = record["value"]
    _require(_valid_semantic_value(field, value), "unsupported semantic value shape")
    _require(card.get(field) is None or _canonical(card[field]) == _canonical(value),
             "semantic value conflicts with card")
    kind = record["kind"]
    _require(isinstance(kind, str) and kind in METHOD_FOR_KIND, "unsupported evidence kind")
    _require(type(record["binding"]) is dict and record["binding"] == binding,
             "packet/pair/card/SQL/commit binding mismatch")
    artifact = record["artifact"]
    _keys(artifact, {"root_id", "locator", "sha256"}, "artifact")
    root_id, expected_hash = artifact["root_id"], artifact["sha256"]
    _require(isinstance(root_id, str) and bool(_ROOT_ID.fullmatch(root_id))
             and root_id in roots
             and isinstance(expected_hash, str) and bool(_DIGEST.fullmatch(expected_hash))
             and expected_hash != binding["compiled_sql_sha256"],
             "artifact root/hash invalid or artifact is compiled SQL")
    actual_hash = _artifact_digest(roots[root_id], artifact["locator"])
    _require(actual_hash == expected_hash, "artifact SHA256 mismatch")

    provenance = record["provenance"]
    _keys(provenance, {"producer_id", "reviewer_id", "reviewer_type", "review_method",
                       "reviewed_at", "signature_ed25519"}, "provenance")
    producer, reviewer_id = provenance["producer_id"], provenance["reviewer_id"]
    _require(isinstance(producer, str) and bool(_ACTOR_ID.fullmatch(producer))
             and isinstance(reviewer_id, str) and bool(_ACTOR_ID.fullmatch(reviewer_id))
             and producer != reviewer_id, "self review or missing identities")
    _require(reviewer_id in reviewers, "reviewer is not independently trusted")
    trusted = reviewers[reviewer_id]
    _keys(trusted, {"public_key_ed25519", "reviewer_type", "independent_of_producers"},
          "trusted reviewer")
    independent = trusted["independent_of_producers"]
    _require(isinstance(independent, (set, frozenset, tuple, list))
             and producer in independent and reviewer_id not in independent,
             "reviewer independence not established by trusted registry")
    _require((provenance["reviewer_type"], provenance["review_method"])
             == METHOD_FOR_KIND[kind]
             and trusted["reviewer_type"] == provenance["reviewer_type"],
             "reviewer type or method mismatch")
    timestamp = provenance["reviewed_at"]
    _require(isinstance(timestamp, str) and bool(_UTC.fullmatch(timestamp)),
             "review timestamp must be UTC")
    try:
        datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise EvidenceRejected("invalid review timestamp") from exc
    key = trusted["public_key_ed25519"]
    _require(isinstance(key, bytes) and len(key) == 32, "invalid pinned reviewer key")
    signature_text = provenance["signature_ed25519"]
    _require(isinstance(signature_text, str), "missing reviewer signature")
    try:
        signature = base64.b64decode(signature_text, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise EvidenceRejected("invalid reviewer signature encoding") from exc
    _require(len(signature) == 64, "invalid reviewer signature length")
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:
        raise EvidenceRejected("Ed25519 verifier unavailable") from exc
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(signature, review_signing_payload(record))
    except (InvalidSignature, ValueError) as exc:
        raise EvidenceRejected("reviewer signature does not authenticate claim") from exc
    return json.loads(_canonical(record))


def authenticate_semantic_evidence(
    packet_bytes: bytes, pair_id: str, metric_id: str, records: list[dict[str, Any]],
    *, expected_packet_sha256: str, artifact_roots: Mapping[str, Any],
    trusted_reviewers: Mapping[str, Any],
) -> dict[str, Any]:
    """Return signed assertions with authenticated bindings or reject all.

    No returned field is a verified semantic fact or a baseline card overlay.
    The independent reviewer signature and artifact bytes are authenticated;
    semantic content needs a separate verification process.
    """
    _require(isinstance(artifact_roots, Mapping) and bool(artifact_roots)
             and isinstance(trusted_reviewers, Mapping) and bool(trusted_reviewers),
             "allowlisted roots and trusted reviewers are required")
    _require(type(records) is list and bool(records), "nonempty record list required")
    binding, card = _packet_context(packet_bytes, pair_id, metric_id,
                                    expected_packet_sha256)
    authenticated = [_verify_record(r, binding, card, artifact_roots, trusted_reviewers)
                     for r in records]
    fields = [entry["field"] for entry in authenticated]
    _require(len(fields) == len(set(fields)), "duplicate semantic field")
    return {"schema_version": SCHEMA_VERSION,
            "binding": binding,
            "authenticated_signed_assertions": authenticated}
