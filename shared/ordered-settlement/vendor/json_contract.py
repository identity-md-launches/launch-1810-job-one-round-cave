#!/usr/bin/env python3
"""Small explicit JSON structural contracts; deliberately not full JSON Schema."""
import argparse
import json
import math
import re
import sys
from pathlib import Path

KEYS = {"type", "required", "properties", "additionalProperties", "items",
        "minItems", "maxItems", "minLength", "maxLength", "minimum", "maximum",
        "enum", "pattern", "prefixItems", "uniqueItems"}
TYPES = {"object", "array", "string", "integer", "number", "boolean", "null"}


class ContractError(ValueError):
    pass


def pointer(parent, key):
    return parent + "/" + str(key).replace("~", "~0").replace("/", "~1")


def same(a, b):
    # JSON boolean true must not compare equal to the JSON number 1.
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def prepare(c, path=""):
    """Reject misspelled, unsupported and contradictory contract rules."""
    def fail(message):
        raise ContractError(f"contract {path or '/'}: {message}")
    if not isinstance(c, dict):
        fail("must be an object")
    if set(c) - KEYS:
        fail("unsupported rules: " + ", ".join(sorted(set(c) - KEYS)))
    t = c.get("type")
    if not isinstance(t, str) or t not in TYPES:
        fail("type must name one supported JSON type")
    permitted = {"type", "enum"}
    permitted |= {"object": {"properties", "required", "additionalProperties"},
                  "array": {"items", "minItems", "maxItems", "prefixItems", "uniqueItems"},
                  "string": {"minLength", "maxLength", "pattern"},
                  "number": {"minimum", "maximum"},
                  "integer": {"minimum", "maximum"}}.get(t, set())
    if set(c) - permitted:
        fail("rules incompatible with type: " + ", ".join(sorted(set(c) - permitted)))
    if "enum" in c and (not isinstance(c["enum"], list) or not c["enum"]):
        fail("enum must be a nonempty array")
    for lo, hi in (("minItems", "maxItems"), ("minLength", "maxLength"), ("minimum", "maximum")):
        for k in (lo, hi):
            if k in c:
                v = c[k]
                if type(v) not in (int, float) or (type(v) is float and not math.isfinite(v)):
                    fail(k + " must be a finite number")
                if k not in ("minimum", "maximum") and (type(v) is not int or v < 0):
                    fail(k + " must be a nonnegative integer")
        if lo in c and hi in c and c[lo] > c[hi]:
            fail(lo + " exceeds " + hi)
    if "pattern" in c:
        if not isinstance(c["pattern"], str):
            fail("pattern must be a string")
        try:
            re.compile(c["pattern"])
        except re.error as exc:
            fail("invalid Python regular expression: " + str(exc))
    if t == "object":
        props = c.get("properties", {})
        required = c.get("required", [])
        if not isinstance(props, dict):
            fail("properties must be an object")
        if not isinstance(required, list) or any(not isinstance(k, str) for k in required):
            fail("required must be an array of property names")
        if len(required) != len(set(required)) or any(k not in props for k in required):
            fail("required names must be unique and declared in properties")
        if "additionalProperties" in c and type(c["additionalProperties"]) is not bool:
            fail("additionalProperties must be boolean")
        for k, child in props.items():
            prepare(child, pointer(path, k))
    if "items" in c:
        prepare(c["items"], pointer(path, "items"))
    if "prefixItems" in c:
        if not isinstance(c["prefixItems"], list):
            fail("prefixItems must be an array of contracts")
        for i, child in enumerate(c["prefixItems"]):
            prepare(child, pointer(pointer(path, "prefixItems"), i))
    if "uniqueItems" in c and type(c["uniqueItems"]) is not bool:
        fail("uniqueItems must be boolean")
    return c


def validate(value, c, path=""):
    errors = []
    def add(rule, message, at=path):
        errors.append({"path": at, "rule": rule, "message": message})
    t = c["type"]
    valid = {"object": isinstance(value, dict), "array": isinstance(value, list),
             "string": isinstance(value, str), "boolean": type(value) is bool,
             "null": value is None, "integer": type(value) is int,
             "number": type(value) in (int, float)}[t]
    if not valid:
        add("type", "expected " + t)
        return errors
    if "enum" in c and not any(same(value, x) for x in c["enum"]):
        add("enum", "value is not an allowed choice")
    if t == "object":
        props = c.get("properties", {})
        for k in c.get("required", []):
            if k not in value:
                add("required", "missing property", pointer(path, k))
        for k, v in value.items():
            if k in props:
                errors.extend(validate(v, props[k], pointer(path, k)))
            elif c.get("additionalProperties", True) is False:
                add("additionalProperties", "unexpected property", pointer(path, k))
    elif t in ("string", "array"):
        lo, hi = ("minLength", "maxLength") if t == "string" else ("minItems", "maxItems")
        if lo in c and len(value) < c[lo]:
            add(lo, f"length must be at least {c[lo]}")
        if hi in c and len(value) > c[hi]:
            add(hi, f"length must be at most {c[hi]}")
        if t == "string" and "pattern" in c and re.search(c["pattern"], value) is None:
            add("pattern", "does not match the required pattern")
        if t == "array" and "items" in c:
            for i in range(len(c.get("prefixItems", [])), len(value)):
                v = value[i]
                errors.extend(validate(v, c["items"], pointer(path, i)))
        if t == "array":
            for i, child in enumerate(c.get("prefixItems", [])):
                if i < len(value):
                    errors.extend(validate(value[i], child, pointer(path, i)))
            if c.get("uniqueItems", False):
                for i, v in enumerate(value):
                    earlier = next((j for j in range(i) if same(v, value[j])), None)
                    if earlier is not None:
                        add("uniqueItems", f"duplicates item at {pointer(path, earlier)}",
                            pointer(path, i))
    elif t in ("number", "integer"):
        for k, fails in (("minimum", lambda x: value < x), ("maximum", lambda x: value > x)):
            if k in c and fails(c[k]):
                add(k, f"must respect {k} {c[k]}")
    return errors


def workspace_file(name):
    root = Path.cwd().resolve()
    p = (root / name).resolve()
    if not p.is_relative_to(root):
        raise ValueError("input must be inside the current workspace")
    if any(part.startswith(".") for part in p.relative_to(root).parts):
        raise ValueError("hidden workspace paths are not accepted")
    if not p.is_file() or p.stat().st_size > 1_000_000:
        raise ValueError("input must be a regular file at most 1 MB")
    return p


def load(name):
    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                raise ValueError("duplicate JSON property: " + key)
            result[key] = value
        return result
    def finite(text):
        v = float(text)
        if not math.isfinite(v):
            raise ValueError("JSON number must be finite")
        return v
    def reject(text):
        raise ValueError("invalid JSON constant: " + text)
    return json.loads(workspace_file(name).read_text(encoding="utf-8"),
                      object_pairs_hook=pairs, parse_float=finite, parse_constant=reject)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract")
    parser.add_argument("document")
    args = parser.parse_args()
    try:
        contract = prepare(load(args.contract))
        errors = validate(load(args.document), contract)
        print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
        return 1 if errors else 0
    except (ValueError, OSError, RecursionError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
