"""Integration checks using retained real ZTO evidence and explicit refusals."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ordered_gate_test', HERE / 'review.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.raw = (HERE / 'plan.json').read_bytes()
        self.pin = (HERE / 'plan.sha256').read_text().strip()
        self.plan = json.loads(self.raw)

    def review(self, plan):
        raw = (json.dumps(plan) + '\n').encode()
        return g.review(raw, hashlib.sha256(raw).hexdigest())

    def test_real_zto_order(self):
        r = g.review(self.raw, self.pin)
        self.assertTrue(r['accepted'])
        self.assertTrue(r['structure']['valid'])
        self.assertEqual(r['state'], 'settlement_order_match')
        self.assertEqual([x['blockNumber'] for x in r['orderReview']['positions']],
                         [26190898, 26194715])

    def test_reverse_order_declines_after_settlement(self):
        self.plan['sequence'].reverse()
        r = self.review(self.plan)
        self.assertFalse(r['accepted'])
        self.assertTrue(r['orderReview']['batch']['accepted'])
        self.assertEqual(r['state'], 'order_review_required')

    def test_storage_order_irrelevant(self):
        self.plan['batch']['items'].reverse()
        self.assertTrue(self.review(self.plan)['accepted'])

    def test_replaced_plan_before_parse(self):
        with patch.object(g.order, 'review_bytes', side_effect=AssertionError('replayed')):
            r = g.review(b'not JSON', self.pin)
        self.assertFalse(r['evidenceChecked'])
        self.assertNotIn('structure', r)

    def test_diagnostics_before_evidence(self):
        self.plan['batch']['items'][1]['policy']['requireFinalized'] = 'yes'
        with patch.object(g.order, 'review_bytes', side_effect=AssertionError('replayed')):
            r = self.review(self.plan)
        self.assertFalse(r['accepted'])
        self.assertEqual(r['structure']['diagnostics'][0]['path'],
                         '/batch/items/1/policy/requireFinalized')
        self.assertFalse(r['evidenceChecked'])

    def test_partial_sequence_rejected(self):
        self.plan['sequence'].pop()
        self.assertEqual(self.review(self.plan)['state'], 'structural_review_required')

    def test_case_alias_duplicate_rejected(self):
        self.plan['sequence'][1] = '0x' + self.plan['sequence'][0][2:].upper()
        with patch.object(g.order.b, 'review', side_effect=AssertionError('opened')):
            with self.assertRaises(g.order.Error):
                self.review(self.plan)

    def test_evidence_pin_failure_never_orders(self):
        self.plan['batch']['items'][1]['sha256'] = self.plan['batch']['items'][0]['sha256']
        with patch.object(g.order, 'compare_positions', side_effect=AssertionError('ordered')):
            r = self.review(self.plan)
        self.assertFalse(r['accepted'])
        self.assertFalse(r['orderChecked'])

    def test_missing_evidence_no_partial_acceptance(self):
        self.plan['batch']['items'][1]['evidence'] = 'test/scratch/ordered-gate-missing.json'
        r = self.review(self.plan)
        self.assertFalse(r['accepted'])
        self.assertEqual(r['state'], 'input_error')

    def test_client_cannot_supply_acceptance(self):
        self.plan['accepted'] = True
        r = self.review(self.plan)
        self.assertEqual(r['state'], 'structural_review_required')
        self.assertEqual(r['structure']['diagnostics'][0]['path'], '/accepted')

    def test_strict_json_and_bounds(self):
        for raw in (b'{"version":1,"version":1}', b'{"version":NaN}', b'\xff', b' ' * 90001):
            with self.subTest(raw=raw[:30]), self.assertRaises((ValueError, g.order.Error)):
                g.review(raw, hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError):
            g.review(bytearray(self.raw), self.pin)

    def test_output_bound(self):
        with self.assertRaises(ValueError):
            g.render({'message': 'x' * 100000})

    def test_unsafe_paths_before_open(self):
        for path in ('/outside', '../outside', '.hidden', 'a//b', 'a/./b'):
            with self.subTest(path=path), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(g.main([path, '--sha256', self.pin]), 2)

    def test_invalid_pin_before_read(self):
        with patch.object(g.order.b.k, 'load_bytes', side_effect=AssertionError('opened')):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(g.main(['irrelevant', '--sha256', 'invalid']), 2)

    def test_cli_accepts_and_is_offline_immutable(self):
        files = [HERE / 'plan.json', HERE / 'plan.sha256'] + [
            Path(i['evidence']) for i in self.plan['batch']['items']]
        before = [p.read_bytes() for p in files]
        plan_before = copy.deepcopy(self.plan)
        with patch.object(g.order.b.k.p.s.RPC, 'call', side_effect=AssertionError('network')):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(g.main([str((HERE / 'plan.json').relative_to(Path.cwd())),
                                         '--sha256', self.pin]), 0)
        self.assertTrue(json.loads(out.getvalue())['accepted'])
        self.assertLess(len(out.getvalue().encode()), 100000)
        self.assertEqual(before, [p.read_bytes() for p in files])
        self.assertEqual(plan_before, self.plan)


if __name__ == '__main__':
    unittest.main(verbosity=2)
