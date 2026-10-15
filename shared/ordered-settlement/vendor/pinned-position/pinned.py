#!/usr/bin/env python3
"""Review exact retained Ethereum transaction-position evidence, offline."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

_spec = importlib.util.spec_from_file_location(
    'pinned_position', Path(__file__).resolve().parent.parent / 'tx-position' / 'position.py')
p = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(p)
Error = p.w.Error
DEMO_PIN = 'b8b7c0ec53f30624c96ce598d0911d803941945332627c3bbfea0739f1ae9ae5'
LIMIT = 90000


def pin(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise Error('expected lowercase SHA-256 without prefix')
    return value


def load_bytes(filename):
    """Descriptor-relative, bounded regular-file read; never follow symlinks.

    Adapted from payment-witness.load_workspace_json to retain the exact bytes.
    Opens only explicit visible paths beneath the current workspace directory.
    """
    if not isinstance(filename, (str, Path)):
        raise Error('expected visible workspace-relative evidence path')
    name = str(filename)
    parts = name.split('/')
    if (not name or name.startswith('/') or '\\' in name or
            any(not part or part in ('.', '..') or part.startswith('.') for part in parts)):
        raise Error('expected visible workspace-relative evidence path')
    if (not hasattr(os, 'O_NOFOLLOW') or not hasattr(os, 'O_DIRECTORY') or
            os.open not in os.supports_dir_fd):
        raise Error('safe file opens unsupported')
    directory = descriptor = None
    try:
        directory = os.open('.', os.O_RDONLY | os.O_DIRECTORY)
        for part in parts[:-1]:
            next_directory = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                     dir_fd=directory)
            os.close(directory)
            directory = next_directory
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise Error('evidence must be a regular file')
        chunks, size = [], 0
        while size <= LIMIT:
            chunk = os.read(descriptor, min(8192, LIMIT + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        if size > LIMIT:
            raise Error('evidence exceeds 90 KB')
        return b''.join(chunks)
    except OSError:
        raise Error('evidence could not be opened safely') from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)


def review_bytes(raw, expected_pin, expected_policy):
    expected_pin = pin(expected_pin)
    expected = p.policy(expected_policy['transactionHash'],
                        expected_policy['minimumConfirmations'],
                        expected_policy['requireFinalized'])
    if type(raw) is not bytes or len(raw) > LIMIT:
        raise Error('bounded bytes required')
    actual = hashlib.sha256(raw).hexdigest()
    report = {'accepted': False, 'state': 'evidence_pin_mismatch',
              'expectedSha256': expected_pin, 'actualSha256': actual,
              'exactBytesMatch': actual == expected_pin, 'policy': expected,
              'evidenceBytes': len(raw),
              'limitations': 'A separately retained pin detects byte replacement; it authenticates no provider, '
                             'chain state, consensus, freshness or payment authorization.'}
    # Pin comparison precedes all JSON parsing and semantic replay. Parse exactly
    # the bytes hashed above, with no second file read or canonical reserialization.
    if actual != expected_pin:
        return report
    result = p.replay(p.s.strict_json(raw), expected)
    report['positionReview'] = result
    report['accepted'] = result['accepted']
    report['state'] = 'pinned_position_and_settlement_match' if result['accepted'] else 'review_required'
    return report


def review_file(filename, expected_pin, expected_policy):
    pin(expected_pin)  # Refuse malformed expectations before opening any input.
    p.policy(expected_policy['transactionHash'], expected_policy['minimumConfirmations'],
             expected_policy['requireFinalized'])
    return review_bytes(load_bytes(filename), expected_pin, expected_policy)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--demo', action='store_true')
    mode.add_argument('--evidence', help='visible workspace-relative position transcript')
    parser.add_argument('--sha256', help='independently retained exact-byte SHA-256')
    parser.add_argument('--tx', help='independently selected Ethereum transaction hash')
    parser.add_argument('--confirmations', type=int, default=12)
    parser.add_argument('--allow-unfinalized', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.demo:
            if args.sha256 or args.tx or args.confirmations != 12 or args.allow_unfinalized:
                raise Error('demo refuses policy or pin overrides')
            filename = (Path(__file__).resolve().parent.parent / 'tx-position' /
                        'live-evidence.json').relative_to(Path.cwd())
            result = review_file(filename, DEMO_PIN, p.policy(p.DEMO_TX, 12, True))
            result['demoNote'] = ('Historical real ZTO evidence. This bundled pin illustrates retention; '
                                  'retain your own pin independently before accepting later evidence.')
        else:
            if args.sha256 is None or args.tx is None:
                raise Error('independent pin and transaction required')
            result = review_file(args.evidence, args.sha256,
                                 p.policy(args.tx, args.confirmations, not args.allow_unfinalized))
        encoded = json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False)
        if len(encoded.encode('ascii')) > 100000:
            raise Error('report exceeds 100 KB')
        print(encoded)
        return 0 if result['accepted'] else 1
    except (Error, ValueError, TypeError, KeyError, OSError, RecursionError):
        print(json.dumps({'accepted': False, 'state': 'input_error',
                          'reason': 'Invalid evidence, independent pin or policy'}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
