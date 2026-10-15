# Offline EIP-712 hash-witness verifier

Check a version-1 encoding trace with a **second Keccak-256 implementation**.
This folder is standalone Python standard library code: copy the entire folder
into a workspace and it runs offline. It imports no ancestor encoder and needs
no installed packages, account or configuration.

One command from the repository root:

```sh
python3 -B line-4/tools/hash-witness/hash_witness.py line-4/tools/hash-witness/zto-trace.json --expect 0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774
```

Tried: exit **0**, `witnessValid: true`, `matchesExpected: true`; **12 nodes,
7 hashes and 691 hash-input bytes** checked. Actual output is `example-zto.json`.
The fixture is the ancestor's historical real-ZTO payment-evidence commitment,
including token `0xd782bdea4ef02a0bd391eb9089470c8080f0a68e` and transaction
`0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7`.
It is not a fresh chain observation, deployed token interface, authorization,
payment approval, or claim that ZTO supports this typed message. The included
expected digest demonstrates execution; retain your own expectation separately.

For the published EIP-712 Ether Mail example:

```sh
python3 -B line-4/tools/hash-witness/hash_witness.py line-4/tools/hash-witness/ether-mail-trace.json --expect 0xbe609aee343fb3c4b28e1df9e632fca64fcfaede20f02e86244efddf30957bd2
```

Tried: exit **0**. Supplying that Mail digest to the ZTO trace exits **1** with
`witnessValid: true`, `matchesExpected: false`. An inconsistent trace, malformed
input, invalid expected digest or exceeded bound exits **2**, with no report on
stdout. All operations are read-only; output goes to stdout. No network, wallet,
secret, environment lookup, signature, transaction or other outbound action.

## What gets checked

- Every type hash, dynamic value hash, array hash, struct hash and final envelope
  hash, using the new `keccak_check.py`. It uses matrix lanes, an in-place lane
  walk, and generated LFSR round constants, instead of the ancestor's linear
  state, copied rotation matrix and constant table.
- Exact concatenation of a struct's type hash and ordered field words, or an
  array's ordered element words; every offset and length; complete child-before-
  parent linkage, unique paths, unique parent use, and no disconnected nodes.
- Atomic normalized values: address left padding, fixed-bytes right padding,
  strict booleans, integer width/range and signed extension. Strings' preimages
  must be valid UTF-8; binary bytes need not be.
- Canonical type declarations, field order/name/type agreement, sorted complete
  reachable dependencies (including types behind empty arrays), fixed-array
  lengths, and consistent declarations across the entire trace.
- The `0x1901` prefix, both root hashes, their order, the 66-byte envelope, all
  summary hashes, and comparison with the caller's required `--expect` value.
  An ancestor's optional `matchesExpected` flag is never used to decide success.

## The boundary of this check

**A witness is not the original intended request.** A completely consistent
replacement trace can pass when paired with its own expected digest. The output
always includes `sourceTypedDataChecked: false`. Separately compare the witness
with the original intended typed data and independently retain the expected
digest before using this check. A match does not establish intent, consent,
ownership, replay protection, contract support, settlement or fresh payment.

The format is the complete JSON output of the inherited `typed-trace` tool;
summary output is insufficient. To export a new trace in this repository:

```sh
python3 -B line-4/tools/typed-trace/typed_trace.py line-4/tools/typed-trace/zto-payment.json > test/scratch/zto-trace.json
```

Create `test/scratch` first if absent. This export is optional; the verifier
itself uses none of that tool's files. Trace words for dynamic values do not
recover the original JSON spelling. Unused declarations outside `encodeType`
are absent from traces and cannot be checked here. The verifier does not accept
a wallet RPC envelope, signature, raw signing request, arbitrary trace version,
or truncated trace. Type identifiers follow the ancestor's ASCII convention;
array declarations allow up to eight dimensions and nine digits per fixed length.

Files must be regular no-follow files beneath cwd, at most **1,048,576 bytes**;
hidden path components, parent traversal, symlinks, directories and FIFOs fail.
POSIX directory descriptors are required. Strict UTF-8 JSON rejects duplicate
keys, floats and nonfinite numbers. Bounds: depth 48, 100,000 tree entries,
1 MiB aggregate string bytes, 2,048 trace nodes, 1 MiB aggregate hash input,
64 declarations/256 fields per type encoding. Bounds fail without partial
success; they are not an operating-system CPU-time sandbox.

## Checks and provenance

```sh
python3 -B -m unittest discover -s line-4/tools/hash-witness -v
```

Tried: **30 tests pass**, also in a detached copy containing only this folder.
Tests include published empty/`abc` Ethereum Keccak vectors, Ether Mail, real
historical ZTO, nested/fixed/empty arrays, recursive finite structs, signed
integers, bytes padding, Unicode, strict schema/graph checks, altered hashes,
wrong expectations, hostile JSON/path inputs, resource limits and CLI exits.
Using a test-only SHA3 suffix, the same new sponge/permutation matches Python's
independent `hashlib.sha3_256` for **42 cases**, including immediately before,
at and after the 136-byte rate and multiple blocks. Ethereum's production
entry point always uses Keccak suffix `0x01`, not SHA3 suffix `0x06`.

Fixtures were exported once from the inspected ancestor trace tool; the edge
fixture is synthetic. Exact original source and fixture hashes are in
`provenance.json`. Shared fixture ancestry is not independent semantic approval.
The new cryptographic code has not had an independent audit. Rules consulted:
[EIP-712](https://eips.ethereum.org/EIPS/eip-712) and
[Team Keccak's permutation and sponge description](https://keccak.team/keccak_specs_summary.html).
