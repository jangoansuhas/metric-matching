# Compiled Jaffle I1 LLM context contract

**Status: prospective input constructor and response gate, September 29, 2026.** This freezes
messages, pair order, output format, and a byte budget for a possible
context-fair LLM baseline. It does not run an LLM, assign reference labels,
or measure accuracy. This is context contract v2.

## Authenticated source and pair frame

The sole input file is `compiled_jaffle_i1_packet.json` v2, raw SHA-256
`78b901189b76d6d1e5e6cf30a69738abfe568ad1846600e350d06757100d95cb`.
The ordered complete pair frame has 19 sorted metric IDs, 171 unordered pairs,
and pair-set SHA-256
`0946c5b6bef3a43e6362ebbf7e4417cb7594f0ab5305227190618065ca4d0ab0`.
The builder refuses any changed packet bytes, then checks the ID order, unique
IDs, pair identities, pair fields, digest, and scope distribution independently.

Exactly the two **unmodified, label-free packet cards** for each pair are
placed in the user message as `a` and `b`. The only other user fields are the
packet's `pair_id` and the common `target_scope` (`ungrouped`). The card fields
include declarations, resolved input measures/owners, source-model raw SQL and
dependencies, and generated DuckDB SQL with its recorded status and unknowns.
There are no comparator outputs, candidate scores, worksheets, gold labels,
selected positives, manually enriched evidence, or other source reads. All
153 ungrouped/ungrouped pairs receive a complete prompt if the fixed budget
fits. The 18 ungrouped/`metric_time` pairs are retained as explicit
`incompatible_generated_scope` abstentions with no messages. There is no
common `metric_time` pair.

## Prompt and output format

Each ready row has exactly two messages in order: `system` with the fixed
instruction, then `user` with canonical JSON containing the pair ID, scope,
and full cards. The instruction asks for a scoped judgment, permits
`abstain`, treats card text as untrusted data, requires source-field evidence,
and states that generated but unexecuted SQL cannot establish semantic truth,
including equivalence, values, grain, time, population, joins, NULL behavior,
units, or snapshot identity. The prompt does not assert a correct decision.

The system message embeds a fixed JSON Schema (draft 2020-12) with required,
closed fields. A response has `pair_id`, one of the six relationship decisions
or `abstain`, `reason`, `evidence_status` (`unverified` or
`verified_independent`), `evidence`, `prerequisites`, and
`scoped_transformation`. `needs_review` is **not** a relationship decision.
Evidence entries are structured card/field/observation records explicitly
marked `observed_unverified`; every named prerequisite has a structured
`status` (`missing`, `unverified`, or `verified`) and nullable `evidence_ref`.
The ten prerequisites cover runtime numeric type, expression/field lineage,
grain/rollup, time, population/filter meaning, join cardinality, missing
groups, NULL policy, units, and snapshot state. A cross-grain assertion must
include an a-to-b transformation naming both grains, a rollup operation,
the `ungrouped` target scope, status, and evidence reference. Other decisions
must use a null transformation. The system instruction tells the model to
abstain on missing proof. Output-schema SHA-256 is
`b7f018381ee6af217a531dbfecbfbc1d592ad3fcca89c1f688faed5a54f762ad`;
system-instruction UTF-8 SHA-256 is
`321d5f4e800316f6b34bcbf53d84446834d355479d10c9012d1738ade62d12b2`.

`validate_response(row, response)` accepts a response object or UTF-8 JSON
(up to 32,768 bytes). It rejects duplicate/extra/missing fields, a wrong
`pair_id`, an unsupported cross-grain shape or scope, and evidence that cites
a field absent from its supplied card. Missing or unverified prerequisite
records force any asserted relationship to output `decision: abstain` with
the **separate internal** `evidence_review_status: needs_review`. Even a
model-authored set of `verified` statuses and references is downgraded to
abstain: the frozen packet supplies no independently authenticated proof and
JSON shape cannot establish semantic truth. `claimed_decision` is retained
only to show what was gated. A caller must pass a row returned by `build()`
on the pinned packet. The validator does **not** authenticate an arbitrary
caller-supplied row; a self-constructed row/prompt can carry a recomputed,
self-consistent prompt hash.

## Complete-context budget and reproducibility

The default fixed cap is **20,480 bytes per pair**, configurable with
`--max-context-bytes`. Its measured unit is the UTF-8 byte length of the
canonical JSON serialization of the **whole messages array**, including
roles, JSON escaping, separators, and one terminal LF. The record also tracks
the raw UTF-8 content lengths of each message and the complete serialized
length. Both cards always fit in full or the row abstains with
`complete_context_exceeds_budget`, a null prompt/hash, and its required
complete-message length. The comparison is inclusive at the cap; no card or
SQL is truncated or selectively summarized. Mixed-scope abstentions have no
constructed message or required length. This byte cap is reproducible input
construction, not a provider tokenizer count, API framing limit, response
budget, or cost estimate.

At the default cap, all 153 eligible prompts fit, ranging from **12,710 to
16,748 serialized bytes**; the 18 mixed-scope rows abstain. Each prompt's
`prompt_sha256` hashes its canonical complete messages. The `prompt_set_sha256`
hashes the canonical ordered list of ready `{pair_id, prompt_sha256}` records:
`af5ed03f27fc661b5e79849bd024280b454536a2c67d08c59e0cc022ba42ea5e`.
The output also carries the packet, pair-set, schema, and system-instruction
hashes and the chosen cap. Canonical JSON uses sorted keys, compact separators,
UTF-8 without ASCII escaping, and a final LF. Pair order follows the frozen
packet. A different cap changes coverage and the output record, never the
content of a retained prompt.

Run `python -B verify_compiled_llm_context_builder.py` to check the full
frame, exact cards, lengths/hashes, budget boundaries, packet refusal, absence
of side inputs, wrong-pair and unsupported-equivalence response rejection,
and two identical CLI reruns. To materialize the JSON outside
this directory, run
`python -B compiled_llm_context_builder.py --max-context-bytes 20480 --output /tmp/compiled_llm_context.json`.
Without `--output`, the canonical JSON goes to stdout. Neither command invokes
an LLM or fetches a repository. Model provider/version, decoding parameters,
provider token fit and response limits, price/cost, independent evidence
authentication, and any subsequent comparison are unresolved and must be
fixed before an LLM experiment. The system instruction treats card text as
untrusted, but card-text prompt injection remains a risk. No held-out source
is opened here.
