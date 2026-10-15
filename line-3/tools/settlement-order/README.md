# Settlement order

Check that 2–32 Ethereum mainnet transactions both meet their settlement policies
and appear in a separately chosen chronological sequence. This helps a worker
review a multi-step operation where successful receipts alone are insufficient:
the prerequisite must appear before the later transaction. Within one block,
transaction indexes decide the order; across blocks, block numbers decide it.
The check establishes ordering under the retained provider evidence, not that
one transaction caused another or that application-specific prerequisites held.

Run from the repository root with standard-library Python 3.9+ on POSIX:

```sh
python3 -B line-3/tools/settlement-order/order.py --demo
```

This works offline with no installation. When tried, it returned
`settlement_order_match`, exit **0**, for two real ZTO transactions:

| Transaction | Inclusion block | Index in block |
| --- | ---: | ---: |
| `0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7` | 26190898 | 181 |
| `0x64847acc0a0d6b0a5cf61cfb26fea3ccfae61a75916ff9d01453a6c7a17b47d7` | 26194715 | 146 |

Both policies require 12 confirmations and finality. New read-only observations
through the assignment's Ethereum route sampled head **26195457**, hash
`0x4086aa5d86624c1bd4d25efc9e3fa1f9482c21df938d6a95c02a2a8cd273a1cd`.
The public source is [Ethereum Publicnode](https://ethereum-rpc.publicnode.com).
The exact transcripts are `evidence-1.json` and `evidence-2.json`; collection
outcomes are in `live-check.json`, and offline output is in `demo-result.json`.
These are historical observations after capture. The demo does not claim that
these two ZTO transactions form an application workflow or causal dependency.

For your own review, prepare the exact envelope illustrated by `demo-plan.json`:
`version: 1`, `batch`, and `sequence`. The `batch` is an unchanged settlement-batch
manifest (`version: 1`, `items`). Each item specifies an evidence path, its exact
SHA-256 and independent transaction/confirmation/finality policy. `sequence` must
list every transaction exactly once, in your required order. Hexadecimal case is
normalized. Batch item storage order is irrelevant. Missing, extra or repeated
sequence members, including case aliases, are rejected before evidence is opened.

Retain the exact plan's SHA-256 separately after reviewing its expectations.
Use that independently held hash with `--plan` and `--sha256`. This runnable
example uses the bundled hash only to demonstrate the interface:

```sh
python3 -B line-3/tools/settlement-order/order.py --plan line-3/tools/settlement-order/demo-plan.json --sha256 5a1693c92c1ec7c337eee0ecc74b1371ee9d4d7f9ea1ea274604b64a6a15f96f
```

The plan hash is checked **before parsing**. Replay uses that same captured plan,
then checks each evidence hash before parsing its exact captured bytes. The
entire batch must pass settlement and position replay, including its checks for
conflicting sampled block hashes, before order is evaluated. The new check also
rejects two distinct transactions claiming one block/index slot and inconsistent
transaction counts for one block. A partial batch never grants acceptance.

Output reports the plan hashes, full batch decisions, required sequence, verified
positions and any adjacent-order violations. Only top-level `accepted` decides
the whole check. Exit **0** means settlement and order match; **1** means a plan
pin, evidence pin, settlement or ordering check declined; **2** means invalid or
unavailable input. Pin mismatches produce a refusal without interpreting the
replaced bytes. Malformed inputs produce bounded diagnostic JSON.

The CLI reads explicit visible workspace-relative regular files only, with the
inherited descriptor-relative no-follow reader. Absolute, hidden, traversal,
symlink and nonregular paths are refused. Plans and each evidence file are
bounded to 90,000 bytes; stdout JSON is bounded to 100,000 bytes. Strict parsing
rejects duplicate keys and nonfinite JSON constants. It writes only to stdout.

Run the tests:

```sh
python3 -B -m unittest discover -s line-3/tools/settlement-order -p 'test_*.py' -v
```

All **24 new tests** and **21 inherited batch tests** passed. Reversing the demo
sequence produced `order_review_required` with exit 1 despite both transactions
settling. Checks cover same-block indexes, collisions, count conflicts, changed
pins, strict plans, complete membership, evidence failures, safe paths, CLI
exits, disabled network and immutable source fixtures. Synthetic branches are
in-memory test mutations only, never represented as chain observations.

Reuse requires unchanged sibling `settlement-batch`, `pinned-position`,
`tx-position`, `payment-witness` and `settlement-check` modules. They are ordinary
repository Python files and require no network or packages for this replay.

This is provider-asserted historical ordering, not a consensus, trie, or
inter-block ancestry proof. Sampled matching anchors do not prove every intervening
block or provider honesty. Full transaction lists are checked per evidence file;
the new ordering layer does not compare all list contents between transcripts.
No token amount, allowance, recipient ownership, application success, current
freshness or authorization is established. Independently retain expectations;
replacing both a plan and its expected hash defeats replacement detection. The
bundled demo hash is illustrative, not independent custody. There is no ledger,
cross-run deduplication, signing, sending, payment, deployment, environment or
secret access.
