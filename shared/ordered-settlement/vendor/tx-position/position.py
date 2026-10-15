#!/usr/bin/env python3
"""Check a receipt's claimed transaction position in a canonical Ethereum block."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

_spec = importlib.util.spec_from_file_location(
    'position_witness', Path(__file__).resolve().parent.parent / 'payment-witness' / 'witness.py')
w = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(w)
s = w.settlement
SOURCES = (s.RPC_URL, 'https://eth.drpc.org')
DEMO_TX = w.DEMO_TX  # A real ZTO pool transaction, not a fabricated transaction.
MAX_READS = 16
MAX_TRANSACTIONS = 1024
MAX_EVIDENCE = 90000


def same_json(left, right):
    """Compare JSON values without Python's True == 1 coercion."""
    return (json.dumps(left, sort_keys=True, separators=(',', ':'), allow_nan=False) ==
            json.dumps(right, sort_keys=True, separators=(',', ':'), allow_nan=False))


def policy(tx, confirmations, finalized):
    tx = s.hash32(tx)
    if type(confirmations) is not int or not 1 <= confirmations <= 1000000 or type(finalized) is not bool:
        raise w.Error('invalid settlement policy')
    return {'transactionHash': tx, 'minimumConfirmations': confirmations,
            'requireFinalized': finalized}


class Recorder:
    """Keep only fields this check consumes; retain the complete transaction list."""
    def __init__(self, rpc):
        self.rpc, self.reads, self.keep_transactions = rpc, [], False

    def call(self, method, params):
        value = self.rpc.call(method, params)
        if method == 'eth_getBlockByNumber' and isinstance(value, dict):
            keys = ('number', 'hash', 'transactions') if self.keep_transactions else ('number', 'hash')
            saved = {key: value.get(key) for key in keys}
        elif method == 'eth_getTransactionReceipt' and isinstance(value, dict):
            saved = {key: value.get(key) for key in
                     ('transactionHash', 'blockNumber', 'blockHash', 'status', 'transactionIndex')}
        else:
            saved = value
        self.reads.append({'method': method, 'params': params, 'result': saved})
        if len(self.reads) > MAX_READS:
            raise w.Error('read transcript exceeds bound')
        return value


class Replay:
    def __init__(self, reads):
        if not isinstance(reads, list) or len(reads) > MAX_READS:
            raise w.Error('invalid or oversized read transcript')
        self.reads, self.index, self.keep_transactions = reads, 0, False

    def call(self, method, params):
        if self.index >= len(self.reads):
            raise w.Error('missing replay read')
        item = self.reads[self.index]
        self.index += 1
        if (not isinstance(item, dict) or set(item) != {'method', 'params', 'result'} or
                item['method'] != method or not same_json(item['params'], params)):
            raise w.Error('replay request mismatch')
        return item['result']


def verify(rpc, expected):
    expected = policy(expected['transactionHash'], expected['minimumConfirmations'],
                      expected['requireFinalized'])
    tx = expected['transactionHash']
    settlement = s.inspect(rpc, tx, expected['minimumConfirmations'], expected['requireFinalized'])
    report = {'accepted': False, 'state': settlement['state'], 'transactionHash': tx,
              'policy': expected, 'settlement': settlement, 'alerts': []}
    if not settlement['settled']:
        report['alerts'].append('settlement_policy_not_met')
        return report

    inclusion = settlement['inclusion']
    receipt = rpc.call('eth_getTransactionReceipt', [tx])
    if not isinstance(receipt, dict):
        raise w.Error('receipt unavailable on reread')
    index = s.quantity(receipt.get('transactionIndex'))
    if (s.hash32(receipt.get('transactionHash')) != tx or
            s.quantity(receipt.get('blockNumber')) != inclusion['number'] or
            s.hash32(receipt.get('blockHash')) != inclusion['hash'] or
            s.quantity(receipt.get('status')) != 1):
        report['alerts'].append('receipt_changed')

    # eth_getBlockByNumber with false returns transaction hashes, not full objects.
    rpc.keep_transactions = True
    raw = rpc.call('eth_getBlockByNumber', [hex(inclusion['number']), False])
    rpc.keep_transactions = False
    if not isinstance(raw, dict):
        raise w.Error('inclusion block unavailable')
    block = {'number': s.quantity(raw.get('number')), 'hash': s.hash32(raw.get('hash'))}
    transactions = raw.get('transactions')
    if (not isinstance(transactions, list) or len(transactions) > MAX_TRANSACTIONS or
            not all(isinstance(item, str) for item in transactions)):
        raise w.Error('block transaction hash list unavailable or oversized')
    hashes = [s.hash32(item) for item in transactions]
    if block != inclusion:
        report['alerts'].append('inclusion_block_changed')
    if len(set(hashes)) != len(hashes):
        report['alerts'].append('duplicate_transaction_hash')
    if index >= len(hashes) or hashes[index] != tx:
        report['alerts'].append('transaction_missing_at_receipt_index')
    inclusion_reread = s.block(rpc, hex(inclusion['number']))
    head_reread = s.block(rpc, hex(settlement['head']['number']))
    if inclusion_reread != inclusion or head_reread != settlement['head']:
        report['alerts'].append('canonical_anchor_changed')
    report['transactionIndex'] = index
    report['transactionCount'] = len(hashes)
    report['block'] = block
    report['accepted'] = not report['alerts']
    report['state'] = 'position_and_settlement_match' if report['accepted'] else 'review_required'
    return report


def replay(sample, expected):
    expected = policy(expected['transactionHash'], expected['minimumConfirmations'],
                      expected['requireFinalized'])
    if (not isinstance(sample, dict) or set(sample) != {'version', 'source', 'policy', 'reads'} or
            type(sample['version']) is not int or sample['version'] != 1 or
            sample['source'] not in SOURCES or not same_json(sample['policy'], expected)):
        raise w.Error('invalid evidence envelope or policy mismatch')
    rpc = Replay(sample['reads'])
    result = verify(rpc, expected)
    if rpc.index != len(rpc.reads):
        raise w.Error('unused replay reads')
    result['source'] = sample['source']
    result['evidenceMode'] = 'offline replay of historical provider responses'
    result['evidenceLimit'] = ('Provider assertions, not a transaction trie proof or consensus proof; '
                               'historical replay does not establish current settlement.')
    return result


def collect(expected, source=SOURCES[0], rpc_factory=s.RPC):
    expected = policy(expected['transactionHash'], expected['minimumConfirmations'],
                      expected['requireFinalized'])
    if source not in SOURCES:
        raise w.Error('documented public RPC source required')
    rpc = Recorder(rpc_factory(source))
    result = verify(rpc, expected)
    sample = {'version': 1, 'source': source, 'policy': expected, 'reads': rpc.reads}
    if len(json.dumps(sample, separators=(',', ':'), allow_nan=False).encode()) > MAX_EVIDENCE:
        raise w.Error('compact evidence exceeds 90 KB replay bound')
    result['source'] = source
    result['evidenceMode'] = 'live sequential public reads; historical after collection'
    result['sample'] = sample
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--demo', action='store_true')
    mode.add_argument('--replay', help='visible workspace-relative evidence JSON')
    mode.add_argument('--live', action='store_true')
    parser.add_argument('--tx', help='independently selected Ethereum transaction hash')
    parser.add_argument('--confirmations', type=int, default=12)
    parser.add_argument('--allow-unfinalized', action='store_true')
    parser.add_argument('--rpc', choices=SOURCES)
    args = parser.parse_args(argv)
    try:
        if args.demo:
            if args.tx or args.rpc or args.confirmations != 12 or args.allow_unfinalized:
                raise w.Error('demo refuses overrides')
            path = Path(__file__).resolve().parent.relative_to(Path.cwd()) / 'live-evidence.json'
            expected = policy(DEMO_TX, 12, True)
            result = replay(w.load_workspace_json(path), expected)
            result['demoNote'] = 'Real ZTO pool transaction; saved historical evidence, not a current payment decision.'
        else:
            if not args.tx or (args.rpc and not args.live):
                raise w.Error('transaction hash required; --rpc applies only to live collection')
            expected = policy(args.tx, args.confirmations, not args.allow_unfinalized)
            result = (collect(expected, args.rpc or SOURCES[0]) if args.live else
                      replay(w.load_workspace_json(args.replay), expected))
        encoded = json.dumps(result, indent=2, allow_nan=False)
        if len(encoded.encode()) > 100000:
            raise w.Error('report exceeds 100 KB')
        print(encoded)
        return 0 if result['accepted'] else 1
    except (w.Error, ValueError, TypeError, KeyError, OSError, RecursionError):
        print(json.dumps({'accepted': False, 'state': 'input_error',
                          'reason': 'Invalid policy, evidence or unavailable public read'}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
