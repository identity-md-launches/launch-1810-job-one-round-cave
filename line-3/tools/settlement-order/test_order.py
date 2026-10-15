import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('settlement_order_test', HERE / 'order.py')
o = importlib.util.module_from_spec(spec)
spec.loader.exec_module(o)


class OrderTests(unittest.TestCase):
    def setUp(self):
        self.raw = (HERE / 'demo-plan.json').read_bytes()
        self.pin = hashlib.sha256(self.raw).hexdigest()
        self.plan = json.loads(self.raw)
        self.scratch = Path('test/scratch/settlement-order')
        self.scratch.mkdir(parents=True, exist_ok=True)

    def review(self, plan):
        raw = json.dumps(plan).encode()
        return o.review_bytes(raw, hashlib.sha256(raw).hexdigest())

    def cli(self, raw, pin=None):
        path = self.scratch / 'order-plan.json'
        path.write_bytes(raw)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = o.main(['--plan', str(path), '--sha256', pin or hashlib.sha256(raw).hexdigest()])
        return code, json.loads(out.getvalue())

    def rows(self):
        return o.b.review(self.plan['batch'])['items']

    def test_real_zto_order(self):
        result = o.review_bytes(self.raw, self.pin)
        self.assertTrue(result['accepted'])
        self.assertEqual(result['state'], 'settlement_order_match')
        self.assertEqual([p['blockNumber'] for p in result['positions']], [26190898, 26194715])
        self.assertEqual([p['transactionIndex'] for p in result['positions']], [181, 146])

    def test_reverse_sequence_declines(self):
        self.plan['sequence'].reverse()
        code, result = self.cli(json.dumps(self.plan).encode())
        self.assertEqual(code, 1)
        self.assertTrue(result['batch']['accepted'])
        self.assertEqual(result['problems'][0]['kind'], 'required_order_not_met')

    def test_batch_storage_order_irrelevant(self):
        self.plan['batch']['items'].reverse()
        self.assertTrue(self.review(self.plan)['accepted'])

    def test_pin_before_parse_or_evidence(self):
        with patch.object(o.b, 'review', side_effect=AssertionError('evidence opened')):
            result = o.review_bytes(b'not JSON', self.pin)
        self.assertEqual(result['state'], 'plan_pin_mismatch')
        self.assertFalse(result['evidenceChecked'])

    def test_changed_sequence_without_new_pin(self):
        self.plan['sequence'].reverse()
        code, result = self.cli(json.dumps(self.plan).encode(), self.pin)
        self.assertEqual(code, 1)
        self.assertEqual(result['state'], 'plan_pin_mismatch')

    def test_exact_envelope(self):
        variants = [None, [], {}, dict(self.plan, version=True), dict(self.plan, version=2),
                    dict(self.plan, accepted=True)]
        for plan in variants:
            with self.subTest(plan=plan), self.assertRaises(o.Error):
                self.review(plan)

    def test_sequence_exactly_covers_batch(self):
        variants = [[], self.plan['sequence'][:1], self.plan['sequence'] * 17,
                    self.plan['sequence'][0], self.plan['sequence'] + [None]]
        for sequence in variants:
            with self.subTest(sequence=sequence), patch.object(o.b, 'review', side_effect=AssertionError('opened')):
                with self.assertRaises(o.Error):
                    self.review(dict(self.plan, sequence=sequence))

    def test_wrong_sequence_member(self):
        # A genuine hash from an inherited block, deliberately outside this batch.
        evidence = json.loads(Path(self.plan['batch']['items'][0]['evidence']).read_bytes())
        block = next(r['result'] for r in evidence['reads'] if isinstance(r['result'], dict)
                     and 'transactions' in r['result'])
        self.plan['sequence'][1] = block['transactions'][0]
        with self.assertRaises(o.Error):
            self.review(self.plan)

    def test_duplicates_case_insensitive(self):
        tx = self.plan['sequence'][0]
        self.plan['sequence'][1] = '0x' + tx[2:].upper()
        with self.assertRaises(o.Error):
            self.review(self.plan)

    def test_valid_case_aliases_normalized(self):
        self.plan['sequence'] = ['0x' + tx[2:].upper() for tx in self.plan['sequence']]
        self.assertTrue(self.review(self.plan)['accepted'])

    def test_malformed_batch_before_evidence(self):
        self.plan['batch']['items'][1]['policy']['minimumConfirmations'] = True
        with patch.object(o.b, 'review', side_effect=AssertionError('opened')):
            with self.assertRaises(o.Error):
                self.review(self.plan)

    def test_pin_failure_never_checks_order(self):
        self.plan['batch']['items'][1]['sha256'] = self.plan['batch']['items'][0]['sha256']
        with patch.object(o, 'compare_positions', side_effect=AssertionError('ordered unaccepted evidence')):
            result = self.review(self.plan)
        self.assertFalse(result['accepted'])
        self.assertFalse(result['orderChecked'])
        self.assertEqual(result['state'], 'settlement_review_required')

    def test_missing_evidence_exit_two(self):
        self.plan['batch']['items'][1]['evidence'] = 'test/scratch/settlement-order/absent-evidence'
        code, result = self.cli(json.dumps(self.plan).encode())
        self.assertEqual(code, 2)
        self.assertFalse(result['orderChecked'])

    def test_bad_policy_evidence_exit_two(self):
        self.plan['batch']['items'][1]['policy']['minimumConfirmations'] += 1
        self.assertEqual(self.cli(json.dumps(self.plan).encode())[0], 2)

    def test_global_conflict_prevents_order(self):
        batch = o.b.review(self.plan['batch'])
        batch.update(accepted=False, state='review_required', conflictingBlockNumbers=[26190898])
        with patch.object(o.b, 'review', return_value=batch):
            result = o.review_bytes(self.raw, self.pin)
        self.assertFalse(result['accepted'])
        self.assertFalse(result['orderChecked'])

    def test_same_block_index_order(self):
        # Isolate comparison with in-memory mutations, not submitted chain evidence.
        rows = self.rows()
        rows[1]['block'] = copy.deepcopy(rows[0]['block'])
        rows[1]['transactionCount'] = rows[0]['transactionCount']
        rows[1]['transactionIndex'] = rows[0]['transactionIndex'] + 1
        positions, problems = o.compare_positions(rows, self.plan['sequence'])
        self.assertFalse(problems)
        self.assertEqual(positions[0]['blockNumber'], positions[1]['blockNumber'])
        self.assertTrue(o.compare_positions(rows, self.plan['sequence'][::-1])[1])

    def test_same_slot_rejected(self):
        rows = self.rows()
        rows[1]['block'] = copy.deepcopy(rows[0]['block'])
        rows[1]['transactionIndex'] = rows[0]['transactionIndex']
        kinds = [p['kind'] for p in o.compare_positions(rows, self.plan['sequence'])[1]]
        self.assertIn('shared_transaction_position', kinds)
        self.assertIn('required_order_not_met', kinds)

    def test_same_block_count_conflict(self):
        rows = self.rows()
        rows[1]['block'] = copy.deepcopy(rows[0]['block'])
        rows[1]['transactionIndex'] = rows[0]['transactionIndex'] + 1
        kinds = [p['kind'] for p in o.compare_positions(rows, self.plan['sequence'])[1]]
        self.assertIn('block_transaction_count_conflict', kinds)

    def test_strict_json_and_bound(self):
        for raw in (b'{"version":1,"version":1}', b'{"version":NaN}', b'\xff', b' ' * 90001):
            with self.subTest(raw=raw[:40]):
                self.assertEqual(self.cli(raw)[0], 2)
        with self.assertRaises(o.Error):
            o.review_bytes(bytearray(self.raw), self.pin)

    def test_unsafe_path(self):
        for path in ('/outside', '../outside', '.hidden', 'a//b', 'a/./b', 'a\\b'):
            with self.subTest(path=path), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(o.main(['--plan', path, '--sha256', self.pin]), 2)

    def test_symlink_and_directory_refused(self):
        link = self.scratch / 'plan-link'
        if link.is_symlink():
            link.unlink()
        link.symlink_to((HERE / 'demo-plan.json').resolve())
        for path in (link, self.scratch):
            with self.subTest(path=path), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(o.main(['--plan', str(path), '--sha256', self.pin]), 2)

    def test_invalid_hash_before_plan_open(self):
        with patch.object(o.b.k, 'load_bytes', side_effect=AssertionError('opened')):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(o.main(['--plan', 'irrelevant', '--sha256', 'bad']), 2)

    def test_cli_missing_and_demo_overrides(self):
        for args in ([], ['--plan', 'missing'], ['--demo', '--sha256', self.pin],
                     ['--demo', '--plan', 'missing']):
            with self.subTest(args=args), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(o.main(args), 2)

    def test_offline_immutable_demo(self):
        files = [HERE / 'demo-plan.json', HERE / 'demo-plan.sha256'] + [
            Path(i['evidence']) for i in self.plan['batch']['items']]
        before = [p.read_bytes() for p in files]
        with patch.object(o.b.k.p.s.RPC, 'call', side_effect=AssertionError('network')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(o.main(['--demo']), 0)
        self.assertEqual([p.read_bytes() for p in files], before)
        self.assertLess(len(output.getvalue().encode()), 100000)
        self.assertTrue(json.loads(output.getvalue())['accepted'])


if __name__ == '__main__':
    unittest.main()
