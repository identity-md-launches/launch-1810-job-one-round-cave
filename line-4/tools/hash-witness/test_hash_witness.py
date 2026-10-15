"""Offline known vectors, adversarial witnesses, reader boundaries and CLI checks."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import hash_witness as witness
from keccak_check import keccak256, _sponge

HERE = Path(__file__).resolve().parent
ZTO = '0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774'
MAIL = '0xbe609aee343fb3c4b28e1df9e632fca64fcfaede20f02e86244efddf30957bd2'


def fixture(name='zto'):
    return json.loads((HERE / (name + '-trace.json')).read_bytes())


def node(trace, path):
    return next(n for n in trace['nodes'] if n['path'] == path)


class HashTests(unittest.TestCase):
    def test_ethereum_empty_and_abc_vectors(self):
        for raw, expected in [(b'', 'c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470'),
                              (b'abc', '4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45')]:
            self.assertEqual(keccak256(raw).hex(), expected)
            self.assertNotEqual(keccak256(raw), hashlib.sha3_256(raw).digest())

    def test_permutation_and_padding_with_independent_hashlib(self):
        # Same sponge/permutation, SHA3 suffix only for this differential test.
        for size in (0, 1, 31, 32, 64, 134, 135, 136, 137, 270, 271, 272, 273, 4096):
            for fill in (b'\0', b'\xff', bytes(range(256))):
                with self.subTest(size=size, fill=fill[:2]):
                    message = (fill * (size // len(fill) + 1))[:size]
                    self.assertEqual(_sponge(message, 6), hashlib.sha3_256(message).digest())

    def test_hash_requires_bytes(self):
        with self.assertRaises(ValueError):
            keccak256('abc')


class WitnessTests(unittest.TestCase):
    def rejected(self, report):
        with self.assertRaises(ValueError):
            witness.verify(report, ZTO)

    def test_historical_zto_trace(self):
        result = witness.verify(fixture(), ZTO)
        self.assertTrue(result['witnessValid'])
        self.assertTrue(result['matchesExpected'])
        self.assertEqual((result['nodesChecked'], result['hashesChecked']), (12, 7))
        self.assertFalse(result['sourceTypedDataChecked'])

    def test_published_ether_mail(self):
        result = witness.verify(fixture('ether-mail'), MAIL)
        self.assertTrue(result['matchesExpected'])

    def test_empty_nested_recursive_dynamic_and_scalar_edges(self):
        report = fixture('edge')
        result = witness.verify(report, report['digest'])
        self.assertTrue(result['matchesExpected'])
        self.assertEqual(node(report, '/message/tree/children/0/children')['preimage'], '0x')
        self.assertIn('Pod(bytes32 hidden)', report['typeEncoding'])

    def test_valid_trace_expected_mismatch(self):
        result = witness.verify(fixture(), MAIL)
        self.assertTrue(result['witnessValid'])
        self.assertFalse(result['matchesExpected'])

    def test_ancestor_match_flag_never_controls_result(self):
        for flag in (True, False):
            data = fixture()
            data['matchesExpected'] = flag
            self.assertFalse(witness.verify(data, MAIL)['matchesExpected'])
            self.assertTrue(witness.verify(data, ZTO)['matchesExpected'])

    def test_no_input_mutation(self):
        data = fixture()
        prior = copy.deepcopy(data)
        witness.verify(data, ZTO)
        self.assertEqual(data, prior)

    def test_every_hash_and_preimage_tampering_rejected(self):
        original = fixture()
        for i, n in enumerate(original['nodes']):
            for field in ('word', 'preimage', 'typeHash'):
                if field not in n:
                    continue
                with self.subTest(path=n['path'], field=field):
                    data = copy.deepcopy(original)
                    old = data['nodes'][i][field]
                    data['nodes'][i][field] = old[:-2] + ('ff' if old[-2:] != 'ff' else '00')
                    self.rejected(data)

    def test_bad_lengths_and_boolean_offsets_rejected(self):
        for path in ('/domain', '/message'):
            for field, value in [('preimageBytes', True), ('preimageBytes', 0)]:
                data = fixture()
                node(data, path)[field] = value
                self.rejected(data)
        data = fixture()
        node(data, '/message')['fields'][0]['offsetBytes'] = True
        self.rejected(data)

    def test_child_path_word_type_and_order_rejected(self):
        for field, value in [('path', '/domain/name'), ('type', 'bytes'), ('word', ZTO), ('name', 'token')]:
            data = fixture()
            node(data, '/message')['fields'][0][field] = value
            self.rejected(data)
        data = fixture()
        node(data, '/message')['fields'].reverse()
        self.rejected(data)

    def test_atomic_normalization_and_ranges(self):
        for path, values in [('/message/requireFinalized', [1, 'true']),
                             ('/message/minimumRaw', ['-1', '01', 12, str(2**256)]),
                             ('/message/token', ['0x12', None]),
                             ('/message/transactionHash', ['0x12'])]:
            for value in values:
                data = fixture()
                node(data, path)['normalizedValue'] = value
                self.rejected(data)
        for bad in ('-129', '128', '-0'):
            data = fixture('edge')
            node(data, '/message/signed')['normalizedValue'] = bad
            self.rejected(data)

    def test_fixed_bytes_padding_not_address_padding(self):
        data = fixture('edge')
        node(data, '/message/fixed')['word'] = '0x' + '00' * 30 + '12ab'
        self.rejected(data)

    def test_array_order_offsets_lengths_and_child_reuse(self):
        for change in ('order', 'offset', 'fixed_length', 'duplicate'):
            data = fixture('edge')
            n = node(data, '/message/nested/0')
            if change == 'order':
                n['elements'].reverse()
            elif change == 'offset':
                n['elements'][1]['offsetBytes'] = 0
            elif change == 'fixed_length':
                n['elements'].pop()
            else:
                n['elements'][1] = copy.deepcopy(n['elements'][0])
            self.rejected(data)

    def test_orphan_duplicate_missing_and_forward_nodes(self):
        data = fixture()
        extra = copy.deepcopy(node(data, '/message/token'))
        extra['path'] = '/message/unconnected'
        data['nodes'].insert(0, extra)
        self.rejected(data)
        data = fixture()
        data['nodes'].append(copy.deepcopy(data['nodes'][0]))
        self.rejected(data)
        data = fixture()
        data['nodes'].pop(0)
        self.rejected(data)
        data = fixture()
        data['nodes'].reverse()
        self.rejected(data)

    def test_schema_dependency_order_unused_missing_and_field_order(self):
        valid = 'Root(A[] a,B b)A(uint8 x)B(string y)'
        self.assertEqual(set(witness.declarations(valid, 'Root')), {'Root', 'A', 'B'})
        for invalid in ('Root(A[] a,B b)B(string y)A(uint8 x)',
                        'Root(A[] a,B b)A(uint8 x)',
                        valid + 'Unused()', 'Root(uint8 x,uint8 x)',
                        'Root(uint8  x)', 'Root(int999 x)int999()',
                        'Root(bytes33 x)bytes33()', 'Root(uint8[0] x)'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                witness.declarations(invalid, 'Root')
        data = fixture()
        node(data, '/message')['typeEncoding'] = node(data, '/message')['typeEncoding'].replace('address token', 'bytes20 token')
        self.rejected(data)

    def test_conflicting_dependency_declarations(self):
        data = fixture('edge')
        n = node(data, '/message/tree/children/0')
        # Hash valid alternate type and word; global schema agreement still fails.
        n['typeEncoding'] = 'Node(Node[] other)'
        n['fields'][0]['name'] = 'other'
        n['typeHash'] = '0x' + keccak256(n['typeEncoding'].encode()).hex()
        self.rejected(data)

    def test_envelope_and_summary_tampering(self):
        for field, value in [('prefix', '0x1900'), ('domainOffsetBytes', 34),
                             ('messageOffsetBytes', 2), ('preimageBytes', 65),
                             ('digest', MAIL), ('preimage', '0x')]:
            data = fixture()
            data['envelope'][field] = value
            self.rejected(data)
        for field in ('digest', 'domainSeparator', 'messageHash'):
            data = fixture()
            data[field] = MAIL
            self.rejected(data)

    def test_version_roles_unknown_members_and_root_type(self):
        for field, value in [('traceVersion', True), ('nodeOrder', 'parents first'), ('primaryType', 'EIP712Domain')]:
            data = fixture()
            data[field] = value
            self.rejected(data)
        data = fixture()
        data['surprise'] = True
        self.rejected(data)
        data = fixture()
        node(data, '/message/token')['kind'] = 'struct'
        self.rejected(data)

    def test_dynamic_utf8_and_byte_count(self):
        data = fixture('edge')
        n = node(data, '/message/unicode')
        n['preimage'] = '0xff'
        n['inputBytes'] = n['preimageBytes'] = 1
        n['word'] = '0x' + keccak256(b'\xff').hex()
        self.rejected(data)
        data = fixture('edge')
        node(data, '/message/binary')['inputBytes'] = 0
        self.rejected(data)

    def test_hash_and_node_limits_fail_closed(self):
        with patch.object(witness, 'MAX_HASH_BYTES', 64), self.assertRaisesRegex(ValueError, 'hash work'):
            witness.verify(fixture(), ZTO)
        with patch.object(witness, 'MAX_NODES', 2), self.assertRaisesRegex(ValueError, 'node count'):
            witness.verify(fixture(), ZTO)

    def test_expected_hex_validation(self):
        for expected in (None, '0x1', '0x', '0x' + 'zz' * 32, True):
            with self.subTest(expected=expected), self.assertRaises(ValueError):
                witness.verify(fixture(), expected)

    def test_raw_json_depth_duplicates_floats_unicode_and_cycles(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":1.0}', b'{"x":NaN}', b'"\\ud800"',
                    b'[' * 49 + b']' * 49, b'\xff', b'{}' + b' ' * witness.MAX_BYTES):
            with self.subTest(raw=raw[:60]), self.assertRaises(ValueError):
                witness.loads(raw)
        data = []; data.append(data)
        with self.assertRaises(ValueError):
            witness.validate_tree(data)

    def test_malformed_json_values_fail_without_type_errors(self):
        original = fixture()
        for field in original:
            for value in (None, [], {}, True, 1, ''):
                if type(value) is type(original[field]) and value == original[field]:
                    continue
                data = copy.deepcopy(original)
                data[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    witness.verify(data, ZTO)

    def test_malformed_node_members_never_escape_as_type_errors(self):
        original = fixture()
        for i, n in enumerate(original['nodes']):
            for field in n:
                for value in (None, [], {}, True, 1, ''):
                    data = copy.deepcopy(original)
                    data['nodes'][i][field] = value
                    with self.subTest(path=n['path'], field=field, value=value):
                        try:
                            witness.verify(data, ZTO)
                        except ValueError:
                            pass


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def test_reader_regular_and_absolute_inside_workspace(self):
        p = self.folder/'trace.json'
        p.write_bytes((HERE/'zto-trace.json').read_bytes())
        self.assertTrue(witness.verify(witness.read_workspace(p), ZTO)['matchesExpected'])
        self.assertEqual(witness.read_workspace(p), witness.read_workspace(p.absolute()))

    def test_reader_hidden_traversal_symlinks_directory_fifo_size(self):
        p = self.folder/'trace.json'
        p.write_text('{}')
        link = self.folder/'link.json'
        link.symlink_to('trace.json')
        dirlink = self.folder/'linked-dir'
        dirlink.symlink_to('.', target_is_directory=True)
        hidden = self.folder/'.hidden'; hidden.write_text('{}')
        large = self.folder/'large'; large.write_bytes(b' ' * (witness.MAX_BYTES + 1))
        fifo = self.folder/'fifo'
        witness.os.mkfifo(fifo)
        for name in (link, dirlink/'trace.json', hidden, large, fifo, self.folder,
                     '../outside.json', '/not-this-workspace/missing.json'):
            with self.subTest(name=str(name)), self.assertRaises((ValueError, OSError)):
                witness.read_workspace(name)

    def test_cli_success_mismatch_and_malformed(self):
        script = str(HERE/'hash_witness.py')
        for name, expected, code in [('zto-trace.json', ZTO, 0), ('zto-trace.json', MAIL, 1),
                                     ('zto-trace.json', '0x1', 2)]:
            p = subprocess.run([sys.executable, '-B', script, str(HERE/name), '--expect', expected],
                               capture_output=True, text=True, timeout=20)
            self.assertEqual(p.returncode, code, p.stderr)
            if code == 2:
                self.assertEqual(p.stdout, '')
            else:
                self.assertEqual(json.loads(p.stdout)['matchesExpected'], code == 0)
        bad = self.folder/'bad.json'; bad.write_text('{"traceVersion":1}')
        p = subprocess.run([sys.executable, '-B', script, str(bad), '--expect', ZTO],
                           capture_output=True, text=True, timeout=20)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(p.stdout, '')
        self.assertNotIn('Traceback', p.stderr)

    def test_no_network_dependencies(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            self.assertTrue(witness.verify(fixture(), ZTO)['matchesExpected'])


if __name__ == '__main__':
    unittest.main()
