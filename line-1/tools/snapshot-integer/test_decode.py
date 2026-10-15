"""Offline integer boundaries, interpretation choices and saved-evidence replay."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

D = runpy.run_path(str(Path(__file__).with_name('decode.py')))
SAMPLE = 'line-1/tools/bounded-rpc-snapshot/sample-zto-supply.json'
BLOCK = 'line-1/tools/snapshot-select/live-block.json'


class DecodeTests(unittest.TestCase):
    def test_fresh_saved_zto_offline(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network')):
            snapshot = D['S']['B']['verify_snapshot'](
                'line-1/tools/snapshot-integer/live-zto.json')
            result = D['report'](snapshot, '', 'uint256', 18)
        self.assertEqual(result['decoded']['raw_decimal'], str(10**27))
        self.assertEqual(snapshot['request']['params'],
                         [{'to': D['S']['B']['ZTO'], 'data': '0x18160ddd'}, 'latest'])

    def test_real_zto_offline(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network')):
            snapshot = D['S']['B']['verify_snapshot'](SAMPLE)
            before = copy.deepcopy(snapshot)
            result = D['report'](snapshot, '', 'uint256', 18)
        self.assertEqual(result['decoded']['raw_decimal'], str(10**27))
        self.assertEqual(result['decoded']['fixed_decimal'], '1000000000.000000000000000000')
        self.assertEqual(result['selection']['request']['params'][0]['to'], D['S']['B']['ZTO'])
        self.assertEqual(snapshot, before)

    def test_real_block_quantity(self):
        snapshot = D['S']['B']['verify_snapshot'](BLOCK)
        self.assertEqual(D['report'](snapshot, '/number', 'quantity', 0)
                         ['decoded']['raw_decimal'], '26195002')

    def test_quantity_boundaries(self):
        for number in (0, 1, 15, 16, 2**255, 2**256-1):
            self.assertEqual(D['decode'](hex(number), 'quantity')['raw_decimal'], str(number))
        self.assertEqual(D['decode']('0xAB', 'quantity')['raw_decimal'], '171')

    def test_quantity_rejects_noncanonical(self):
        for value in ('0x', '0x00', '0x01', '0X1', '-0x1', '1', '0xg', '0x1 ',
                      '0x1\n', '0x'+'f'*65, '0x'+'f'*100000):
            with self.subTest(value=value[:70]), self.assertRaises(ValueError):
                D['decode'](value, 'quantity')

    def test_word_width_and_syntax(self):
        for value in ('0x0', '0x'+'0'*63, '0x'+'0'*65, '0x'+'g'*64,
                      '0X'+'a'*64, '0x'+'a'*64+'\n'):
            for kind in ('uint256', 'int256'):
                with self.subTest(value=value, kind=kind), self.assertRaises(ValueError):
                    D['decode'](value, kind)

    def test_signed_boundaries(self):
        for number in (-(2**255), -1, 0, 1, 2**255-1):
            word = '0x'+format(number % 2**256, '064x')
            self.assertEqual(D['decode'](word, 'int256')['raw_decimal'], str(number))

    def test_unsigned_and_signed_are_explicit(self):
        word = '0x'+'f'*64
        self.assertEqual(D['decode'](word, 'uint256')['raw_decimal'], str(2**256-1))
        self.assertEqual(D['decode'](word, 'int256')['raw_decimal'], '-1')
        with self.assertRaises(ValueError):
            D['decode'](word, 'auto')

    def test_exact_scale(self):
        for number, decimals, expected in ((1, 18, '0.000000000000000001'),
                                          (101, 2, '1.01'), (0, 3, '0.000'),
                                          (10, 0, '10'), (-1, 3, '-0.001')):
            word = '0x'+format(number % 2**256, '064x')
            self.assertEqual(D['decode'](word, 'int256', decimals)['fixed_decimal'], expected)
        self.assertEqual(D['decode']('0x1', 'quantity', 255)['fixed_decimal'],
                         '0.'+'0'*254+'1')

    def test_invalid_scale(self):
        for value in (-1, 256, True, 1.0, '18', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                D['decode']('0x1', 'quantity', value)

    def test_nonstring_selected_values(self):
        for value in (None, True, 0, 1.5, [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                D['decode'](value, 'quantity')

    def test_cli_success_and_no_file_changes(self):
        before = Path(SAMPLE).read_bytes()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(D['main']([SAMPLE, '--encoding', 'uint256', '--decimals', '18']), 0)
        self.assertEqual(json.loads(output.getvalue())['decoded']['raw_decimal'], str(10**27))
        self.assertEqual(Path(SAMPLE).read_bytes(), before)
        self.assertLess(len(output.getvalue().encode()), 100000)

    def test_cli_rejects_without_partial_output(self):
        for args in ([SAMPLE, '--encoding', 'quantity'],
                     [SAMPLE, '--encoding', 'uint256', '--decimals', '-1'],
                     [SAMPLE, '--encoding', 'uint256', '--pointer', '/missing'],
                     [BLOCK, '--encoding', 'quantity', '--pointer', '/transactions'],
                     ['../outside', '--encoding', 'quantity'],
                     ['/outside', '--encoding', 'quantity']):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(D['main'](args), 1)
            self.assertEqual(out.getvalue(), '')
            self.assertTrue(err.getvalue().startswith('snapshot-integer:'))

    def test_cli_requires_explicit_encoding(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
            D['main']([SAMPLE])
        self.assertEqual(exc.exception.code, 2)

    def test_tampered_strict_json_and_symlinks(self):
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir='test/scratch') as tmp:
            path = Path(tmp).resolve().relative_to(Path.cwd())/'snapshot.json'
            original = json.loads(Path(SAMPLE).read_text())
            changed = copy.deepcopy(original)
            changed['response']['result'] = '0x'+'f'*64
            for raw in (json.dumps(changed), '{"a":1,"a":2}', '{"a":NaN}'):
                path.write_text(raw)
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(D['main']([str(path), '--encoding', 'uint256']), 1)
            path.write_text(json.dumps(original))
            link = path.with_name('link.json')
            link.symlink_to('snapshot.json')
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(D['main']([str(link), '--encoding', 'uint256']), 1)

    def test_consistently_resealed_evidence_is_not_proof(self):
        # Document the trust boundary: a checksum does not authenticate a provider.
        snapshot = D['S']['B']['verify_snapshot'](SAMPLE)
        snapshot['response']['result'] = '0x'+format(42, '064x')
        canonical = json.dumps(snapshot['response'], sort_keys=True, separators=(',', ':'),
                               ensure_ascii=False).encode()
        snapshot['response_sha256'] = hashlib.sha256(canonical).hexdigest()
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir='test/scratch') as tmp:
            path = Path(tmp).resolve().relative_to(Path.cwd())/'resealed.json'
            path.write_text(json.dumps(snapshot))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(D['main']([str(path), '--encoding', 'uint256']), 0)
            self.assertEqual(json.loads(output.getvalue())['decoded']['raw_decimal'], '42')


if __name__ == '__main__':
    unittest.main()
