# Ordered settlement review

Check an independently pinned transaction-order plan with explicit structural
errors, then replay every pinned Ethereum transcript and require the exact
intended transaction sequence. This joins Line 2's JSON contracts to Line 3's
settlement and position/order checks. Standard-library Python 3.9+ on POSIX;
no packages, network, accounts, configuration or line folders are needed.

Run from the repository root:

```sh
python3 -B shared/ordered-settlement/review.py shared/ordered-settlement/plan.json --sha256 70e3848cd1ae7417abbd8ca0b05e4cb271a485978ab0921420270911672ef7de
```

When tried, exit 0, `accepted: true`, `settlement_order_match`. The two real
historical ZTO transactions were included at block/index **26190898/181** and
**26194715/146**. Both policies require 12 confirmations and finality. This is
retained public Ethereum evidence, not a fresh observation or a causal workflow.
The bundled plan and hash demonstrate execution; retain your own expectations
independently before relying on a later plan.

A reversed sequence exits 1 with `order_review_required` even though both
transactions meet settlement policy. A string replacing `requireFinalized`
exits 1 with `/batch/items/0/policy/requireFinalized` in structural diagnostics;
no evidence opens. Actual accepted/refused reports are beside this README.

## Inputs and decisions

`plan.json` illustrates the exact version-1 envelope: `batch` contains `version`
and `items`; `sequence` contains every batch transaction exactly once in the
intended order. Each item supplies a visible workspace-relative evidence path,
its exact lowercase SHA-256 and an explicit transaction/confirmation/finality
policy. There must be 2..32 items. Sequence and transaction hashes normalize hex
case; duplicates, extra or missing members reject before any evidence opens.
The fixed contract cannot be relaxed by an incoming plan.

The expected plan hash is checked **before parsing**. Structural diagnostics use
JSON Pointers. Semantic validation follows, then settlement replay consumes the
**same captured plan bytes**. Each evidence hash is checked before parsing its
captured bytes. All transactions must settle with consistent sampled block
hashes. Ordering uses block number, then transaction index; collisions and
conflicting transaction counts reject. There is no partial-batch acceptance.

Require top-level `accepted: true` and exit 0. Exit 1 means a pin, structural,
settlement or order refusal; exit 2 means invalid/unavailable input or bounds.
Input errors emit a bounded refusal without a partial acceptance report.
The Python API raises on invalid inputs; callers must handle errors as refusal.
Inputs are bounded to 90,000 bytes, stdout to 100,000 ASCII bytes including its
newline. Strict JSON rejects duplicate keys/nonfinite constants. The inherited
no-follow descriptor reader refuses absolute/hidden/traversal/symlink/special
paths. The program writes only stdout.

## Relocation and checks

Copy this whole folder as ordinary files to `shared/ordered-settlement` beneath
a new workspace root. Run the same command there. No line folders are required;
all seven source dependencies and both evidence fixtures are included. For a
different location, explicitly update the evidence paths in your plan and retain
its new exact hash after review. Never silently update a trusted expected hash.
`provenance.json` maps unchanged code/evidence copies to source hashes; only the
demo plan's evidence paths were changed for portability.

```sh
python3 -B shared/ordered-settlement/test_review.py
```

All 15 integration tests pass here and in a detached workspace. They cover real
ZTO order, reversed sequence despite settlement, irrelevant batch storage order,
plan pins before parse, structural failures before replay, complete membership,
case aliases, evidence pin/missing-file refusals, hostile acceptance fields,
strict inputs, bounds, CLI exits, disabled transport and immutable inputs.

## Limits

Provider assertions are not consensus, trie or inter-block ancestry proofs.
Chronological order does not establish causation, application success or a
required business dependency. This does not check token amount, recipient
ownership, freshness, authorization or persistent deduplication. It neither
signs nor sends anything. Separately keep the policy and plan hash; replacing
both defeats replacement detection. The older `shared/settlement-gate` remains
the tool for comparing a proposed policy against a retained non-weakening
baseline; this order review does not perform that comparison. A Line 4 digest
review can bind an intended typed message separately; acceptance here grants
no signing permission. No additional coin or deployment is required.
