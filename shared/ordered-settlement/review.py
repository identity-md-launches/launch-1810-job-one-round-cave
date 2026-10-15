#!/usr/bin/env python3
"""Check a pinned order plan's structure, settlement and transaction order offline."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


order = module('shared_order', 'vendor/settlement-order/order.py')
contracts = module('shared_contracts', 'vendor/json_contract.py')
HASH = {'type': 'string', 'pattern': '^0x[0-9a-fA-F]{64}$'}
POLICY = {'type': 'object', 'required': ['transactionHash', 'minimumConfirmations', 'requireFinalized'],
          'additionalProperties': False, 'properties': {
              'transactionHash': HASH,
              'minimumConfirmations': {'type': 'integer', 'minimum': 1, 'maximum': 1000000},
              'requireFinalized': {'type': 'boolean'}}}
ITEM = {'type': 'object', 'required': ['evidence', 'sha256', 'policy'],
        'additionalProperties': False, 'properties': {
            'evidence': {'type': 'string', 'minLength': 1},
            'sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'policy': POLICY}}
CONTRACT = contracts.prepare({'type': 'object', 'required': ['version', 'batch', 'sequence'],
    'additionalProperties': False, 'properties': {
        'version': {'type': 'integer', 'enum': [1]},
        'batch': {'type': 'object', 'required': ['version', 'items'],
                  'additionalProperties': False, 'properties': {
                      'version': {'type': 'integer', 'enum': [1]},
                      'items': {'type': 'array', 'minItems': 2, 'maxItems': 32, 'items': ITEM}}},
        'sequence': {'type': 'array', 'minItems': 2, 'maxItems': 32, 'items': HASH}}})


def render(report):
    encoded = json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + '\n'
    if len(encoded.encode('ascii')) > 100000:
        raise ValueError('complete report exceeds 100000 bytes')
    return encoded


def review(raw, expected_sha256):
    """Pin before parsing; replay exactly the bytes whose structure was checked."""
    order.b.k.pin(expected_sha256)
    if type(raw) is not bytes or len(raw) > order.b.k.LIMIT:
        raise ValueError('bounded exact plan bytes required')
    actual = hashlib.sha256(raw).hexdigest()
    result = {'accepted': False, 'state': 'plan_pin_mismatch',
              'actualPlanSha256': actual, 'expectedPlanSha256': expected_sha256,
              'evidenceChecked': False, 'orderChecked': False,
              'limitations': order.LIMITATIONS}
    if actual != expected_sha256:
        return result
    plan = order.b.k.p.s.strict_json(raw)
    diagnostics = contracts.validate(plan, CONTRACT)
    result['structure'] = {'valid': not diagnostics, 'diagnostics': diagnostics}
    if diagnostics:
        result['state'] = 'structural_review_required'
        render(result)
        return result
    # Semantic sequence membership, uniqueness, policy and path checks also run
    # before any evidence opens. Never trust an incoming acceptance flag.
    decision = order.review_bytes(raw, expected_sha256)
    result.update(accepted=decision['accepted'], state=decision['state'],
                  evidenceChecked=decision['evidenceChecked'],
                  orderChecked=decision['orderChecked'], orderReview=decision)
    render(result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', help='visible workspace-relative plan path')
    parser.add_argument('--sha256', required=True, help='independently retained exact plan hash')
    args = parser.parse_args(argv)
    try:
        order.b.k.pin(args.sha256)
        raw = order.b.k.load_bytes(args.plan)
        result = review(raw, args.sha256)
        sys.stdout.write(render(result))
        return 0 if result['accepted'] else 2 if result['state'] == 'input_error' else 1
    except (ValueError, TypeError, KeyError, OSError, RecursionError, order.Error):
        print(json.dumps({'accepted': False, 'state': 'input_error',
                          'reason': 'Invalid bounded plan, independent hash, evidence or report'}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
