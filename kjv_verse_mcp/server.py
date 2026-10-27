"""KJV Verse MCP server (stdio transport, newline-delimited JSON-RPC 2.0).

Zero dependencies: pure Python 3.9+ standard library. Fully offline.
Implements MCP lifecycle (initialize / notifications/initialized / ping) and tools (tools/list, tools/call).
"""
from __future__ import annotations

import json
import sys

from . import __version__, bible

SUPPORTED = ["2025-06-18", "2025-03-26", "2024-11-05"]

ITALICS = {"type": "string", "enum": ["plain", "brackets", "markdown"], "default": "plain",
           "description": "How to show the KJV's translator-supplied words: plain (no marks), brackets ([was]) or markdown (*was*)."}

TOOLS = [
    {
        "name": "get_passage",
        "title": "Get KJV verse or passage",
        "description": ("Look up King James Version (1769, public domain) text by reference. Accepts single verses "
                        "('John 3:16'), ranges ('1 Cor 13:4-7', 'Gen 1:31-2:3'), whole chapters ('Psalm 23'), and several "
                        "references separated by ';'. Common abbreviations work (Jn, Ps, 1 Cor, Rev). Max 200 verses per call."),
        "inputSchema": {"type": "object", "properties": {
            "reference": {"type": "string", "description": "e.g. 'John 3:16' or 'Psalm 23; Romans 8:28'"},
            "italics": ITALICS}, "required": ["reference"], "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "openWorldHint": False, "idempotentHint": True},
    },
    {
        "name": "search_kjv",
        "title": "Search the KJV",
        "description": "Find KJV verses containing a word or exact phrase (case-insensitive). Optional book filter. Returns total match count and up to `limit` verses in canonical order.",
        "inputSchema": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Word or phrase, e.g. 'living water'"},
            "book": {"type": "string", "description": "Optional book name or abbreviation to restrict the search"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
            "whole_word": {"type": "boolean", "default": True}}, "required": ["query"], "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "openWorldHint": False, "idempotentHint": True},
    },
    {
        "name": "verse_of_the_day",
        "title": "KJV verse of the day",
        "description": "Deterministic verse for a date (same date always returns the same verse). pool='popular' picks from well-known encouraging verses; pool='all' picks from all 31,102 verses.",
        "inputSchema": {"type": "object", "properties": {
            "date": {"type": "string", "description": "ISO date YYYY-MM-DD; defaults to today (server local time)"},
            "pool": {"type": "string", "enum": ["popular", "all"], "default": "popular"}}, "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "openWorldHint": False, "idempotentHint": True},
    },
    {
        "name": "list_books",
        "title": "List KJV books",
        "description": "The 66 books of the KJV protocanon with chapter counts and testament.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "openWorldHint": False, "idempotentHint": True},
    },
]


def _fmt_passages(ps):
    lines = []
    for p in ps:
        lines.append(f"{p['reference']} (KJV)")
        if len(p["verses"]) == 1:
            lines.append(p["verses"][0]["text"])
        else:
            lines += [f"{v['chapter']}:{v['verse']} {v['text']}" for v in p["verses"]]
        lines.append("")
    return "\n".join(lines).strip()


def call_tool(name, args):
    args = args or {}
    if name == "get_passage":
        ps = bible.passage(args["reference"], args.get("italics", "plain"))
        return _fmt_passages(ps), {"passages": ps}
    if name == "search_kjv":
        r = bible.search(args["query"], args.get("book"), args.get("limit", 10), args.get("whole_word", True))
        head = f"{r['total_matches']} KJV verse(s) match {r['query']!r}" + (f" in {r['book']}" if r["book"] else "")
        body = "\n".join(f"{h['reference']}: {h['text']}" for h in r["results"])
        more = f"\n(showing first {len(r['results'])})" if r["total_matches"] > len(r["results"]) else ""
        return f"{head}\n{body}{more}".strip(), r
    if name == "verse_of_the_day":
        p = bible.verse_of_the_day(args.get("date"), args.get("pool", "popular"))
        return f"Verse of the day {p['date']}: {p['reference']} (KJV)\n{p['text']}", p
    if name == "list_books":
        b = bible.books()
        return "\n".join(f"{x['name']} ({x['chapters']} ch, {x['testament']})" for x in b), {"books": b}
    raise KeyError(name)


def handle(msg):
    """Return a response dict, or None for notifications."""
    mid = msg.get("id")
    method = msg.get("method")
    if mid is None:  # notification (e.g. notifications/initialized) -> no reply
        return None
    try:
        if method == "initialize":
            req = (msg.get("params") or {}).get("protocolVersion")
            ver = req if req in SUPPORTED else SUPPORTED[0]
            result = {"protocolVersion": ver,
                      "capabilities": {"tools": {"listChanged": False}},
                      "serverInfo": {"name": "kjv-verse-mcp", "title": "KJV Verse Lookup", "version": __version__},
                      "instructions": "Offline King James Version (1769, public domain). Use get_passage for references, search_kjv for words/phrases. Always cite the reference with (KJV)."}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            p = msg.get("params") or {}
            if p.get("name") not in {t["name"] for t in TOOLS}:
                return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"Unknown tool: {p.get('name')}"}}
            try:
                text, data = call_tool(p["name"], p.get("arguments"))
                result = {"content": [{"type": "text", "text": text}], "structuredContent": data, "isError": False}
            except (bible.RefError, ValueError, KeyError, TypeError) as e:
                result = {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}
        elif method in ("resources/list", "prompts/list"):
            result = {method.split("/")[0]: []}
        else:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Method not found: {method}"}}
        return {"jsonrpc": "2.0", "id": mid, "result": result}
    except Exception as e:  # never crash the stdio loop
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": f"Internal error: {e}"}}


def main():
    bible.load()  # warm the cache (~0.3 s)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        else:
            if isinstance(msg, list):  # batch (older protocol revisions)
                resp = [r for r in (handle(m) for m in msg) if r is not None] or None
            else:
                resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
