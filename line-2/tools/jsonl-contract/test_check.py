"""JSON Lines framing, diagnostics, boundary and offline integration checks."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('jsonl_check', Path(__file__).with_name('check.py'))
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)


class Reader:
    def __init__(self, files):
        self.files, self.reads = files, []

    def read_bytes(self, name):
        self.reads.append(name)
        return self.files[name]


class JsonLinesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reader, cls.source, cls.engine, cls.rules = check.dependencies()
        Path('test/scratch').mkdir(parents=True, exist_ok=True)

    def review(self, contract, document, **pins):
        reader = Reader({'c': contract, 'd': document})
        return check.inspect(reader, self.source, self.engine, self.rules, 'c', 'd', **pins)

    def test_mixed_rows_continue_and_keep_error_order(self):
        c = Path('line-2/tools/json-contract/report.contract.json').read_bytes()
        bad = json.loads(Path('line-2/tools/rule-locator/report.invalid.json').read_bytes())
        good = json.loads(Path('line-2/tools/json-contract/report.example.json').read_bytes())
        data = (json.dumps(good) + '\n' + json.dumps(bad) + '\n{\n' + json.dumps(good)).encode()
        result = self.review(c, data)
        self.assertEqual(result['summary'], {'rows': 4, 'passed': 2, 'violated': 1,
                                             'malformed': 1, 'structural_errors': 3})
        self.assertEqual([r['status'] for r in result['rows']],
                         ['valid', 'violations', 'malformed', 'valid'])
        expected = self.engine.validate(bad, json.loads(c))
        self.assertEqual([{k: e[k] for k in ('path', 'rule', 'message')}
                          for e in result['rows'][1]['errors']], expected)
        self.assertTrue(result['complete'])
        self.assertFalse(result['valid'])

    def test_unicode_crlf_global_spans_and_key_spans(self):
        c = '{"type":"object","properties":{"🐸":{"type":"integer"}}}'.encode()
        data = '{"🐸":1}\r\n\t{"🐸":"日"}\r\n'.encode()
        report = self.review(c, data)
        error = report['rows'][1]['errors'][0]
        loc = error['document_source']
        span = loc['value']
        self.assertEqual(span['start']['line'], 2)
        self.assertEqual(span['start']['column'], 7)
        self.assertEqual(data[span['start']['byte_offset']:span['end']['byte_offset']], '"日"'.encode())
        text = data.decode()
        self.assertEqual(text[span['start']['char_offset']:span['end']['char_offset']], '"日"')
        key = loc['key']
        self.assertEqual(data[key['start']['byte_offset']:key['end']['byte_offset']], '"🐸"'.encode())
        rule = error['contract_source']['value']
        self.assertEqual(c[rule['start']['byte_offset']:rule['end']['byte_offset']], b'"integer"')
        row = report['rows'][1]
        self.assertEqual(data[row['byte_start']:row['byte_end']], '\t{"🐸":"日"}\r'.encode())
        self.assertEqual(row['sha256'], hashlib.sha256(data[row['byte_start']:row['byte_end']]).hexdigest())

    def test_missing_and_null_are_distinct(self):
        c = b'{"type":"object","required":["a/b~"],"properties":{"a/b~":{"type":"integer"}}}'
        data = b'{}\n{"a/b~":null}\n'
        result = self.review(c, data)
        missing, present = [row['errors'][0] for row in result['rows']]
        self.assertEqual(missing['path'], '/a~1b~0')
        self.assertFalse(missing['document_source']['present'])
        self.assertEqual(missing['document_source']['anchor']['value']['end']['byte_offset'], 2)
        loc = present['document_source']
        self.assertTrue(loc['present'])
        self.assertEqual(data[loc['value']['start']['byte_offset']:loc['value']['end']['byte_offset']], b'null')

    def test_terminal_newline_not_blank_but_other_blank_rows_reject(self):
        for data in (b'1', b'1\n', b'1\r\n'):
            self.assertEqual(self.review(b'{"type":"integer"}', data)['summary']['rows'], 1)
        for data in (b'1\n\n', b'1\n \n', b'\n1', b'\r\n1'):
            result = self.review(b'{"type":"integer"}', data)
            self.assertEqual(result['summary']['malformed'], 1)
            self.assertEqual(result['summary']['passed'], 1)
        self.assertEqual(self.review(b'{"type":"null"}', b'\n')['summary']['malformed'], 1)

    def test_only_literal_lf_separates_rows(self):
        data = '"x\\ny"\n"a\u2028b\u2029c"\n"z"'.encode()
        result = self.review(b'{"type":"string"}', data)
        self.assertTrue(result['valid'])
        self.assertEqual(result['summary']['rows'], 3)
        for data in (b'1\r2', b'1\x0b2', b'1\x0c2'):
            result = self.review(b'{"type":"integer"}', data)
            self.assertEqual(result['summary']['rows'], 1)
            self.assertEqual(result['summary']['malformed'], 1)

    def test_scalar_and_array_rows_supported(self):
        self.assertTrue(self.review(b'{"type":"null"}', b'null\nnull')['valid'])
        report = self.review(b'{"type":"array","items":{"type":"integer"}}', b'[]\n[1,"x"]')
        self.assertEqual(report['rows'][1]['errors'][0]['path'], '/1')

    def test_syntax_point_is_whole_file_and_zero_width(self):
        data = '"🐸"\r\n{"日":}\n"ok"'.encode()
        result = self.review(b'{"type":"string"}', data)
        error = result['rows'][1]['parse_error']
        self.assertEqual(error['kind'], 'syntax_point')
        self.assertEqual(error['span']['start'], error['span']['end'])
        start = error['span']['start']
        self.assertEqual(start['line'], 2)
        self.assertEqual(data[start['byte_offset']:start['byte_offset']+1], b'}')

    def test_strict_json_rejections_continue(self):
        for raw in (b'{"a":1,"a":2}', b'NaN', b'Infinity', b'-Infinity', b'1e999'):
            result = self.review(b'{"type":"object"}', raw+b'\n{}')
            self.assertEqual(result['rows'][0]['status'], 'malformed')
            self.assertEqual(result['rows'][0]['parse_error']['kind'], 'row_anchor')
            self.assertEqual(result['rows'][1]['status'], 'valid')

    def test_bom_and_pretty_printed_json_reject(self):
        result = self.review(b'{"type":"object"}', b'\xef\xbb\xbf{}\n{}')
        self.assertEqual(result['summary']['malformed'], 1)
        result = self.review(b'{"type":"object"}', b'{\n"x":1\n}')
        self.assertEqual(result['summary']['malformed'], 3)

    def test_invalid_utf8_empty_and_row_limit_fail_whole_input(self):
        for raw in (b'', b'{}\n"\xff"', b'null\n'*257):
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                self.review(b'{"type":"null"}', raw)
        result = self.review(b'{"type":"null"}', b'null\n'*256)
        self.assertEqual(result['summary']['passed'], 256)

    def test_contract_prepared_before_document_read(self):
        for raw in (b'{', b'{"type":"integer","typo":1}'):
            reader = Reader({'c': raw})
            with self.assertRaises(ValueError):
                check.inspect(reader, self.source, self.engine, self.rules, 'c', 'never')
            self.assertEqual(reader.reads, ['c'])

    def test_pins_before_parsing_and_exact_whole_bytes(self):
        c, d = b'{"type":"integer"}', b'1\r\n2\n'
        result = self.review(c, d, contract_sha256=hashlib.sha256(c).hexdigest(),
                             document_sha256=hashlib.sha256(d).hexdigest())
        self.assertTrue(result['valid'])
        self.assertEqual(result['sources']['document']['sha256'], hashlib.sha256(d).hexdigest())
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            self.review(c, d.replace(b'\r', b''), document_sha256=hashlib.sha256(d).hexdigest())
        reader = Reader({})
        with self.assertRaises(ValueError):
            check.inspect(reader, self.source, self.engine, self.rules, 'c', 'd', 'bad')
        self.assertEqual(reader.reads, [])
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            self.review(b'{', d, contract_sha256=hashlib.sha256(c).hexdigest())

    def test_identical_paths_capture_once(self):
        reader = Reader({'same': b'{"type":"object"}\n'})
        result = check.inspect(reader, self.source, self.engine, self.rules, 'same', 'same')
        self.assertEqual(reader.reads, ['same'])
        self.assertTrue(result['valid'])

    def test_ascii_safe_output_and_determinism(self):
        data = json.dumps({'\x1b[31m\u202e': 1}).encode()+b'\n'
        report = self.review(b'{"type":"object","additionalProperties":false}', data)
        output = check.encode(report)
        self.assertTrue(output.isascii())
        self.assertNotIn('\x1b', output)
        self.assertIn('\\u001b', output)
        self.assertEqual(output, check.encode(self.review(b'{"type":"object","additionalProperties":false}', data)))

    def test_output_overflow_has_no_partial_stdout(self):
        report = self.review(b'{"type":"integer"}', b'"x"\n')
        out, err = io.StringIO(), io.StringIO()
        with patch.object(check, 'MAX_OUTPUT_BYTES', 100), patch.object(check, 'inspect', return_value=report), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = check.main(['c', 'd'])
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), '')
        self.assertFalse(json.loads(err.getvalue())['complete'])
        report = self.review(b'{"type":"integer"}', b'"x"\n'*100)
        self.assertEqual(report['summary']['structural_errors'], 100)
        with self.assertRaisesRegex(ValueError, 'no report emitted'):
            check.encode(report)

    def test_saved_zto_policy_with_network_disabled(self):
        c = 'shared/payment-evidence/policy.contract.json'
        d = 'line-2/tools/jsonl-contract/zto-policy.jsonl'
        with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            report = check.inspect(*check.dependencies(), c, d)
        self.assertTrue(report['valid'])
        self.assertEqual(report['summary']['rows'], 1)
        self.assertEqual(json.loads(Path(d).read_bytes()),
                         json.loads(Path('shared/payment-evidence/example.policy.json').read_bytes()))

    def test_nofollow_hidden_absolute_parent_and_special_paths(self):
        with tempfile.TemporaryDirectory(dir='test/scratch') as root:
            target, link = Path(root)/'target', Path(root)/'link'
            target.write_bytes(b'null\n')
            link.symlink_to(target.name)
            for name in (str(link.relative_to(Path.cwd())), '../outside', '.hidden', str(target),
                         str(target.parent.relative_to(Path.cwd()))):
                with self.subTest(name=name), self.assertRaises((ValueError, OSError)):
                    check.inspect(self.reader, self.source, self.engine, self.rules,
                                  'line-2/tools/json-contract/report.contract.json', name)

    def test_cli_codes_complete_reports_and_immutability(self):
        with tempfile.TemporaryDirectory(dir='test/scratch') as root:
            c, d = Path(root)/'c', Path(root)/'d'
            c.write_bytes(b'{"type":"integer"}')
            for data, expected in ((b'1\n2\n', 0), (b'1\n"bad"\n', 1),
                                   (b'{\n2\n', 2), (b'', 2), (b'"\xff"', 2)):
                d.write_bytes(data)
                result = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('check.py')),
                                         str(c.relative_to(Path.cwd())), str(d.relative_to(Path.cwd()))],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stdout+result.stderr)
                if not data or b'\xff' in data:
                    self.assertEqual(result.stdout, '')
                    self.assertFalse(json.loads(result.stderr)['complete'])
                else:
                    report = json.loads(result.stdout)
                    self.assertTrue(report['complete'])
                    self.assertEqual(result.stderr, '')
                self.assertEqual(c.read_bytes(), b'{"type":"integer"}')
                self.assertEqual(d.read_bytes(), data)


if __name__ == '__main__':
    unittest.main(verbosity=2)
