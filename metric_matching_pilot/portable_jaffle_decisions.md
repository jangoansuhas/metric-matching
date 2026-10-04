# Portable source decision probe (development only)

Input SHA-256 `ab52ee843d139dd5dccde3dc04c63dddac6a8e8a4a276f4f5cb465a27dfdf5b6`; 23 source cards and every one of their 253 unordered pairs.
No labels, built rows or held-out source are inputs. A candidate is a review hypothesis; all outcomes require domain-human review.

| Method | Candidate decisions | Abstain | Pairs with missing decisive evidence |
| --- | --- | ---: | ---: |
| `normalized_sql_lineage_baseline` | none | 253 | 253 |
| `constraint_aware_full_context_v2` | none | 253 | 253 |
| `proposed_conditional_explanation` | none | 253 | 253 |

Cards missing one or more required source fields: 23/23.
The complete card/field list and every method decision appear in JSON. Missing period grouping, grain, source relation or value expression forces an abstention; unknown NULL, units, time and row-membership semantics remain review conditions.

This bridge calls the frozen development decision functions and verifies a complete pair universe. It does not compile dbt, resolve YAML filters/model lineage, run Snowflake, or establish human gold. If source fields are absent, candidate coverage is a measurement of this bounded adapter rather than method accuracy.
