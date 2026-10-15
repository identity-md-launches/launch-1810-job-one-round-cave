# Snapshot integer decoder

Read one Ethereum integer from a validated portable JSON-RPC snapshot and print
its exact decimal value. This Python standard-library tool works offline, needs
no installation, writes no files, and never uses a wallet or submits a transaction.
It builds on the existing snapshot validator and JSON Pointer selector.

One command from the repository root shows it working:

```sh
python3 -B line-1/tools/snapshot-integer/decode.py line-1/tools/snapshot-integer/live-zto.json --encoding uint256 --decimals 18
```

Tried on 2026-10-15 with a fresh real Ethereum public read of ZTO
`0xd782bdea4ef02a0bd391eb9089470c8080f0a68e` `totalSupply()` (`0x18160ddd`).
The command exits 0 and decodes **1000000000000000000000000000 raw**, displayed
as **1000000000.000000000000000000** with the caller's explicit scale of 18.
The complete response is retained in `live-zto.json`, with the public source
label `https://ethereum-rpc.publicnode.com`. This is a historical `latest`-tag
observation, without a recorded block anchor. Running this command replays the
saved observation; it does not refresh the data or prove the token's decimals.

For a block number from the ancestor's real saved block response:

```sh
python3 -B line-1/tools/snapshot-integer/decode.py line-1/tools/snapshot-select/live-block.json --pointer /number --encoding quantity
```

This returns **26195002**. Pointers are RFC 6901 paths relative to
`response.result`; an empty pointer selects the whole result. Selection validates
the snapshot's public-read request, RPC envelope and response checksum first.
The output retains that selection, original hex string, request and source/time
metadata alongside a `decoded` object. Decimal integers are strings to avoid
JSON consumers rounding values above their safe integer range.

Choose the interpretation explicitly:

- `quantity`: canonical Ethereum `0x` hex, zero as `0x0`, no leading zeros,
  at most 64 hex digits (256 bits). An odd number of hex digits is valid here.
- `uint256`: exactly one 32-byte ABI word, unsigned.
- `int256`: exactly one 32-byte ABI word, interpreted as signed two's complement.
- `--decimals N`: caller-supplied scale from 0 to 255, default 0. Formatting uses
  integer arithmetic, preserves every fractional digit and never rounds.

No interpretation is inferred from the method, selector, address or field name.
The same all-ones word means `2**256 - 1` in unsigned mode and `-1` in signed
mode. Shorter ABI integer types, address/bool words, ABI tuples, dynamic arrays,
and multiword results are not decoded. A 32-byte hash or address-shaped word can
be explicitly interpreted as an integer; success does not establish its ABI type.
The tool assigns no token symbol, currency unit, ownership or price meaning.

Exit 0 means validation, selection and the requested interpretation succeeded.
Exit 1 reports a file, validation, selection, bounds or decoding error on stderr,
with no partial JSON on stdout. CLI syntax errors exit 2. Output is bounded to
100,000 bytes. The inherited input cap is 2,016,384 bytes; input must be a visible
relative workspace regular file, without symlinks or parent components. Metadata
remains untrusted. Keep sibling `snapshot-select`, `bounded-rpc-snapshot`, and
`safe-snapshot-files` folders: these ordinary local Python sources are dependencies.

Checks, also offline:

```sh
python3 -B -m unittest discover -s line-1/tools/snapshot-integer -p 'test_*.py' -v
```

The suite covers fresh and inherited real ZTO observations, saved block selection,
signed and unsigned limits, canonical quantity syntax, word width, exact scaling,
negative fractions, malformed values, missing pointers, CLI exits, unchanged
inputs, strict JSON, checksum tampering, symlink rejection and disabled transport.
Synthetic mutations are test inputs, not chain evidence. A consistently resealed
fake observation deliberately passes, demonstrating the limit of checksums.
The first test run exposed absolute scratch paths returned by `tempfile`; the
tests now convert their own scratch paths to workspace-relative paths before
exercising the reader, including genuine malformed-input checks.

Checksums and decoding do not authenticate a provider or establish Ethereum
state, chain identity, finality, freshness, balance, payment or authorization.
Use retained external pins and appropriate anchored evidence when those matter.
No extra coin, dependency, payment, wallet or deployment is required.
