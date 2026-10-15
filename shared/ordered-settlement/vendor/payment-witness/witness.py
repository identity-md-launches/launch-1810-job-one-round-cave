#!/usr/bin/env python3
"""Read-only ZTO/IMD receipt net-transfer and settlement checks; stdlib only."""
import argparse
import importlib.util
import json
import os
import stat
from pathlib import Path
import re
import sys
import urllib.error

# Reuse the ancestor's settlement policy without altering it.
_spec = importlib.util.spec_from_file_location(
    "ancestor_settlement", Path(__file__).resolve().parent.parent / "settlement-check" / "settlement.py")
settlement = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(settlement)
Error = settlement.EvidenceError
TOKENS = {"ZTO": settlement.ZTO, "IMD": "0xd34a99bc0f67ae1bbd63c660e6d0b0dd03e263b7"}
DEMO_TX = "0xc4ca304c305cae326cab066639ab2156412eee7f5f774b41a2a136369f817ef7"
LIMIT = 90000


def address(value):
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]{40}", value):
        raise Error("expected a 20-byte address")
    if int(value[2:], 16) == 0:
        raise Error("recipient must be nonzero")
    return value.lower()


def positive(value):
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]{0,77}", value):
        raise Error("minimumRaw must be a positive decimal integer string")
    number = int(value)
    if number >= 2**256:
        raise Error("minimumRaw exceeds uint256")
    return number


def topic_address(value):
    word = settlement.hash32(value)
    if word[2:26] != "0" * 24:
        raise Error("nonzero address-topic padding")
    return "0x" + word[26:]


def transfers(receipt, tx, token):
    """Decode only exact ERC-20 Transfer logs emitted by the chosen token."""
    if not isinstance(receipt, dict) or settlement.hash32(receipt.get("transactionHash")) != tx:
        raise Error("receipt transaction mismatch")
    block_hash = settlement.hash32(receipt.get("blockHash"))
    height = settlement.quantity(receipt.get("blockNumber"))
    logs = receipt.get("logs")
    if not isinstance(logs, list):
        raise Error("receipt logs unavailable")
    found, indices = [], set()
    for log in logs:
        if not isinstance(log, dict):
            raise Error("invalid receipt log")
        emitter = log.get("address")
        if not isinstance(emitter, str) or not re.fullmatch(r"0x[0-9a-fA-F]{40}", emitter):
            raise Error("invalid log emitter")
        if emitter.lower() != token:
            continue
        topics = log.get("topics")
        if not isinstance(topics, list):
            raise Error("invalid token log topics")
        if not topics or settlement.hash32(topics[0]) != settlement.TRANSFER:
            continue
        if len(topics) != 3:
            raise Error("Transfer event must have exactly three topics")
        if log.get("removed") is not False:
            raise Error("removed or unverifiable Transfer log")
        if (settlement.hash32(log.get("transactionHash")) != tx or
                settlement.hash32(log.get("blockHash")) != block_hash or
                settlement.quantity(log.get("blockNumber")) != height):
            raise Error("Transfer log does not belong to this receipt")
        index = settlement.quantity(log.get("logIndex"))
        if index in indices:
            raise Error("duplicate Transfer log index")
        indices.add(index)
        amount = int(settlement.hash32(log.get("data")), 16)
        found.append({"from": topic_address(topics[1]), "to": topic_address(topics[2]),
                      "raw": str(amount), "logIndex": index})
    return found


def net_amount(events, recipient):
    incoming = sum(int(e["raw"]) for e in events if e["to"] == recipient)
    outgoing = sum(int(e["raw"]) for e in events if e["from"] == recipient)
    return incoming, outgoing, incoming - outgoing


class Recorder:
    def __init__(self, rpc):
        self.rpc, self.reads = rpc, []

    def call(self, method, params):
        result = self.rpc.call(method, params)
        # Block summaries are all the policy reads. Avoid huge transaction arrays.
        saved = ({k: result.get(k) for k in ("number", "hash")} if
                 method == "eth_getBlockByNumber" and isinstance(result, dict) else result)
        self.reads.append({"method": method, "params": params, "result": saved})
        return result


class Replay:
    def __init__(self, reads):
        if not isinstance(reads, list) or len(reads) > 32:
            raise Error("invalid or oversized read transcript")
        self.reads, self.index = reads, 0

    def call(self, method, params):
        if self.index >= len(self.reads):
            raise Error("missing replay read")
        item = self.reads[self.index]
        self.index += 1
        if not isinstance(item, dict) or item.get("method") != method or item.get("params") != params:
            raise Error("replay request mismatch")
        if "result" not in item:
            raise Error("missing replay result")
        return item["result"]


def verify(rpc, tx, recipient, minimum_raw, token="ZTO", confirmations=12, finalized=True):
    tx, recipient = settlement.hash32(tx), address(recipient)
    minimum = positive(minimum_raw)
    if token not in TOKENS:
        raise Error("supported tokens are ZTO and IMD")
    if type(confirmations) is not int or not 1 <= confirmations <= 1000000 or type(finalized) is not bool:
        raise Error("invalid settlement policy")
    report = settlement.inspect(rpc, tx, confirmations, finalized)
    report["accepted"] = False
    report["paymentPolicy"] = {"token": token, "contract": TOKENS[token],
                               "recipient": recipient, "minimumRaw": minimum_raw,
                               "measure": "incoming minus outgoing Transfer amounts in this receipt"}
    if not report["settled"]:
        return report
    receipt = rpc.call("eth_getTransactionReceipt", [tx])
    if (not isinstance(receipt, dict) or settlement.quantity(receipt.get("status")) != 1 or
            settlement.hash32(receipt.get("blockHash")) != report["inclusion"]["hash"] or
            settlement.quantity(receipt.get("blockNumber")) != report["inclusion"]["number"]):
        raise Error("receipt changed after settlement check")
    events = transfers(receipt, tx, TOKENS[token])
    incoming, outgoing, net = net_amount(events, recipient)
    if settlement.block(rpc, hex(report["inclusion"]["number"])) != report["inclusion"]:
        raise Error("inclusion changed during payment check")
    report["transferEvidence"] = {"incomingRaw": str(incoming), "outgoingRaw": str(outgoing),
                                  "netRaw": str(net), "events": events}
    report["accepted"] = net >= minimum
    report["paymentState"] = "verified" if report["accepted"] else "amount_not_met"
    return report


def load_workspace_json(filename):
    """Bounded regular-file read, relative to an open workspace directory.

    Never resolve/follow symlinks, including during a concurrent rename. POSIX
    descriptor-relative opens are required; unsupported systems fail closed.
    """
    if not isinstance(filename, (str, Path)):
        raise Error("replay path must be workspace relative")
    name = str(filename)
    parts = name.split("/")
    if (not name or name.startswith("/") or "\\" in name or
            any(not part or part in (".", "..") or part.startswith(".") for part in parts)):
        raise Error("replay path must use visible workspace-relative components")
    if (not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY") or
            os.open not in os.supports_dir_fd):
        raise Error("safe replay file opens are unsupported on this platform")
    directory = None
    descriptor = None
    try:
        directory = os.open(".", os.O_RDONLY | os.O_DIRECTORY)
        for part in parts[:-1]:
            next_directory = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                     dir_fd=directory)
            os.close(directory)
            directory = next_directory
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise Error("replay input must be a regular file")
        chunks, size = [], 0
        while size <= LIMIT:
            chunk = os.read(descriptor, min(8192, LIMIT + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        if size > LIMIT:
            raise Error("replay file exceeds 90 KB")
        return settlement.strict_json(b"".join(chunks))
    except OSError:
        raise Error("replay input could not be opened safely") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--tx")
    source.add_argument("--demo", action="store_true", help="observe a documented real ZTO transaction")
    source.add_argument("--replay", help="verify a saved read transcript offline")
    parser.add_argument("--recipient")
    parser.add_argument("--minimum-raw")
    parser.add_argument("--token", choices=TOKENS, default="ZTO")
    parser.add_argument("--confirmations", type=int, default=12)
    parser.add_argument("--allow-unfinalized", action="store_true")
    parser.add_argument("--rpc", choices=[settlement.RPC_URL, "https://eth.drpc.org"], default=settlement.RPC_URL)
    args = parser.parse_args(argv)
    try:
        if args.replay:
            if args.recipient or args.minimum_raw or args.token != "ZTO" or args.confirmations != 12 or args.allow_unfinalized:
                raise Error("replay uses the saved policy; CLI policy overrides are not allowed")
            sample = load_workspace_json(args.replay)
            if not isinstance(sample, dict) or sample.get("version") != 1:
                raise Error("unsupported replay format")
            policy = sample["policy"]
            rpc = Replay(sample["reads"])
            report = verify(rpc, **policy)
            if rpc.index != len(rpc.reads):
                raise Error("unused replay reads")
            report["evidenceMode"] = "offline historical RPC observations, not current chain evidence"
        else:
            rpc = Recorder(settlement.RPC(args.rpc))
            tx = DEMO_TX if args.demo else args.tx
            recipient, minimum = args.recipient, args.minimum_raw
            if args.demo:
                if recipient or minimum or args.token != "ZTO":
                    raise Error("demo derives an observed ZTO recipient and amount; use --tx for an invoice")
                if settlement.quantity(rpc.call("eth_chainId", [])) != 1:
                    raise Error("demo requires mainnet")
                receipt = rpc.call("eth_getTransactionReceipt", [tx])
                events = transfers(receipt, tx, TOKENS["ZTO"])
                candidates = [(net_amount(events, r)[2], r) for r in {e["to"] for e in events}
                              if int(r[2:], 16) != 0 and net_amount(events, r)[2] > 0]
                if not candidates:
                    raise Error("documented transaction has no positive ZTO recipient")
                amount, recipient = max(candidates)
                minimum = str(amount)
                # Discovery is outside the policy transcript; replay needs only verification reads.
                rpc.reads.clear()
            if recipient is None or minimum is None:
                raise Error("--tx requires --recipient and --minimum-raw")
            policy = dict(tx=tx, recipient=recipient, minimum_raw=minimum, token=args.token,
                          confirmations=args.confirmations, finalized=not args.allow_unfinalized)
            report = verify(rpc, **policy)
            report["evidenceMode"] = "live RPC observations"
            report["sample"] = {"version": 1, "policy": policy, "reads": rpc.reads}
            if args.demo:
                report["demoNote"] = "Expected amount derived from this receipt; this demonstrates decoding, not an independent invoice."
        print(json.dumps(report, indent=2))
        return 0 if report["accepted"] else 1
    except (Error, ValueError, TypeError, KeyError, OSError, urllib.error.URLError) as exc:
        print(json.dumps({"accepted": False, "state": "error", "reason": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
