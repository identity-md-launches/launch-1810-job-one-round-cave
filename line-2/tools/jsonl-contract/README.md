# Offline JSON Lines contract checker

Check an API export, worker queue or batch of JSON values against one explicit
structural contract. Each physical line is checked independently. A malformed
row does not hide later rows: the report separates valid rows, contract
violations and malformed JSON, and locates errors in the original whole file.
The program reads inputs and prints a report; it never rewrites inputs.

Run from the repository root with Python 3.10+ on POSIX:

```sh
python3 -B line-2/tools/jsonl-contract/check.py shared/payment-evidence/policy.contract.json line-2/tools/jsonl-contract/zto-policy.jsonl
```

Tried locally: **exit 0**, one valid row, zero violations. `zto-policy.jsonl`
contains the existing saved ZTO payment policy converted to one compact line,
with every value unchanged. The contract lists ZTO first and IMD second.
`zto-policy.result.json` retains the actual result. This verifies structure,
not a payment, live chain state, amount received or authorization.

To see recovery after a malformed row:

```sh
python3 -B line-2/tools/jsonl-contract/check.py line-2/tools/json-contract/report.contract.json line-2/tools/jsonl-contract/mixed-reports.jsonl
```

Tried locally: **exit 2**, four rows: **two pass**, **one has three structural
violations**, and **one is malformed**. Row four is still checked. The input
combines inherited example build reports with an intentionally unfinished `{`
row; it does not assert real build outcomes. The complete actual result is in
`mixed-reports.result.json`. These are local observations, not certification.

## Framing and locations

- Input is UTF-8, with exactly one JSON value per LF-delimited line. CRLF is
  accepted; the CR remains in the original row bytes. The final LF is optional.
  Blank or whitespace-only rows fail and are never silently skipped. An empty
  file fails. Pretty-printed multiline JSON is not one JSON Lines record.
- Root objects, arrays, strings, numbers, booleans and null are supported under
  their respective contracts. Escaped newlines and Unicode line separators
  inside strings do not split rows. Duplicate keys, nonfinite numbers, a BOM
  and invalid JSON reject. Invalid UTF-8 rejects the entire input.
- Each row has a one-based physical `line`, zero-based `byte_start`/`byte_end`
  excluding its LF delimiter, and SHA-256 of those exact row bytes. CR, spaces
  and original escaping affect the hash. Top-level `sources` identifies the
  complete original document and contract, including their exact byte hashes.
- Diagnostic JSON Pointers are relative to that row's JSON value. Document
  spans use **whole-file** byte and character offsets and physical line numbers;
  contract spans remain relative to the contract file. Columns count Unicode
  code points, including tabs as one, not UTF-16 units or display cells. Ranges
  include their start and exclude their end. Keys get their own source spans.
- Missing properties explicitly anchor the containing object. Present `null`
  has its own token. Syntax errors use a zero-width parser position. Duplicate
  keys and other parser errors without a reliable token position use an
  explicit `row_anchor`; the program never invents their precise token location.
- All inherited structural diagnostics and their order are retained. Rows are
  independent: the tool does not enforce uniqueness or relationships across rows.

## Exit codes and limits

| Exit | Meaning | Output |
| --- | --- | --- |
| 0 | Every row satisfies the contract | Complete JSON report on stdout |
| 1 | At least one structural violation, no malformed rows | Complete JSON report on stdout |
| 2 | At least one malformed row | Complete JSON report on stdout, `valid: false` |
| 2 | File, contract, pin, UTF-8, resource or output failure | Empty stdout; small JSON error on stderr |

`complete: true` means every framed row was processed; it does **not** mean
the input is valid. Acceptance requires exit 0 and `valid: true`. Do not infer
success from an empty structural error array on a malformed row.

Optional `--contract-sha256 HASH` and `--document-sha256 HASH` check separately
retained lowercase hashes before parsing the captured bytes. The contract is
prepared before opening the document. Equal paths are captured only once.
A digest binds bytes, not an author or approval; retain expected hashes separately.

Inputs are explicit visible relative workspace regular files, at most 1,000,000
bytes each. No-follow descriptor traversal rejects symlinks, parent/hidden paths,
absolute paths and special files. Up to **256 rows** are accepted. The complete
ASCII JSON report, including its newline, must fit **100,000 bytes**; overflow
rejects the entire output instead of dropping rows or diagnostics. Split large
batches explicitly; this is a bounded in-memory checker, not a streaming service.

Only the Python standard library and ordinary committed sibling sources are
needed: `source-locator`, `rule-locator`, `bounded-contract`, and `json-contract`.
Keep those directories beside this tool when relocating it; run within the
workspace containing them. No installation, network or environment lookup occurs.
The contract language is the inherited deliberate subset, not full JSON Schema.
Trusted regexes are required; file/output bounds do not provide a CPU sandbox.

## Tests

```sh
python3 -B line-2/tools/jsonl-contract/test_check.py
```

All **18 tests passed**, covering row recovery, strict parsing, LF/CRLF/Unicode,
exact original token slices, missing/null distinctions, scalar/array rows, pins,
capture reuse, complete-output failure, CLI codes, immutability, path restrictions
and the saved ZTO policy with network transport disabled. The unchanged
source-locator's **16 tests** also passed. Results are in `validation.json`.
