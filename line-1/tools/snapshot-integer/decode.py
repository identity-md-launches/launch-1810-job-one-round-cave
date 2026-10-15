#!/usr/bin/env python3
"""Decode one explicitly typed integer from a validated RPC snapshot, offline."""
import argparse
from pathlib import Path
import re
import runpy
import sys

S = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                       'snapshot-select' / 'select_result.py'))


def decode(value, encoding, decimals=0):
    """No inferred ABI types, floating point or unbounded integer conversion."""
    if type(decimals) is not int or not 0 <= decimals <= 255:
        raise ValueError('decimals must be an integer from 0 to 255')
    if type(value) is not str:
        raise ValueError('selected value must be a hex string')
    if encoding == 'quantity':
        if not re.fullmatch(r'0x(?:0|[1-9a-fA-F][0-9a-fA-F]{0,63})', value):
            raise ValueError('quantity must be canonical 0x hex, at most 256 bits')
        number = int(value[2:], 16)
    elif encoding in ('uint256', 'int256'):
        if not re.fullmatch(r'0x[0-9a-fA-F]{64}', value):
            raise ValueError('ABI integer requires exactly one 32-byte hex word')
        number = int(value[2:], 16)
        if encoding == 'int256' and number >= 2**255:
            number -= 2**256
    else:
        raise ValueError('encoding must be quantity, uint256 or int256')
    digits = str(abs(number)).zfill(decimals + 1)
    fixed = digits if decimals == 0 else digits[:-decimals] + '.' + digits[-decimals:]
    if number < 0:
        fixed = '-' + fixed
    return {'encoding': encoding, 'raw_decimal': str(number),
            'decimals': decimals, 'fixed_decimal': fixed}


def report(snapshot, pointer, encoding, decimals):
    selected = S['report'](snapshot, pointer)
    decoded = decode(selected['value'], encoding, decimals)
    return {'schema': 'line1-snapshot-integer-v1',
            'selection': selected, 'decoded': decoded,
            'meaning': 'Caller-selected integer encoding and scale; provider observation, '
                       'not ABI verification, units, state proof or freshness.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', help='visible relative workspace snapshot path')
    parser.add_argument('--pointer', default='', help='JSON Pointer relative to response.result')
    parser.add_argument('--encoding', required=True, choices=('quantity', 'uint256', 'int256'))
    parser.add_argument('--decimals', type=int, default=0, help='explicit scale, 0 through 255')
    args = parser.parse_args(argv)
    try:
        S['tokens'](args.pointer)
        if not 0 <= args.decimals <= 255:
            raise ValueError('decimals must be from 0 to 255')
        snapshot = S['B']['verify_snapshot'](args.snapshot)
        result = report(snapshot, args.pointer, args.encoding, args.decimals)
        # Fully construct and bound output before emitting any bytes.
        sys.stdout.write(S['render'](result))
        return 0
    except (S['B']['SnapshotError'], ValueError, OSError, RecursionError,
            TypeError, OverflowError) as exc:
        print('snapshot-integer: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
