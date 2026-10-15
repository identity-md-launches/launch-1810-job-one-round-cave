#!/usr/bin/env python3
"""Review a bounded queue of independently pinned Ethereum settlement evidence."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

_spec = importlib.util.spec_from_file_location(
    'batch_pinned', Path(__file__).resolve().parent.parent / 'pinned-position' / 'pinned.py')
k = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(k)
Error = k.Error
MAX_ITEMS = 32
LIMITATIONS = (
    'Historical provider assertions, not consensus or transaction-trie proofs. '
    'Pins and policies need independent custody. No freshness, payment amount, '
    'recipient ownership, authorization or cross-run deduplication is established. '
    'This report does not execute or record payments. Entries can sample different heads.')


def path_name(value):
    if (not isinstance(value, str) or not value or value.startswith('/') or '\\' in value
            or any(not p or p.startswith('.') for p in value.split('/'))):
        raise Error('visible workspace-relative evidence path required')
    return value


def validate(manifest):
    """Validate the entire plan, including uniqueness, before evidence is read."""
    if (not isinstance(manifest, dict) or set(manifest) != {'version', 'items'}
            or type(manifest['version']) is not int or manifest['version'] != 1
            or not isinstance(manifest['items'], list)
            or not 1 <= len(manifest['items']) <= MAX_ITEMS):
        raise Error('version 1 with 1..32 items required')
    items, seen = [], set()
    for item in manifest['items']:
        if not isinstance(item, dict) or set(item) != {'evidence', 'sha256', 'policy'}:
            raise Error('exact item fields required')
        policy = item['policy']
        if (not isinstance(policy, dict) or set(policy) != {
                'transactionHash', 'minimumConfirmations', 'requireFinalized'}):
            raise Error('exact independent policy fields required')
        policy = k.p.policy(policy['transactionHash'], policy['minimumConfirmations'],
                            policy['requireFinalized'])
        tx = policy['transactionHash']
        if tx in seen:
            raise Error('duplicate transaction in batch')
        seen.add(tx)
        items.append({'evidence': path_name(item['evidence']),
                      'sha256': k.pin(item['sha256']), 'policy': policy})
    return items


def review(manifest):
    items = validate(manifest)
    reports = []
    for index, item in enumerate(items):
        row = {'index': index, 'transactionHash': item['policy']['transactionHash'],
               'policy': item['policy'], 'expectedSha256': item['sha256']}
        try:
            report = k.review_file(item['evidence'], item['sha256'], item['policy'])
            row.update(accepted=report['accepted'], state=report['state'],
                       actualSha256=report['actualSha256'])
            position = report.get('positionReview')
            if position is not None:
                row['positionState'] = position['state']
                row['alerts'] = position['alerts']
                for field in ('transactionIndex', 'transactionCount', 'block'):
                    if field in position:
                        row[field] = position[field]
                settlement = position['settlement']
                row['settlementState'] = settlement['state']
                for field in ('head', 'inclusion', 'finalizedHead', 'confirmations', 'finalized'):
                    if field in settlement:
                        row[field] = settlement[field]
        except (Error, ValueError, TypeError, KeyError, OSError, RecursionError):
            # A bad row cannot hide later failures or grant partial acceptance.
            row.update(accepted=False, state='input_error',
                       reason='Evidence unavailable, invalid or inconsistent with expected policy')
        reports.append(row)
    anchors = {}
    for row in reports:
        for field in ('head', 'inclusion', 'finalizedHead'):
            if field in row:
                block = row[field]
                anchors.setdefault(block['number'], set()).add(block['hash'])
    conflicts = sorted(height for height, hashes in anchors.items() if len(hashes) > 1)
    accepted = all(row['accepted'] for row in reports) and not conflicts
    invalid = any(row['state'] == 'input_error' for row in reports)
    return {'accepted': accepted,
            'state': 'batch_settlement_match' if accepted else
                     'input_error' if invalid else 'review_required',
            'count': len(reports), 'acceptedCount': sum(row['accepted'] for row in reports),
            'conflictingBlockNumbers': conflicts,
            'items': reports, 'limitations': LIMITATIONS}


def review_manifest_bytes(raw):
    if type(raw) is not bytes or len(raw) > k.LIMIT:
        raise Error('bounded manifest bytes required')
    result = review(k.p.s.strict_json(raw))
    result['manifestSha256'] = hashlib.sha256(raw).hexdigest()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--demo', action='store_true')
    mode.add_argument('--manifest', help='independently reviewed workspace-relative batch plan')
    args = parser.parse_args(argv)
    try:
        path = args.manifest
        if args.demo:
            path = (Path(__file__).resolve().parent / 'demo-manifest.json').relative_to(Path.cwd())
        result = review_manifest_bytes(k.load_bytes(path))
        if args.demo:
            result['demoNote'] = ('Real historical ZTO transaction; bundled expectations illustrate '
                                  'retention and are not independently held approval or current evidence.')
        encoded = json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False)
        if len(encoded.encode('ascii')) > 100000:
            raise Error('report exceeds 100 KB')
        print(encoded)
        return 0 if result['accepted'] else 2 if result['state'] == 'input_error' else 1
    except (Error, ValueError, TypeError, KeyError, OSError, RecursionError):
        print(json.dumps({'accepted': False, 'state': 'input_error',
                          'reason': 'Invalid batch plan, file boundary or report size'}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
