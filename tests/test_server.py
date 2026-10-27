"""Run: python3 -m unittest discover -s tests -v   (from the package root)"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kjv_verse_mcp import bible, server  # noqa: E402


class Bible(unittest.TestCase):
    def test_counts(self):
        verses, order, _, bk = bible.load()
        self.assertEqual(len(order), 31102)
        self.assertEqual(len(bk), 66)
        self.assertEqual(bk["PSA"], 150)

    def test_john_3_16(self):
        p = bible.passage("John 3:16")[0]
        self.assertEqual(p["reference"], "John 3:16")
        self.assertTrue(p["text"].startswith("For God so loved the world"))

    def test_aliases(self):
        for r in ["Jn 3:16", "jhn 3.16", "JOHN 3 : 16", "joh 3:16"]:
            self.assertEqual(bible.passage(r)[0]["reference"], "John 3:16", r)
        self.assertEqual(bible.passage("1 Cor 13:4-7")[0]["reference"], "1 Corinthians 13:4-7")
        self.assertEqual(bible.passage("I Corinthians 13:13")[0]["reference"], "1 Corinthians 13:13")
        self.assertEqual(bible.passage("Song of Solomon 2:1")[0]["reference"], "Song of Solomon 2:1")
        self.assertEqual(bible.passage("Rev 22:21")[0]["reference"], "Revelation 22:21")

    def test_chapter_and_cross_chapter(self):
        p = bible.passage("Psalm 23")[0]
        self.assertEqual((p["reference"], len(p["verses"])), ("Psalm 23", 6))
        p = bible.passage("Gen 1:31-2:3")[0]
        self.assertEqual(len(p["verses"]), 4)
        self.assertEqual(p["reference"], "Genesis 1:31-2:3")

    def test_single_chapter_book(self):
        self.assertEqual(bible.passage("Jude 3")[0]["reference"], "Jude 1:3")
        self.assertEqual(len(bible.passage("Philemon 4-6")[0]["verses"]), 3)

    def test_multi(self):
        self.assertEqual(len(bible.passage("John 3:16; Rom 8:28")), 2)

    def test_italics(self):
        raw = bible.passage("Gen 1:2", "brackets")[0]["text"]
        self.assertIn("[was]", raw)
        self.assertNotIn("[", bible.passage("Gen 1:2")[0]["text"])
        self.assertIn("*was*", bible.passage("Gen 1:2", "markdown")[0]["text"])

    def test_errors(self):
        for bad in ["John 22:1", "John 3:99", "Hezekiah 1:1", "Psalm 151", "John 3:18-16", "", "Ps 1-150"]:
            with self.assertRaises(bible.RefError, msg=bad):
                bible.passage(bad)

    def test_search(self):
        r = bible.search("living water")
        self.assertGreaterEqual(r["total_matches"], 2)
        self.assertTrue(any(h["reference"].startswith("John 4:10") for h in r["results"]))
        self.assertEqual(bible.search("Jesus wept", book="John")["results"][0]["reference"], "John 11:35")

    def test_votd_deterministic(self):
        a = bible.verse_of_the_day("2026-10-26")
        self.assertEqual(a, bible.verse_of_the_day("2026-10-26"))
        self.assertIn(a["reference"], [bible.passage(r)[0]["reference"] for r in bible.POPULAR])


class Protocol(unittest.TestCase):
    def rpc(self, msgs):
        inp = "\n".join(json.dumps(m) for m in msgs) + "\n"
        out = subprocess.run([sys.executable, "-m", "kjv_verse_mcp"], input=inp, capture_output=True,
                             text=True, cwd=ROOT, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return [json.loads(l) for l in out.stdout.splitlines() if l.strip()]

    def test_stdio_session(self):
        r = self.rpc([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "get_passage", "arguments": {"reference": "John 11:35"}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "get_passage", "arguments": {"reference": "John 99:1"}}},
            {"jsonrpc": "2.0", "id": 5, "method": "nope"},
            {"jsonrpc": "2.0", "id": 6, "method": "ping"},
        ])
        self.assertEqual([m["id"] for m in r], [1, 2, 3, 4, 5, 6])  # notification got no reply
        self.assertEqual(r[0]["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual({t["name"] for t in r[1]["result"]["tools"]}, {"get_passage", "search_kjv", "verse_of_the_day", "list_books"})
        self.assertIn("Jesus wept.", r[2]["result"]["content"][0]["text"])
        self.assertTrue(r[3]["result"]["isError"])
        self.assertEqual(r[4]["error"]["code"], -32601)
        self.assertEqual(r[5]["result"], {})

    def test_handle_unknown_tool(self):
        r = server.handle({"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": "x"}})
        self.assertEqual(r["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
