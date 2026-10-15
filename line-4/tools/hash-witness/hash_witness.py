#!/usr/bin/env python3
"""Independently verify the bytes and hashes of a version-1 EIP-712 trace offline."""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys

from keccak_check import keccak256

MAX_BYTES = 1_048_576
MAX_NODES = 2048
MAX_HASH_BYTES = 1_048_576
IDENT = r'[A-Za-z_][A-Za-z0-9_]{0,127}'
TYPE = re.compile(IDENT + r'(?:\[(?:[1-9][0-9]{0,8})?\]){0,8}')
ARRAY = re.compile(r'(.+)\[([0-9]*)\]')
INTEGER = re.compile(r'(u?int)(8|16|24|32|40|48|56|64|72|80|88|96|104|112|120|128|136|144|152|160|168|176|184|192|200|208|216|224|232|240|248|256)')
FIXED = re.compile(r'bytes([1-9]|[12][0-9]|3[0-2])')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, wanted):
    require(type(value) is dict and set(value) == set(wanted.split()), 'unexpected object members')


def number(value, expected):
    require(type(value) is int and value == expected, 'incorrect length, version or byte offset')


def unhex(value, length=None):
    require(type(value) is str and re.fullmatch(r'0x(?:[0-9a-fA-F]{2})*', value) is not None,
            'expected even-length 0x hex')
    result = bytes.fromhex(value[2:])
    require(length is None or len(result) == length, 'incorrect hex byte length')
    return result


def atomic_type(kind):
    return kind in ('bool', 'address', 'string', 'bytes') or INTEGER.fullmatch(kind) or FIXED.fullmatch(kind)


def base(kind):
    return kind.split('[', 1)[0]


def declarations(encoding, primary):
    """Parse canonical encodeType, including dependencies behind empty arrays."""
    require(type(encoding) is str and len(encoding) <= 65536, 'invalid type encoding')
    found, order, position = {}, [], 0
    for match in re.finditer('(' + IDENT + r')\(([^()]*)\)', encoding):
        require(match.start() == position, 'noncanonical type encoding')
        name, contents = match.groups()
        require(name not in found and not atomic_type(name) and name not in ('uint', 'int') and
                re.fullmatch(r'(?:u?int|bytes)[0-9]+', name) is None,
                'duplicate or reserved struct')
        fields, names = [], set()
        for field in contents.split(',') if contents else []:
            parts = field.split(' ')
            require(len(parts) == 2 and TYPE.fullmatch(parts[0]) is not None and
                    re.fullmatch(IDENT, parts[1]) is not None and parts[1] not in names,
                    'invalid field declaration')
            names.add(parts[1])
            fields.append(tuple(parts))
        found[name] = fields
        order.append(name)
        position = match.end()
    require(position == len(encoding) and order and order[0] == primary and len(found) <= 64,
            'missing or invalid primary declaration')
    require(sum(map(len, found.values())) <= 256, 'too many fields')
    reached, pending = set(), [primary]
    while pending:
        name = pending.pop()
        if name in reached:
            continue
        reached.add(name)
        for kind, _ in found[name]:
            dependency = base(kind)
            if not atomic_type(dependency):
                require(dependency in found, 'missing struct dependency')
                pending.append(dependency)
    require(reached == set(found) and order[1:] == sorted(reached - {primary}),
            'unused or unsorted type dependencies')
    return found


def atomic_word(kind, value):
    if kind == 'bool':
        require(type(value) is bool, 'nonboolean normalized value')
        return int(value).to_bytes(32, 'big')
    if kind == 'address':
        return unhex(value, 20).rjust(32, b'\0')
    fixed = FIXED.fullmatch(kind)
    if fixed:
        return unhex(value, int(fixed[1])).ljust(32, b'\0')
    integer = INTEGER.fullmatch(kind)
    require(integer is not None and type(value) is str and
            re.fullmatch(r'0|-?[1-9][0-9]{0,77}', value) is not None, 'invalid normalized integer')
    parsed, width = int(value), int(integer[2])
    signed = integer[1] == 'int'
    lower, upper = (-(1 << (width - 1)), 1 << (width - 1)) if signed else (0, 1 << width)
    require(lower <= parsed < upper, 'normalized integer out of range')
    return (parsed % (1 << 256)).to_bytes(32, 'big')


def validate_tree(value):
    stack, count, text_bytes, seen = [(value, 0)], 0, 0, set()
    while stack:
        item, depth = stack.pop()
        count += 1
        require(count <= 100_000 and depth <= 48, 'JSON tree limit exceeded')
        if type(item) in (dict, list):
            require(id(item) not in seen, 'shared or cyclic containers are not JSON trees')
            seen.add(id(item))
            if type(item) is dict:
                require(all(type(k) is str for k in item), 'nonstring JSON key')
                stack.extend((k, depth + 1) for k in item)
                stack.extend((v, depth + 1) for v in item.values())
            else:
                stack.extend((v, depth + 1) for v in item)
        elif type(item) is str:
            text_bytes += len(item.encode('utf-8'))
            require(text_bytes <= MAX_BYTES, 'JSON text limit exceeded')
        elif type(item) is int:
            require(item.bit_length() <= 256, 'JSON integer limit exceeded')
        else:
            require(type(item) in (bool, type(None)), 'noninteger JSON number or unsupported value')


def verify(trace, expected):
    validate_tree(trace)
    expected = unhex(expected, 32)
    require(type(trace) is dict, 'trace must be an object')
    allowed = set('traceVersion primaryType typeEncoding domainSeparator messageHash digest nodeOrder nodes envelope'.split())
    require(set(trace) in (allowed, allowed | {'matchesExpected'}), 'unexpected trace members')
    if 'matchesExpected' in trace:
        require(type(trace['matchesExpected']) is bool, 'invalid ancestor comparison flag')
    number(trace['traceVersion'], 1)
    require(trace['nodeOrder'] == 'children before parents', 'unsupported node order')
    primary = trace['primaryType']
    require(type(primary) is str and re.fullmatch(IDENT, primary) is not None and primary != 'EIP712Domain',
            'invalid primary type')
    nodes = trace['nodes']
    require(type(nodes) is list and 2 <= len(nodes) <= MAX_NODES, 'invalid trace node count')
    known, consumed, schemas = {}, set(), {}
    hash_bytes, hash_count = 0, 0

    def hashed(raw):
        nonlocal hash_bytes, hash_count
        hash_bytes += len(raw)
        hash_count += 1
        require(hash_bytes <= MAX_HASH_BYTES, 'hash work limit exceeded')
        return keccak256(raw)

    def child(link, path, kind, offset, field=False):
        keys(link, 'name type path offsetBytes word' if field else 'path offsetBytes word')
        require(link['path'] == path and path in known and path not in consumed,
                'missing, repeated, forward or incorrect child path')
        number(link['offsetBytes'], offset)
        node = known[path]
        require(node['type'] == kind and unhex(link['word'], 32) == unhex(node['word'], 32),
                'child type or word differs')
        consumed.add(path)
        return unhex(link['word'], 32)

    for node in nodes:
        require(type(node) is dict, 'node must be an object')
        path, kind, role = node.get('path'), node.get('type'), node.get('kind')
        require(type(path) is str and len(path) <= 8192 and
                re.fullmatch(r'/(domain|message)(?:/(?:' + IDENT + r'|0|[1-9][0-9]*))*', path) is not None and
                path.count('/') <= 48 and path not in known, 'invalid or duplicate node path')
        require(type(kind) is str and TYPE.fullmatch(kind) is not None, 'invalid node type')
        word = unhex(node.get('word'), 32)
        common = 'path type kind word '
        array = ARRAY.fullmatch(kind)
        if array:
            require(role == 'array', 'array kind mismatch')
            keys(node, common + 'elements preimage preimageBytes')
            links = node['elements']
            require(type(links) is list and len(links) <= MAX_NODES, 'invalid array elements')
            require(not array[2] or len(links) == int(array[2]), 'fixed array length mismatch')
            preimage = b''.join(child(link, path + '/' + str(i), array[1], i * 32)
                                for i, link in enumerate(links))
        elif kind in ('bytes', 'string'):
            require(role == 'dynamic', 'dynamic kind mismatch')
            keys(node, common + 'inputBytes preimage preimageBytes')
            preimage = unhex(node['preimage'])
            number(node['inputBytes'], len(preimage))
            if kind == 'string':
                preimage.decode('utf-8')  # No invalid Unicode byte sequences.
        elif atomic_type(kind):
            require(role == 'atomic', 'atomic kind mismatch')
            keys(node, common + 'normalizedValue')
            require(atomic_word(kind, node['normalizedValue']) == word, 'atomic value/word mismatch')
            known[path] = node
            continue
        else:
            require(role == 'struct', 'struct kind mismatch')
            keys(node, common + 'typeEncoding typeHash fields preimage preimageBytes')
            schema = declarations(node['typeEncoding'], kind)
            for name, fields in schema.items():
                require(name not in schemas or schemas[name] == fields, 'inconsistent struct declarations')
                schemas[name] = fields
            links, declared = node['fields'], schema[kind]
            require(type(links) is list and len(links) == len(declared), 'struct field count mismatch')
            type_hash = hashed(node['typeEncoding'].encode('ascii'))
            require(type_hash == unhex(node['typeHash'], 32), 'incorrect type hash')
            words = [type_hash]
            for i, (link, (field_type, name)) in enumerate(zip(links, declared), 1):
                require(type(link) is dict and link.get('name') == name and link.get('type') == field_type,
                        'struct field declaration mismatch')
                words.append(child(link, path + '/' + name, field_type, i * 32, True))
            preimage = b''.join(words)
        require(unhex(node['preimage']) == preimage, 'preimage differs from concatenated child words')
        number(node['preimageBytes'], len(preimage))
        require(hashed(preimage) == word, 'incorrect node hash at ' + path)
        known[path] = node

    require(set(known) - consumed == {'/domain', '/message'}, 'unconnected or missing root nodes')
    domain, message = known['/domain'], known['/message']
    require(domain['kind'] == message['kind'] == 'struct' and domain['type'] == 'EIP712Domain' and
            message['type'] == primary and message['typeEncoding'] == trace['typeEncoding'], 'incorrect root type')
    domain_hash, message_hash = unhex(domain['word'], 32), unhex(message['word'], 32)
    require(unhex(trace['domainSeparator'], 32) == domain_hash and
            unhex(trace['messageHash'], 32) == message_hash, 'root hash summary differs')
    envelope = trace['envelope']
    keys(envelope, 'prefix domainOffsetBytes messageOffsetBytes preimage preimageBytes digest')
    require(unhex(envelope['prefix']) == b'\x19\x01', 'incorrect EIP-712 prefix')
    number(envelope['domainOffsetBytes'], 2)
    number(envelope['messageOffsetBytes'], 34)
    number(envelope['preimageBytes'], 66)
    preimage = b'\x19\x01' + domain_hash + message_hash
    require(unhex(envelope['preimage']) == preimage, 'incorrect envelope concatenation')
    digest = hashed(preimage)
    require(unhex(envelope['digest'], 32) == digest == unhex(trace['digest'], 32), 'incorrect final digest')
    return {'witnessValid': True, 'digest': '0x' + digest.hex(),
            'matchesExpected': digest == expected, 'nodesChecked': len(nodes),
            'hashesChecked': hash_count, 'hashInputBytes': hash_bytes,
            'sourceTypedDataChecked': False,
            'scope': 'Trace byte consistency only; compare the witness with the original intended typed data separately.'}


def loads(raw):
    require(len(raw) <= MAX_BYTES, 'input exceeds 1048576 bytes')
    text = raw.decode('utf-8')
    depth, quoted, escaped = 0, False, False
    for c in text:
        if quoted:
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == '"':
                quoted = False
        elif c == '"':
            quoted = True
        elif c in '[{':
            depth += 1
            require(depth <= 48, 'JSON nesting limit exceeded')
        elif c in ']}':
            depth -= 1

    def unique(pairs):
        out = {}
        for k, v in pairs:
            require(k not in out, 'duplicate JSON member')
            out[k] = v
        return out

    def no_float(_):
        raise ValueError('floating point and nonfinite numbers are not supported')

    parsed = json.loads(text, object_pairs_hook=unique, parse_float=no_float, parse_constant=no_float)
    validate_tree(parsed)
    return parsed


def read_workspace(name):
    path = Path(name)
    if path.is_absolute():
        path = path.relative_to(Path.cwd())
    parts = path.parts
    require(parts and all(not p.startswith('.') for p in parts), 'unsafe workspace path')
    require(hasattr(os, 'O_NOFOLLOW') and os.open in os.supports_dir_fd, 'POSIX no-follow reader required')
    directory = os.open('.', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts[:-1]:
            next_dir = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = next_dir
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(fd, 'rb') as source:
            info = os.fstat(source.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_BYTES, 'not a bounded regular file')
            raw = source.read(MAX_BYTES + 1)
    finally:
        os.close(directory)
    return loads(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', help='version-1 trace JSON file beneath cwd, no symlinks')
    parser.add_argument('--expect', required=True, help='separately retained 32-byte digest')
    args = parser.parse_args(argv)
    try:
        unhex(args.expect, 32)
        result = verify(read_workspace(args.trace), args.expect)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result['matchesExpected'] else 1
    except (ValueError, OSError, RecursionError) as exc:
        print('hash-witness: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
