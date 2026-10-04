#!/usr/bin/env python3
"""Fail-closed, exact-chain probe for two pinned Jaffle conditional scopes.

Requires PyYAML, sqlglot and DuckDB. Only the selected packet pairs, their
measure declarations, order_items projection/join, staging classifier and raw
product source are checked. No real rows or held-out material are read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

import duckdb
import sqlglot
from sqlglot import exp
import yaml

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT / 'public_corpus/jaffle-shop-sidemantic/jaffle-shop'
BUNDLE = ROOT / 'metric_provenance_verification'
PACKET = ROOT / 'metric_matching_pilot/compiled_jaffle_i1_packet.json'
REPORT = Path(__file__).with_name('probe_flag_lineage_report.md')
PIN = '7be2c5838dbdeca8e915d4e46db70e910753d7f6'
PAIRS = (('food_revenue', 'revenue'), ('drink_revenue', 'revenue'))
YAML = 'models/marts/order_items.yml'
MART = 'models/marts/order_items.sql'
PRODUCTS = 'models/staging/stg_products.sql'
ITEMS = 'models/staging/stg_order_items.sql'
SOURCES = 'models/staging/__sources.yml'


class Unsupported(ValueError):
    pass


def check(condition, reason):
    if not condition:
        raise Unsupported(reason)


def one(values, reason):
    check(len(values) == 1, reason)
    return values[0]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_read(path):
    return json.loads(path.read_bytes())


def parse(sql, label):
    try:
        result = sqlglot.parse(sql, read='duckdb')
    except sqlglot.errors.ParseError as error:
        raise Unsupported(f'unsupported_SQL:{label}:{error}') from error
    check(len(result) == 1 and result[0] is not None, f'unsupported_SQL_statements:{label}')
    return result[0]


def relation(table):
    check(isinstance(table, exp.Table), f'unsupported_relation:{table}')
    return '.'.join(part.lower() for part in (table.catalog, table.db, table.name) if part)


def named_relation(name):
    query = parse(f'SELECT * FROM {name}', 'manifest relation')
    return relation(query.args['from_'].this)


def source(path, hashes, texts):
    check(path in (YAML, MART, PRODUCTS, ITEMS, SOURCES), f'unsupported_source_path:{path}')
    disk = (REPO / path).read_bytes()
    pinned = subprocess.run(['git', '-C', str(REPO), 'show', f'HEAD:{path}'],
                            capture_output=True, check=True).stdout
    check(disk == pinned, f'source_differs_from_Git_HEAD:{path}')
    hashes[f'public_corpus/jaffle-shop-sidemantic/jaffle-shop/{path}'] = digest(pinned)
    texts[path] = disk.decode('utf-8')
    return texts[path]


def where(text, path, needle):
    check(text.count(needle) == 1, f'source_span_not_unique:{path}:{needle}')
    start = text.index(needle)
    line = text.count('\n', 0, start) + 1
    end = line + needle.count('\n')
    return f'`{path}:{line}' + (f'-{end}' if end != line else '') + '`'


def model_sql(node_id, path, checkout, bundle, hashes, texts):
    a, b = checkout['nodes'][node_id], bundle['nodes'][node_id]
    check(a['original_file_path'] == b['original_file_path'] == path,
          f'model_source_path_mismatch:{node_id}')
    raw = source(path, hashes, texts)
    # Both manifests omit one final LF from raw_code for these three models.
    check(raw == a['raw_code'] + '\n' == b['raw_code'] + '\n',
          f'model_raw_code_differs_from_HEAD:{node_id}')
    compiled_path = f'target/compiled/jaffle_shop/{path}'
    compiled = (REPO / compiled_path).read_bytes()
    check(compiled == a.get('compiled_code', '').encode(),
          f'compiled_model_differs_from_checkout_manifest:{node_id}')
    hashes[f'public_corpus/jaffle-shop-sidemantic/jaffle-shop/{compiled_path}'] = digest(compiled)
    tree = parse(compiled.decode(), compiled_path)
    check(isinstance(tree, exp.Select) and isinstance(tree.args.get('with_'), exp.With),
          f'unsupported_compiled_model:{node_id}')
    ctes = {cte.alias: cte.this for cte in tree.args['with_'].expressions}
    check(len(ctes) == len(tree.args['with_'].expressions)
          and all(isinstance(q, exp.Select) for q in ctes.values()),
          f'unsupported_CTEs:{node_id}')
    return tree, ctes


def direct_star(query, expected_table, label):
    check(len(query.expressions) == 1 and isinstance(query.expressions[0], exp.Star)
          and not query.args.get('joins') and isinstance(query.args.get('from_').this, exp.Table)
          and query.args['from_'].this.name == expected_table,
          f'unsupported_star_edge:{label}')


def exact_projection(query, name, label):
    return one([p.this for p in query.expressions
                if isinstance(p, exp.Alias) and p.alias == name],
               f'projection_not_unique:{label}.{name}')


def dep(node):
    return node.get('depends_on', {}).get('nodes', [])


def validate_metric(card, packet_manifest, checkout, yaml_doc, provenance, hashes, texts):
    uid = card['metric_id']
    metric = packet_manifest['metrics'][uid]
    check(metric['name'] == card['metric_name'] and metric['type'] == card['type'] == 'simple'
          and metric.get('filter') is None and card['sql_scope'] == 'ungrouped',
          f'unsupported_metric_type_filter_or_scope:{uid}')
    sem_id = one(dep(metric), f'ambiguous_metric_dependency:{uid}')
    sem = packet_manifest['semantic_models'][sem_id]
    check(sem_id in checkout['semantic_models'] and card['manifest_depends_on'] == [sem_id],
          f'semantic_dependency_mismatch:{uid}')
    measure_name = metric['type_params']['measure']['name']
    check(metric['type_params']['input_measures'] == [metric['type_params']['measure']],
          f'unsupported_measure_modifiers:{uid}')
    measure = one([m for m in sem['measures'] if m['name'] == measure_name],
                  f'ambiguous_measure:{uid}')
    model_id = one(dep(sem), f'ambiguous_model_dependency:{uid}')
    check(model_id == 'model.jaffle_shop.order_items', f'unsupported_model:{uid}')
    owner = one(one(card['input_measures'], f'ambiguous_packet_measure:{uid}')['owners'],
                f'ambiguous_packet_owner:{uid}')
    check(card['input_measures'][0]['measure'] == measure_name
          and owner['expr'] == measure['expr'] and owner['agg'] == measure['agg'] == 'sum'
          and owner['model_node'] == [model_id] and len(card['source_models']) == 1
          and card['source_models'][0]['node'] == model_id,
          f'packet_measure_binding_mismatch:{uid}')
    card_source = card['source_models'][0]
    raw = source(MART, hashes, texts)
    check(card_source['source_file'] == MART and raw == card_source['raw_sql'] + '\n'
          and digest(card_source['raw_sql'].encode()) == card_source['raw_sql_sha256']
          and card_source['raw_sql'] == packet_manifest['nodes'][model_id]['raw_code'],
          f'packet_model_source_mismatch:{uid}')
    check(card['declared_file'] == metric['original_file_path'] == sem['original_file_path'] == YAML,
          f'YAML_path_mismatch:{uid}')
    definition = one([m for m in yaml_doc['metrics'] if m['name'] == metric['name']],
                     f'YAML_metric_ambiguous:{uid}')
    semantic = one([s for s in yaml_doc['semantic_models'] if s['name'] == sem['name']],
                   f'YAML_semantic_ambiguous:{uid}')
    declared = one([m for m in semantic['measures'] if m['name'] == measure_name],
                   f'YAML_measure_ambiguous:{uid}')
    check(definition['type'] == 'simple' and definition['type_params']['measure'] == measure_name
          and declared['agg'] == 'sum' and declared['expr'] == measure['expr'],
          f'YAML_manifest_binding_mismatch:{uid}')
    for limits, name in ((card['declared_span_text_located'], metric['name']),
                         (owner['measure_span'], measure_name)):
        lines = texts[YAML].splitlines()[limits[0]-1:limits[1]]
        check(any(x.strip() == f'- name: {name}' for x in lines), f'YAML_span_mismatch:{uid}')
    lines = texts[YAML].splitlines()[owner['measure_span'][0]-1:owner['measure_span'][1]]
    check(any(x.strip() == f"expr: {measure['expr']}" for x in lines),
          f'YAML_measure_expression_span_mismatch:{uid}')
    record = one([r for r in provenance if r['metric'] == metric['name']],
                 f'provenance_ambiguous:{uid}')
    attempt = one([a for a in record['explain_attempts'] if a.get('sql_file')],
                  f'generated_SQL_ambiguous:{uid}')
    path = attempt['sql_file']
    check(re.fullmatch(r'generated_sql/[a-z_]+\.sql', path) is not None,
          f'unsupported_generated_SQL_path:{path}')
    sql = (BUNDLE / path).read_bytes()
    check(sql.decode() == card['compiled_sql'] and digest(sql) == card['compiled_sql_sha256']
          == attempt['sql_sha256'], f'generated_SQL_hash_or_packet_mismatch:{uid}')
    hashes[f'metric_provenance_verification/{path}'] = digest(sql)
    query = parse(sql.decode(), path)
    check(isinstance(query, exp.Select) and len(query.expressions) == 1
          and query.args.get('with_') is None and not query.args.get('joins')
          and all(query.args.get(k) is None for k in ('where', 'group', 'having', 'qualify', 'limit')),
          f'unsupported_metric_SQL:{uid}')
    output = query.expressions[0]
    check(isinstance(output, exp.Alias) and output.alias == metric['name']
          and isinstance(output.this, exp.Sum)
          and output.this.this == parse(measure['expr'], uid),
          f'compiled_measure_expression_mismatch:{uid}')
    check(relation(query.args['from_'].this) ==
          named_relation(packet_manifest['nodes'][model_id]['relation_name']),
          f'compiled_metric_relation_mismatch:{uid}')
    return {'card': card, 'owner': owner, 'expr': output.this.this, 'measure': measure_name,
            'model': model_id}


def case_shape(expression):
    if isinstance(expression, exp.Column) and not expression.table:
        return None, expression.name
    check(isinstance(expression, exp.Case) and expression.this is None
          and len(expression.args.get('ifs', [])) == 1,
          f'unsupported_measure_expression:{expression.sql()}')
    branch = expression.args['ifs'][0]
    flag, price, default = branch.this, branch.args.get('true'), expression.args.get('default')
    check(isinstance(flag, exp.Column) and not flag.table
          and isinstance(price, exp.Column) and not price.table
          and isinstance(default, exp.Literal) and default.this == '0' and not default.is_string,
          f'unsupported_CASE_shape:{expression.sql()}')
    return flag.name, price.name


def classify(staging, flag):
    expression = exact_projection(staging, flag, 'stg_products')
    check(isinstance(expression, exp.Coalesce) and isinstance(expression.this, exp.EQ)
          and len(expression.expressions) == 1
          and isinstance(expression.expressions[0], exp.Boolean)
          and expression.expressions[0].this is False,
          f'unsupported_classifier:{expression.sql()}')
    eq = expression.this
    check(isinstance(eq.this, exp.Column) and not eq.this.table and eq.this.name == 'type'
          and isinstance(eq.expression, exp.Literal) and eq.expression.is_string,
          f'unsupported_raw_type_predicate:{expression.sql()}')
    return eq.expression.this


def duckdb_check(classes):
    db = duckdb.connect(':memory:')
    results = {}
    for flag, category in classes:
        check(re.fullmatch(r'[a-z_]+', category) is not None, 'unsafe_category_literal')
        rows = db.execute(f"""
            WITH raw_products(sku, type, price) AS
                (VALUES (1, '{category}', 500), (2, NULL::VARCHAR, 500)),
            raw_items(product_id) AS (VALUES (1), (2), (3)),
            stg_products AS
                (SELECT sku, price, coalesce(type = '{category}', false) AS flag
                 FROM raw_products),
            order_items AS
                (SELECT raw_items.product_id, stg_products.flag, stg_products.price
                 FROM raw_items LEFT JOIN stg_products
                 ON raw_items.product_id = stg_products.sku)
            SELECT product_id, typeof(flag), flag, flag IS NULL,
                   CASE WHEN flag THEN price ELSE 0 END
            FROM order_items ORDER BY product_id
        """).fetchall()
        check(rows == [(1, 'BOOLEAN', True, False, 500),
                       (2, 'BOOLEAN', False, False, 0),
                       (3, 'BOOLEAN', None, True, 0)],
              f'unexpected_DuckDB_NULL_or_boolean_behavior:{flag}:{rows}')
        results[flag] = rows
    db.close()
    return results


def build():
    head = subprocess.run(['git', '-C', str(REPO), 'rev-parse', 'HEAD'],
                          capture_output=True, check=True, text=True).stdout.strip()
    check(head == PIN, f'Git_HEAD_not_pinned:{head}')
    packet = json_read(PACKET)
    hashes = {'metric_matching_pilot/compiled_jaffle_i1_packet.json': digest(PACKET.read_bytes())}
    check(packet['source_commit'] == PIN and packet['metric_count'] == len(packet['cards']) == 19
          and packet['pair_count'] == len(packet['pairs']) == 171,
          'packet_commit_or_171_pair_census_mismatch')
    pair_ids = [p['pair_id'] for p in packet['pairs']]
    check(len(set(pair_ids)) == 171 and
          digest((json.dumps(pair_ids, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':')) + '\n').encode()) == packet['pair_set_sha256'],
          'packet_pair_set_hash_mismatch')
    for key, path in (('manifest', 'manifests/manifest.json'),
                      ('semantic_manifest', 'manifests/semantic_manifest.json'),
                      ('provenance', 'provenance.json')):
        data = (BUNDLE / path).read_bytes()
        check(digest(data) == packet['source_sha256'][key], f'bundle_hash_mismatch:{path}')
        hashes[f'metric_provenance_verification/{path}'] = digest(data)
    manifest = json_read(BUNDLE / 'manifests/manifest.json')
    semantic = json_read(BUNDLE / 'manifests/semantic_manifest.json')
    provenance = json_read(BUNDLE / 'provenance.json')
    checkout = json_read(REPO / 'target/manifest.json')
    hashes['public_corpus/jaffle-shop-sidemantic/jaffle-shop/target/manifest.json'] = digest(
        (REPO / 'target/manifest.json').read_bytes())
    check(len(semantic['metrics']) == len(provenance) == 19, 'bundle_metric_census_mismatch')
    by_name = {c['metric_name']: c for c in packet['cards']}
    check(len(by_name) == 19 and {c['metric_id'] for c in packet['cards']} == set(manifest['metrics']),
          'packet_metric_inventory_mismatch')
    selected = []
    for a, b in PAIRS:
        ids = {by_name[a]['metric_id'], by_name[b]['metric_id']}
        pair = one([p for p in packet['pairs'] if {p['a'], p['b']} == ids],
                   f'selected_pair_missing:{a}:{b}')
        check(pair['scope_compatible'] is True and pair['target_scope'] == 'ungrouped',
              f'unsupported_pair_scope:{a}:{b}')
        selected.append(pair)
    texts = {}
    yaml_doc = yaml.safe_load(source(YAML, hashes, texts))
    findings = {name: validate_metric(by_name[name], manifest, checkout, yaml_doc,
                                      provenance, hashes, texts)
                for name in sorted({n for pair in PAIRS for n in pair})}
    mart, mart_ctes = model_sql('model.jaffle_shop.order_items', MART,
                                checkout, manifest, hashes, texts)
    products, product_ctes = model_sql('model.jaffle_shop.stg_products', PRODUCTS,
                                       checkout, manifest, hashes, texts)
    items, item_ctes = model_sql('model.jaffle_shop.stg_order_items', ITEMS,
                                 checkout, manifest, hashes, texts)
    direct_star(mart, 'joined', 'mart.final')
    direct_star(products, 'renamed', 'stg_products.final')
    direct_star(items, 'renamed', 'stg_order_items.final')
    joined = mart_ctes['joined']
    product_rename = product_ctes['renamed']
    item_rename = item_ctes['renamed']
    direct_star(mart_ctes['products'], 'stg_products', 'mart.products')
    check(relation(mart_ctes['products'].args['from_'].this) ==
          named_relation(checkout['nodes']['model.jaffle_shop.stg_products']['relation_name']),
          'mart_products_relation_mismatch')
    direct_star(product_ctes['source'], 'raw_products', 'products.source')
    check(relation(product_ctes['source'].args['from_'].this) ==
          named_relation(checkout['sources']['source.jaffle_shop.ecom.raw_products']['relation_name']),
          'raw_products_relation_mismatch')
    check(product_rename.args['from_'].this.name == 'source'
          and item_rename.args['from_'].this.name == 'source',
          'unsupported_staging_source_CTE')
    check(dep(checkout['nodes']['model.jaffle_shop.order_items']).count(
          'model.jaffle_shop.stg_products') == 1
          and dep(checkout['nodes']['model.jaffle_shop.stg_products']) ==
          ['source.jaffle_shop.ecom.raw_products'], 'source_dependency_mismatch')
    join = one([j for j in joined.args.get('joins', [])
                if j.this.alias_or_name == 'products'], 'product_join_ambiguous')
    on = join.args.get('on')
    check(join.args.get('side') == 'LEFT' and isinstance(on, exp.EQ)
          and isinstance(on.this, exp.Column) and isinstance(on.expression, exp.Column)
          and {on.this.sql().lower(), on.expression.sql().lower()} ==
          {'order_items.product_id', 'products.product_id'},
          f'unsupported_product_JOIN:{join.sql()}')
    check(exact_projection(product_rename, 'product_id', 'stg_products') == parse('sku', 'product key')
          and exact_projection(item_rename, 'product_id', 'stg_order_items') == parse('sku', 'item key')
          and [p.alias_or_name for p in item_rename.expressions] ==
          ['order_item_id', 'order_id', 'product_id'],
          'join_key_or_item_star_fields_mismatch')
    check(isinstance(joined.expressions[0], exp.Column)
          and joined.expressions[0].sql().lower() == 'order_items.*',
          'unsupported_mart_star_projection')
    classes = []
    for name, finding in findings.items():
        flag, price = case_shape(finding['expr'])
        finding.update(flag=flag, price=price)
        projection = exact_projection(joined, price, 'order_items')
        check(isinstance(projection, exp.Column) and projection.table == 'products'
              and projection.name == price, f'price_not_projected_from_products:{name}')
        check(exact_projection(product_rename, price, 'stg_products') is not None,
              f'price_missing_in_staging:{name}')
        if flag:
            projection = exact_projection(joined, flag, 'order_items')
            check(isinstance(projection, exp.Column) and projection.table == 'products'
                  and projection.name == flag, f'flag_not_projected_from_products:{name}')
            category = classify(product_rename, flag)
            finding['category'] = category
            classes.append((flag, category))
    check(len(classes) == 2 and len(set(classes)) == 2, 'selected_classifiers_not_distinct')
    for a, b in PAIRS:
        check(findings[a]['flag'] and findings[b]['flag'] is None
              and findings[a]['price'] == findings[b]['price'] == 'product_price',
              f'unsupported_conditional_pair_shape:{a}:{b}')
    sources = source(SOURCES, hashes, texts)
    doc = yaml.safe_load(sources)
    ecom = one([s for s in doc['sources'] if s['name'] == 'ecom'], 'source_group_ambiguous')
    check({'raw_products', 'raw_items'} <= {t['name'] for t in ecom['tables']},
          'raw_source_declaration_missing')
    results = duckdb_check(classes)
    return render(selected, findings, classes, results, hashes, texts)


def render(selected, findings, classes, results, hashes, texts):
    lines = [
        '# Conditional flag lineage: pinned Jaffle development packet', '',
        f'Git HEAD `{PIN}`; packet SHA-256 `{hashes["metric_matching_pilot/compiled_jaffle_i1_packet.json"]}`. '
        f'`sqlglot {sqlglot.__version__}`, `DuckDB {duckdb.__version__}`.', '',
        '## Coverage and finding', '',
        f'- Verified 2 selected pairs of 171, using 3 distinct metric cards/measures of 19. '
        'Both selected generated SQL scopes are `ungrouped`. The exact selected CASE predicates '
        'trace to `raw_products.type`; `revenue` uses the same `product_price` projection without '
        'the predicate. This supports the two conditional scope hypotheses as source evidence.',
        '- Unsupported expressions encountered within these two chains: none. The executable '
        'probe raises `Unsupported` for a changed CASE, classifier, join, projection, binding, '
        'scope, or hash. Other SQL shapes and metrics are outside its checked chain.', '',
        '| Packet pair | Exact measure → generated SQL | Raw type predicate |',
        '| --- | --- | --- |',
    ]
    for pair, (a, b) in zip(selected, PAIRS):
        x, y = findings[a], findings[b]
        lines.append(f'| `{pair["pair_id"]}` | `SUM({x["expr"].sql()}) AS {a}` vs '
                     f'`SUM({y["expr"].sql()}) AS {b}`; unique manifest owners '
                     f'`{x["measure"]}` / `{y["measure"]}` in `order_items` | '
                     f'`type = \'{x["category"]}\'` |')
    lines += ['', '## Exact source spans', '',
              '| Link | Git HEAD source span | Verified text |', '| --- | --- | --- |']
    for name, row in findings.items():
        c, m = row['card'], row['owner']['measure_span']
        s = c['declared_span_text_located']
        lines.append(f'| `{name}` metric → measure | `{YAML}:{s[0]}-{s[1]}` → '
                     f'`{YAML}:{m[0]}-{m[1]}` | `{row["expr"].sql()}` |')
    for flag, category in classes:
        lines.append(f'| `{flag}` mart → staging | '
                     f'{where(texts[MART], MART, f"products.{flag},")} → '
                     f'{where(texts[PRODUCTS], PRODUCTS, f"coalesce(type = \'{category}\', false) as {flag}")} | '
                     f'`coalesce(type = \'{category}\', false)` |')
    lines += [
        f'| Product CTE and LEFT JOIN | {where(texts[MART], MART, "select * from {{ ref(\'stg_products\') }}")} → '
        f'{where(texts[MART], MART, "left join products on order_items.product_id = products.product_id")} | '
        '`order_items.product_id = products.product_id`; absent right row yields NULL flag |',
        f'| Staging raw source | {where(texts[PRODUCTS], PRODUCTS, "source(\'ecom\', \'raw_products\')")} → '
        f'{where(texts[SOURCES], SOURCES, "- name: raw_products")} | `raw_products.type` is the classifier input |',
        f'| Join keys and price | {where(texts[ITEMS], ITEMS, "sku as product_id")} / '
        f'{where(texts[PRODUCTS], PRODUCTS, "sku as product_id")} / '
        f'{where(texts[MART], MART, "products.product_price,")} / '
        f'{where(texts[PRODUCTS], PRODUCTS, "{{ cents_to_dollars(\'price\') }} as product_price")} | '
        'Keys come from `sku`; price is projected from staging (macro internals not traced) |',
        '', '## DuckDB behavior on synthetic rows', '',
        '| Classifier | Raw type / join | Staging flag | Mart flag type/value | `CASE` with price 500 |',
        '| --- | --- | --- | --- | ---: |',
    ]
    for flag, category in classes:
        matched, null_type, missing = results[flag]
        lines += [f'| `{flag}` | `{category}` matched | TRUE | `{matched[1]}` / TRUE | {matched[4]} |',
                  f'| `{flag}` | NULL type matched | FALSE | `{null_type[1]}` / FALSE | {null_type[4]} |',
                  f'| `{flag}` | missing product row | no staging row | `{missing[1]}` / NULL | {missing[4]} |']
    lines += ['', 'The staged `coalesce` expression is `BOOLEAN` and yields FALSE for a NULL raw '
              'type. The LEFT JOIN can reintroduce NULL in the mart flag when the product row '
              'is absent; `CASE WHEN NULL THEN product_price ELSE 0 END` takes `ELSE 0`. '
              'A TRUE flag and NULL price yields NULL; SUM ignores NULL values and can be NULL '
              'when no non-NULL input exists.', '',
              '## Hashes (SHA-256)', '', '| Artifact | SHA-256 |', '| --- | --- |']
    lines += [f'| `{path}` | `{value}` |' for path, value in sorted(hashes.items())]
    lines += ['', 'All source file bytes above equal `Git HEAD:<path>`. The bundle hashes equal '
              'the 171-pair packet’s recorded manifest, semantic manifest, and provenance hashes. '
              'The three generated metric SQL files equal their packet SQL bytes and exact '
              '`SUM(measure expression)` bindings. The three checkout compiled model SQL files '
              'equal checkout manifest `compiled_code`; model `raw_code` in both manifests '
              'equals the Git source except for exactly one omitted final LF.', '',
              '## Limits', '',
              '- This is an explicit checked chain for the two CASE flags. It does not parse '
              'general dbt SQL, expand arbitrary stars, or trace other expressions. The '
              'staging price macro implementation, real rows, row multiplicity, and complete '
              'aggregation/null behavior are not established.',
              '- The generated MetricFlow queries use `dev.main.order_items`, matching their '
              'bundle manifest. The checkout model compilation uses '
              '`jaffle_shop.main.order_items`, matching its checkout manifest. Both manifests '
              'point to the pinned source, but a single physical build identity is not '
              'attested. Their source checksum fields differ from Git HEAD and `raw_code`; '
              'the bundle build commit is not independently attested.',
              '- No held-out sources or worksheets were read. No human gold, universal '
              'equivalence, matching accuracy, or complete time/group scope follows.', '',
              'Reproduce with installed `duckdb`, `sqlglot`, and `PyYAML`: '
              '`python -B metric_matching_pilot/probe_flag_lineage.py --check`.', '']
    return '\n'.join(lines)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--check', action='store_true')
    args = cli.parse_args()
    report = build()
    if args.check:
        check(REPORT.read_text() == report, 'report_differs_from_probe')
    else:
        REPORT.write_text(report)
    print(f'2/171 pairs checked; report SHA-256 {digest(report.encode())}')


if __name__ == '__main__':
    main()
