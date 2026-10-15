#!/usr/bin/env python3
"""Validate every JSON Lines row with exact whole-file source locations, offline."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import types

MAX_ROWS = 256
MAX_OUTPUT_BYTES = 100_000

def bounded_module():
    # Bootstrap only the fixed, trusted sibling; user inputs use its no-follow reader.
    source = Path(__file__).absolute().parent.parent / 'bounded-contract' / 'check.py'
    relative = source.relative_to(Path.cwd()).as_posix()
    if any(not p or p.startswith('.') for p in relative.split('/')):
        raise ValueError('run inside the workspace containing the sibling tools')
    # Open each component without following links, including the trusted bootstrap.
    import os
    import stat
    directory = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    leaf = None
    try:
        parts = relative.split('/')
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                       dir_fd=directory)
        if not stat.S_ISREG(os.fstat(leaf).st_mode):
            raise ValueError('trusted sibling must be a regular file')
        chunks, remaining = [], 1_000_001
        while remaining:
            chunk = os.read(leaf, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        code = b''.join(chunks)
        if len(code) > 1_000_000:
            raise ValueError('trusted sibling exceeds byte limit')
    finally:
        if leaf is not None:
            os.close(leaf)
        os.close(directory)
    module = types.ModuleType('repair_bounded_contract')
    module.__file__ = str(source)
    exec(compile(code, str(source), 'exec'), module.__dict__)
    return module


def dependencies():
    reader = bounded_module()
    path = Path(__file__).absolute().parent.parent / 'source-locator' / 'locate.py'
    source = types.ModuleType('jsonl_source_locator')
    source.__file__ = str(path)
    relative = path.relative_to(Path.cwd()).as_posix()
    exec(compile(reader.read_bytes(relative), str(path), 'exec'), source.__dict__)
    _, engine, rules = source.dependencies()
    return reader, source, engine, rules


def encode(report):
    """Emit all rows and diagnostics, or nothing; all output is ASCII JSON."""
    chunks, size = [], 0
    for chunk in json.JSONEncoder(ensure_ascii=True, allow_nan=False,
                                   indent=2).iterencode(report):
        size += len(chunk)
        if size + 1 > MAX_OUTPUT_BYTES:
            raise ValueError('complete output exceeds 100,000 bytes; no report emitted')
        chunks.append(chunk)
    return ''.join(chunks) + '\n'


def identity(data, name):
    return {'file': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def shift_location(location, line, byte_start, char_start):
    """Translate document spans only; contract coordinates stay unchanged."""
    spans = [location['value']] if location['present'] else [location['anchor']['value']]
    if 'key' in location:
        spans.append(location['key'])
    for span in spans:
        for point in span.values():
            point['line'] += line - 1
            point['byte_offset'] += byte_start
            point['char_offset'] += char_start


def inspect(reader, source, engine, rules, contract_name, document_name,
            contract_sha256=None, document_sha256=None):
    for pin in (contract_sha256, document_sha256):
        if pin is not None and not re.fullmatch('[0-9a-f]{64}', pin):
            raise ValueError('expected SHA-256 must be 64 lowercase hex digits')
    captured = {}

    def capture(name, pin):
        if name not in captured:
            captured[name] = reader.read_bytes(name)
        raw = captured[name]
        if not isinstance(raw, bytes) or len(raw) > 1_000_000:
            raise ValueError('input must be at most 1,000,000 bytes')
        if pin is not None and hashlib.sha256(raw).hexdigest() != pin:
            raise ValueError('source SHA-256 mismatch: ' + name)
        return raw

    contract = source.Source(capture(contract_name, contract_sha256), contract_name)
    engine.prepare(contract.value)
    data = capture(document_name, document_sha256)
    text = data.decode('utf-8')
    if not text:
        raise ValueError('JSON Lines input must contain at least one row')
    # Only LF separates records. Keep CR as original JSON whitespace; Unicode
    # separators, escaped newlines and form feeds do not create extra records.
    lines = text.split('\n')
    if text.endswith('\n'):
        lines.pop()  # optional final delimiter is not an extra blank record
    if len(lines) > MAX_ROWS:
        raise ValueError('at most 256 JSON Lines rows per invocation')
    rows, byte_start, char_start = [], 0, 0
    counts = {'rows': len(lines), 'passed': 0, 'violated': 0,
              'malformed': 0, 'structural_errors': 0}
    for line, body in enumerate(lines, 1):
        raw = body.encode('utf-8')
        row = {'line': line, 'byte_start': byte_start,
               'byte_end': byte_start + len(raw),
               'sha256': hashlib.sha256(raw).hexdigest()}
        try:
            document = source.Source(raw, document_name)
        except (ValueError, RecursionError) as exc:
            # Semantic JSON parse errors (duplicates/nonfinite numbers) have no
            # reliable token position from the inherited parser. Anchor the row
            # honestly, rather than inventing a token location.
            if isinstance(exc, json.JSONDecodeError):
                position = {'line': line, 'column': exc.pos + 1,
                            'byte_offset': byte_start + len(body[:exc.pos].encode('utf-8')),
                            'char_offset': char_start + exc.pos}
                kind, span = 'syntax_point', {'start': position, 'end': dict(position)}
            else:
                kind = 'row_anchor'
                span = {'start': {'line': line, 'column': 1, 'byte_offset': byte_start,
                                  'char_offset': char_start},
                        'end': {'line': line, 'column': len(body) + 1,
                                'byte_offset': byte_start + len(raw),
                                'char_offset': char_start + len(body)}}
            row.update({'valid': False, 'status': 'malformed', 'errors': [],
                        'parse_error': {'message': str(exc)[:1000], 'kind': kind,
                                        'file': document_name, 'span': span}})
            counts['malformed'] += 1
        else:
            report = source.locate(engine, rules, contract, document)
            for error in report['errors']:
                shift_location(error['document_source'], line, byte_start, char_start)
            row.update({'valid': report['valid'],
                        'status': 'valid' if report['valid'] else 'violations',
                        'errors': report['errors']})
            counts['passed' if report['valid'] else 'violated'] += 1
            counts['structural_errors'] += report['error_count']
        rows.append(row)
        byte_start += len(raw) + 1
        char_start += len(body) + 1
    valid = not (counts['violated'] or counts['malformed'])
    return {'valid': valid, 'complete': True,
            'status': 'malformed_rows' if counts['malformed'] else
                      ('valid' if valid else 'structural_violations'),
            'summary': counts,
            'sources': {'contract': contract.identity(),
                        'document': identity(data, document_name)},
            'coordinates': {
                'pointers': 'relative to the JSON value on the reported row',
                'lines': 'one-based physical LF-delimited file lines',
                'columns': 'one-based Unicode code points, not display cells or UTF-16',
                'offsets': 'zero-based whole-file UTF-8 bytes and Unicode code points; end exclusive',
                'row_bytes': 'includes CR when present; excludes the LF delimiter',
                'missing': 'missing values anchor the containing object; no invented value token'},
            'rows': rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract', help='explicit relative workspace structural contract')
    parser.add_argument('document', help='relative workspace UTF-8 JSON Lines file')
    parser.add_argument('--contract-sha256', help='separately retained exact contract hash')
    parser.add_argument('--document-sha256', help='separately retained exact whole-file hash')
    args = parser.parse_args(argv)
    try:
        result = inspect(*dependencies(), args.contract, args.document,
                         args.contract_sha256, args.document_sha256)
        output = encode(result)
        sys.stdout.write(output)
        return 2 if result['summary']['malformed'] else (0 if result['valid'] else 1)
    except (ValueError, OSError, RecursionError, KeyError, IndexError) as exc:
        sys.stderr.write(json.dumps({'valid': False, 'complete': False,
                                     'status': 'input_or_output_error',
                                     'error': str(exc)[:1000]}, ensure_ascii=True) + '\n')
        return 2


if __name__ == '__main__':
    sys.exit(main())


