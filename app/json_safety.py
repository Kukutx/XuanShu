"""Strict JSON decoding shared by HTTP and stdio MCP transports.

The Python json module accepts NaN/Infinity and converts huge exponents to
infinity by default. Those are not interoperable JSON numbers, and can turn
framework response serialization into an HTTP 500. Reject them at ingress.
Reject duplicate object keys to avoid header/body interpretation ambiguity.
"""
from __future__ import annotations

import json
import math


def _constant(value: str):
    raise ValueError(f'Non-finite JSON value is not permitted: {value}')


def _finite_float(value: str) -> float:
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError('Non-finite JSON number is not permitted')
    return converted


def _unique_keys(pairs: list[tuple]):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON object key: {key!r}')
        result[key] = value
    return result


def strict_json_loads(value: bytes | str):
    """JSON RFC-compatible numeric input, unique keys and bounded depth."""
    try:
        result = json.loads(value, parse_constant=_constant, parse_float=_finite_float,
                            object_pairs_hook=_unique_keys)
    except RecursionError as exc:
        raise ValueError('JSON nesting is too deep') from exc

    # FastAPI's validation-error encoder can recursively walk a malformed body
    # to far deeper levels than the JSON decoder's own recursion ceiling.
    # Reject lone UTF-16 surrogates too: they cannot be encoded in UTF-8 JSON
    # responses and would otherwise cause a 500 from the response serializer.
    stack = [(result, 0)]
    while stack:
        item, depth = stack.pop()
        if depth > 64:
            raise ValueError('JSON nesting exceeds 64 levels')
        if isinstance(item, dict):
            for key, child in item.items():
                try:
                    key.encode('utf-8')
                except UnicodeEncodeError as exc:
                    raise ValueError('Invalid Unicode surrogate in JSON key') from exc
                stack.append((child, depth + 1))
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
        elif isinstance(item, str):
            try:
                item.encode('utf-8')
            except UnicodeEncodeError as exc:
                raise ValueError('Invalid Unicode surrogate in JSON string') from exc
    return result
