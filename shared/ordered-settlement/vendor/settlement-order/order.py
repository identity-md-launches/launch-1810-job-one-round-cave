#!/usr/bin/env python3
"""Replay pinned Ethereum settlement evidence and check an independently chosen order."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

_spec = importlib.util.spec_from_file_location(
    'order_batch', Path(__file__).resolve().parent.parent / 'settlement-batch' / 'batch.py')
b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b)
Error = b.Error
LIMITATIONS = (
    'Historical provider assertions, not consensus, trie or inter-block ancestry proofs. '
    'Order means ascending (block number, transaction index), not causation or a successful '
    'application workflow. No payment amount, current freshness or authorization is checked. '
    'Keep the plan hash independently; replacing plan and expected hash defeats this check. '
    'No transactions are sent and no persistent ledger is updated.')


def validate(plan):
    """Validate all expectations before opening any evidence file."""
    if (not isinstance(plan, dict) or set(plan) != {'version', 'batch', 'sequence'}
            or type(plan['version']) is not int or plan['version'] != 1):
        raise Error('exact version 1 order plan required')
    items = b.validate(plan['batch'])
    sequence = plan['sequence']
    if not isinstance(sequence, list) or not 2 <= len(sequence) <= b.MAX_ITEMS:
        raise Error('sequence must contain 2..32 transaction hashes')
    sequence = [b.k.p.s.hash32(tx) for tx in sequence]
    if len(set(sequence)) != len(sequence):
        raise Error('sequence contains duplicate transaction hashes')
    if set(sequence) != {row['policy']['transactionHash'] for row in items}:
        raise Error('sequence must contain every batch transaction exactly once')
    return sequence


def compare_positions(rows, sequence):
    """Internal helper: inputs must be successful rows from batch replay."""
    by_tx = {row['transactionHash']: row for row in rows}
    slots, counts, problems = {}, {}, []
    positions = []
    for tx in sequence:
        row = by_tx[tx]
        height, index = row['block']['number'], row['transactionIndex']
        slot = (height, index)
        if slot in slots:
            problems.append({'kind': 'shared_transaction_position',
                             'transactions': [slots[slot], tx]})
        slots[slot] = tx
        count = row['transactionCount']
        if height in counts and counts[height] != count:
            problems.append({'kind': 'block_transaction_count_conflict', 'blockNumber': height})
        counts[height] = count
        positions.append({'transactionHash': tx, 'blockNumber': height,
                          'blockHash': row['block']['hash'], 'transactionIndex': index})
    for left, right in zip(positions, positions[1:]):
        if (left['blockNumber'], left['transactionIndex']) >= (
                right['blockNumber'], right['transactionIndex']):
            problems.append({'kind': 'required_order_not_met',
                             'before': left['transactionHash'], 'after': right['transactionHash']})
    return positions, problems


def review_bytes(raw, expected_sha256):
    expected = b.k.pin(expected_sha256)
    if type(raw) is not bytes or len(raw) > b.k.LIMIT:
        raise Error('bounded exact plan bytes required')
    actual = hashlib.sha256(raw).hexdigest()
    result = {'accepted': False, 'state': 'plan_pin_mismatch',
              'expectedPlanSha256': expected, 'actualPlanSha256': actual,
              'evidenceChecked': False, 'orderChecked': False, 'limitations': LIMITATIONS}
    # Do not parse a replaced plan, even if it would otherwise be valid.
    if actual != expected:
        return result
    plan = b.k.p.s.strict_json(raw)
    sequence = validate(plan)
    batch = b.review(plan['batch'])
    result.update(evidenceChecked=True, sequence=sequence, batch=batch)
    if not batch['accepted']:
        result['state'] = 'input_error' if batch['state'] == 'input_error' else 'settlement_review_required'
        return result
    positions, problems = compare_positions(batch['items'], sequence)
    result.update(orderChecked=True, positions=positions, problems=problems,
                  accepted=not problems,
                  state='settlement_order_match' if not problems else 'order_review_required')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--plan', help='visible workspace-relative order plan')
    parser.add_argument('--sha256', help='independently retained SHA-256 of exact plan bytes')
    args = parser.parse_args(argv)
    try:
        if args.demo:
            if args.plan or args.sha256:
                raise Error('demo refuses overrides')
            folder = Path(__file__).resolve().parent.relative_to(Path.cwd())
            raw = b.k.load_bytes(folder / 'demo-plan.json')
            # The bundled pin is illustrative, never independent approval.
            expected = b.k.load_bytes(folder / 'demo-plan.sha256').decode('ascii').strip()
        else:
            if args.plan is None or args.sha256 is None:
                raise Error('plan and independent hash required')
            expected = b.k.pin(args.sha256)
            raw = b.k.load_bytes(args.plan)
        result = review_bytes(raw, expected)
        if args.demo:
            result['demoNote'] = ('Two real ZTO transactions, ordered by their historical mainnet '
                                  'inclusions. This illustrates ordering, not a causal dependency '
                                  'between those transactions or independently retained approval.')
        encoded = json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False)
        if len(encoded.encode('ascii')) > 100000:
            raise Error('report exceeds 100 KB')
        print(encoded)
        return 0 if result['accepted'] else 2 if result['state'] == 'input_error' else 1
    except (Error, ValueError, TypeError, KeyError, OSError, RecursionError):
        print(json.dumps({'accepted': False, 'state': 'input_error',
                          'reason': 'Invalid bounded order plan, expected hash or evidence'}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
