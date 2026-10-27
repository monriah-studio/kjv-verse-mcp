# KJV Verse MCP

Offline **King James Version** lookup for AI assistants, as an MCP server.
Zero dependencies (Python standard library only), no API key, no network calls, no tracking.
The full 1769 KJV text (31,102 verses, 66 books, public domain) ships inside the package (1.3 MB gzipped).

## Tools

| Tool | What it does | Example input |
|---|---|---|
| `get_passage` | Verse, range, cross-chapter range, whole chapter, or several refs joined by `;` | `{"reference": "Psalm 23; 1 Cor 13:4-7"}` |
| `search_kjv` | Word / exact-phrase search, optional book filter, total count + first N hits | `{"query": "living water", "book": "John"}` |
| `verse_of_the_day` | Deterministic verse for a date (same date → same verse) | `{"date": "2026-10-26"}` |
| `list_books` | 66 books with chapter counts and testament | `{}` |

All tools are read-only (`readOnlyHint: true`) and return both readable text and `structuredContent` JSON.
Every result is labelled with the reference and "(KJV)" so the assistant can cite it.

Reference parsing understands common abbreviations (`Jn`, `Ps`, `1 Cor`, `I Corinthians`, `Rev`, `Song`),
`:` or `.` separators, en dashes, single-chapter books (`Jude 3`), and returns clear errors for
references that do not exist (`John 22:1` → "John has 21 chapters").

`italics` option: the KJV prints translator-supplied words in italics (stored as `[brackets]`).
`plain` (default) removes the marks, `brackets` keeps them, `markdown` renders them as `*word*`.

## Install

Requires Python 3.9+.

```bash
pip install .            # from this folder (or: pipx install .)
kjv-verse-mcp            # speaks MCP over stdio
```

### Claude Desktop / Claude Code / Cursor / VS Code

```json
{
  "mcpServers": {
    "kjv": { "command": "kjv-verse-mcp" }
  }
}
```

Without installing: `{"command": "python3", "args": ["-m", "kjv_verse_mcp"], "cwd": "/path/to/kjv-verse-mcp"}`.

## Example

> **You:** What does the Bible say about worry? Quote KJV with references.
>
> **Assistant** (calls `search_kjv {"query":"take no thought"}` then `get_passage {"reference":"Matthew 6:33-34; Philippians 4:6-7"}`):
>
> Matthew 6:34 (KJV): "Take therefore no thought for the morrow: for the morrow shall take thought for the things of itself. Sufficient unto the day is the evil thereof." …

## Tests

```bash
python3 -m unittest discover -s tests -v      # 12 tests: parsing, search, errors, full stdio JSON-RPC session
pip install mcp && python3 tests/sdk_interop.py   # optional: drives the server with the official MCP Python SDK client
```

## Notes and limits

- Text: eBible.org `eng-kjv2006` (Crosswire), protocanon only (no Apocrypha). Psalm superscriptions are part of verse 1 in this edition
  (e.g. Psalm 23:1 begins "A Psalm of David.").
- Max 200 verses per `get_passage` call; search returns at most 100 hits per call (total count always reported).
- Protocol: MCP stdio, protocol versions 2025-06-18 / 2025-03-26 / 2024-11-05 (tested with MCP Python SDK 2.3.0).

## License

Code: MIT (see LICENSE). Bible text: public domain (see LICENSE for the UK Crown-patent note).
