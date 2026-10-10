"""Claude Desktop/Codex stdio transport: python -m app.stdio

One JSON-RPC request per line. Writes only protocol messages to stdout.
"""
from __future__ import annotations
import json
import sys
from .mcp import process_rpc
from .json_safety import strict_json_loads


def run() -> None:
    for line in sys.stdin:
        try:
            payload = strict_json_loads(line)
            response = process_rpc(payload)
            if response is not None:
                print(json.dumps(response, ensure_ascii=False, separators=(',', ':')), flush=True)
        except (ValueError, UnicodeError) as exc:
            print(json.dumps({'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Parse error'}},ensure_ascii=False),flush=True)
        except Exception:
            # Never leak server internals or private data to clients.
            print(json.dumps({'jsonrpc':'2.0','id':None,'error':{'code':-32603,'message':'Internal error'}},ensure_ascii=False),flush=True)

if __name__ == '__main__':
    run()
