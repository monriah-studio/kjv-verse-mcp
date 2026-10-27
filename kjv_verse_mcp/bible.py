"""Offline KJV (1769 standard text, public domain) data + reference parsing.

No network, no API keys, no dependencies beyond the Python standard library.
"""
from __future__ import annotations

import datetime as _dt
import gzip
import hashlib
import re
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).with_name("data") / "kjv.tsv.gz"

# (code, canonical name, extra aliases)
BOOKS = [
    ("GEN", "Genesis", ["gen", "ge", "gn"]),
    ("EXO", "Exodus", ["exod", "exo", "ex"]),
    ("LEV", "Leviticus", ["lev", "le", "lv"]),
    ("NUM", "Numbers", ["num", "nu", "nm"]),
    ("DEU", "Deuteronomy", ["deut", "deu", "dt"]),
    ("JOS", "Joshua", ["josh", "jos"]),
    ("JDG", "Judges", ["judg", "jdg", "jg"]),
    ("RUT", "Ruth", ["ru", "rth"]),
    ("1SA", "1 Samuel", ["1sam", "1sa", "1 sam", "i samuel", "first samuel"]),
    ("2SA", "2 Samuel", ["2sam", "2sa", "2 sam", "ii samuel", "second samuel"]),
    ("1KI", "1 Kings", ["1kgs", "1ki", "1 kgs", "i kings", "first kings"]),
    ("2KI", "2 Kings", ["2kgs", "2ki", "2 kgs", "ii kings", "second kings"]),
    ("1CH", "1 Chronicles", ["1chr", "1ch", "1 chron", "i chronicles", "first chronicles"]),
    ("2CH", "2 Chronicles", ["2chr", "2ch", "2 chron", "ii chronicles", "second chronicles"]),
    ("EZR", "Ezra", ["ezr"]),
    ("NEH", "Nehemiah", ["neh", "ne"]),
    ("EST", "Esther", ["esth", "est", "es"]),
    ("JOB", "Job", ["jb"]),
    ("PSA", "Psalms", ["psalm", "ps", "psa", "pss", "psm"]),
    ("PRO", "Proverbs", ["prov", "pro", "pr", "prv"]),
    ("ECC", "Ecclesiastes", ["eccl", "ecc", "ec", "qoh"]),
    ("SOL", "Song of Solomon", ["song", "song of songs", "sos", "canticles", "sng"]),
    ("ISA", "Isaiah", ["isa", "is"]),
    ("JER", "Jeremiah", ["jer", "je", "jr"]),
    ("LAM", "Lamentations", ["lam", "la"]),
    ("EZE", "Ezekiel", ["ezek", "eze", "ezk"]),
    ("DAN", "Daniel", ["dan", "da", "dn"]),
    ("HOS", "Hosea", ["hos", "ho"]),
    ("JOE", "Joel", ["joel", "jl"]),
    ("AMO", "Amos", ["am", "amo"]),
    ("OBA", "Obadiah", ["obad", "oba", "ob"]),
    ("JON", "Jonah", ["jonah", "jnh", "jon"]),
    ("MIC", "Micah", ["mic", "mc"]),
    ("NAH", "Nahum", ["nah", "na"]),
    ("HAB", "Habakkuk", ["hab", "hb"]),
    ("ZEP", "Zephaniah", ["zeph", "zep", "zp"]),
    ("HAG", "Haggai", ["hag", "hg"]),
    ("ZEC", "Zechariah", ["zech", "zec", "zc"]),
    ("MAL", "Malachi", ["mal", "ml"]),
    ("MAT", "Matthew", ["matt", "mat", "mt"]),
    ("MAR", "Mark", ["mrk", "mar", "mk", "mr"]),
    ("LUK", "Luke", ["luk", "lk"]),
    ("JOH", "John", ["jn", "jhn", "joh"]),
    ("ACT", "Acts", ["act", "ac"]),
    ("ROM", "Romans", ["rom", "ro", "rm"]),
    ("1CO", "1 Corinthians", ["1cor", "1co", "1 cor", "i corinthians", "first corinthians"]),
    ("2CO", "2 Corinthians", ["2cor", "2co", "2 cor", "ii corinthians", "second corinthians"]),
    ("GAL", "Galatians", ["gal", "ga"]),
    ("EPH", "Ephesians", ["eph", "ephes"]),
    ("PHI", "Philippians", ["phil", "php", "pp"]),
    ("COL", "Colossians", ["col"]),
    ("1TH", "1 Thessalonians", ["1thess", "1th", "1 thess", "i thessalonians", "first thessalonians"]),
    ("2TH", "2 Thessalonians", ["2thess", "2th", "2 thess", "ii thessalonians", "second thessalonians"]),
    ("1TI", "1 Timothy", ["1tim", "1ti", "1 tim", "i timothy", "first timothy"]),
    ("2TI", "2 Timothy", ["2tim", "2ti", "2 tim", "ii timothy", "second timothy"]),
    ("TIT", "Titus", ["tit"]),
    ("PHM", "Philemon", ["philem", "phm", "phlm"]),
    ("HEB", "Hebrews", ["heb"]),
    ("JAM", "James", ["jas", "jam", "jm"]),
    ("1PE", "1 Peter", ["1pet", "1pe", "1 pet", "i peter", "first peter"]),
    ("2PE", "2 Peter", ["2pet", "2pe", "2 pet", "ii peter", "second peter"]),
    ("1JO", "1 John", ["1jn", "1jo", "1 jn", "1john", "i john", "first john"]),
    ("2JO", "2 John", ["2jn", "2jo", "2 jn", "2john", "ii john", "second john"]),
    ("3JO", "3 John", ["3jn", "3jo", "3 jn", "3john", "iii john", "third john"]),
    ("JUD", "Jude", ["jud", "jd"]),
    ("REV", "Revelation", ["rev", "re", "rv", "revelations", "the revelation", "apocalypse"]),
]
NAME = {c: n for c, n, _ in BOOKS}
ORDER = {c: i for i, (c, _, _) in enumerate(BOOKS)}


def _key(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower().replace(".", " ")).replace(" ", "")


ALIAS: dict[str, str] = {}
for _c, _n, _al in BOOKS:
    for _a in [_c, _n, *_al]:
        ALIAS[_key(_a)] = _c


@lru_cache(maxsize=1)
def load():
    """Return (verses dict[(book,ch,v)] -> text, ordered key list, chapter->max verse, book->max chapter)."""
    verses, order, chmax, bkmax = {}, [], {}, {}
    with gzip.open(DATA, "rt", encoding="utf-8") as f:
        for line in f:
            b, c, v, t = line.rstrip("\n").split("\t", 3)
            k = (b, int(c), int(v))
            verses[k] = t
            order.append(k)
            chmax[(b, k[1])] = max(chmax.get((b, k[1]), 0), k[2])
            bkmax[b] = max(bkmax.get(b, 0), k[1])
    return verses, order, chmax, bkmax


@lru_cache(maxsize=1)
def _pos():
    return {k: i for i, k in enumerate(load()[1])}


def clean(text: str, italics: str = "plain") -> str:
    """KJV marks translator-supplied words with [brackets]. italics: plain|brackets|markdown."""
    if italics == "brackets":
        return text
    if italics == "markdown":
        return re.sub(r"\[([^\]]+)\]", r"*\1*", text)
    return re.sub(r"\[([^\]]+)\]", r"\1", text)


class RefError(ValueError):
    pass


_REF = re.compile(
    r"^\s*(?P<book>(?:[1-3]|i{1,3})?\s*[a-z][a-z .]*?)\s*"
    r"(?P<c1>\d+)(?:\s*[:.]\s*(?P<v1>\d+))?"
    r"(?:\s*[-\u2013\u2014]\s*(?:(?P<c2>\d+)\s*[:.]\s*)?(?P<v2>\d+))?\s*$",
    re.I,
)


def resolve_book(s: str) -> str:
    k = _key(s)
    if k in ALIAS:
        return ALIAS[k]
    # unique prefix match on canonical names, e.g. "Phile" -> Philemon
    hits = {c for a, c in ALIAS.items() if a.startswith(k) and len(k) >= 3}
    if len(hits) == 1:
        return hits.pop()
    raise RefError(f"Unknown or ambiguous book: {s!r}")


def parse_one(ref: str):
    """Parse 'John 3:16', 'Jn 3:16-18', 'Psalm 23', '1 Cor 13:4-7', 'Gen 1:31-2:3' -> (start, end) keys."""
    m = _REF.match(ref)
    if not m:
        raise RefError(f"Could not parse reference: {ref!r}")
    _, _, chmax, bkmax = load()
    b = resolve_book(m["book"])
    c1 = int(m["c1"])
    if bkmax[b] == 1 and m["v1"] is None and not m["c2"]:
        # single-chapter books (Obadiah, Philemon, 2-3 John, Jude): "Jude 3" means verse 3
        v1, v2 = c1, int(m["v2"]) if m["v2"] else c1
        for v in (v1, v2):
            if v < 1 or v > chmax[(b, 1)]:
                raise RefError(f"{NAME[b]} 1:{v} does not exist ({NAME[b]} has {chmax[(b, 1)]} verses)")
        if v2 < v1:
            raise RefError(f"Range runs backwards in {ref!r}")
        return (b, 1, v1), (b, 1, v2)
    if c1 < 1 or c1 > bkmax[b]:
        raise RefError(f"{NAME[b]} has {bkmax[b]} chapters (asked for {c1})")
    if m["v1"] is None:  # whole chapter, or chapter range "Psalm 1-2"
        c2 = int(m["v2"]) if m["v2"] and not m["c2"] else c1
        if c2 < c1 or c2 > bkmax[b]:
            raise RefError(f"Bad chapter range in {ref!r}")
        return (b, c1, 1), (b, c2, chmax[(b, c2)])
    v1 = int(m["v1"])
    c2 = int(m["c2"]) if m["c2"] else c1
    v2 = int(m["v2"]) if m["v2"] else v1
    for c, v in ((c1, v1), (c2, v2)):
        if c > bkmax[b] or v < 1 or v > chmax.get((b, c), 0):
            raise RefError(f"{NAME[b]} {c}:{v} does not exist (chapter {c} has {chmax.get((b, c), 0)} verses)")
    if (c2, v2) < (c1, v1):
        raise RefError(f"Range runs backwards in {ref!r}")
    return (b, c1, v1), (b, c2, v2)


def _bname(b, c1, c2):
    return "Psalm" if b == "PSA" and c1 == c2 else NAME[b]


def label(start, end) -> str:
    b, c1, v1 = start
    _, c2, v2 = end
    n = _bname(b, c1, c2)
    if c1 == c2 and v1 == 1 and v2 == load()[2][(b, c1)] and start != end:
        return f"{n} {c1}"
    if start == end:
        return f"{n} {c1}:{v1}"
    if c1 == c2:
        return f"{n} {c1}:{v1}-{v2}"
    return f"{NAME[b]} {c1}:{v1}-{c2}:{v2}"


MAX_VERSES = 200


def passage(reference: str, italics: str = "plain"):
    """Look up one or more references separated by ';'. Returns list of passages."""
    verses, order, _, _ = load()
    out = []
    for part in [p for p in re.split(r"[;\n]", reference) if p.strip()]:
        start, end = parse_one(part)
        i, j = _pos()[start], _pos()[end]
        if j - i + 1 > MAX_VERSES:
            raise RefError(f"{label(start, end)} is {j - i + 1} verses; limit is {MAX_VERSES} per request")
        vs = [{"book": NAME[k[0]], "chapter": k[1], "verse": k[2], "text": clean(verses[k], italics)} for k in order[i : j + 1]]
        out.append({"reference": label(start, end), "translation": "KJV", "verses": vs,
                    "text": " ".join(v["text"] for v in vs)})
    if not out:
        raise RefError("Empty reference")
    return out


def search(query: str, book: str | None = None, limit: int = 10, whole_word: bool = True):
    verses, order, _, _ = load()
    limit = max(1, min(int(limit or 10), 100))
    bcode = resolve_book(book) if book else None
    q = query.strip()
    if not q:
        raise RefError("Empty query")
    phrase = q.strip('"')
    pat = re.compile((r"\b%s\b" if whole_word else "%s") % re.escape(phrase).replace(r"\ ", r"\s+"), re.I)
    hits, total = [], 0
    for k in order:
        if bcode and k[0] != bcode:
            continue
        t = clean(verses[k])
        if pat.search(t):
            total += 1
            if len(hits) < limit:
                hits.append({"reference": f"{_bname(k[0], 1, 1)} {k[1]}:{k[2]}", "text": t})
    return {"query": phrase, "book": NAME[bcode] if bcode else None, "total_matches": total, "results": hits}


def verse_of_the_day(date: str | None = None, pool: str = "popular"):
    """Deterministic: same date -> same verse, so it is reproducible and citable."""
    d = _dt.date.fromisoformat(date) if date else _dt.date.today()
    h = int(hashlib.sha256(d.isoformat().encode()).hexdigest(), 16)
    if pool == "popular":
        ref = POPULAR[h % len(POPULAR)]
        p = passage(ref)[0]
    else:
        verses, order, _, _ = load()
        k = order[h % len(order)]
        p = passage(f"{NAME[k[0]]} {k[1]}:{k[2]}")[0]
    p["date"] = d.isoformat()
    return p


POPULAR = [
    "John 3:16", "Jeremiah 29:11", "Philippians 4:13", "Romans 8:28", "Proverbs 3:5-6", "Isaiah 41:10",
    "Psalm 23:1", "Joshua 1:9", "Matthew 11:28", "Psalm 46:1", "Romans 12:2", "Galatians 5:22-23",
    "Hebrews 11:1", "2 Timothy 1:7", "1 Corinthians 13:4-7", "Psalm 119:105", "Matthew 6:33",
    "Isaiah 40:31", "Romans 15:13", "Psalm 37:4", "Philippians 4:6-7", "Lamentations 3:22-23",
    "Psalm 27:1", "Ephesians 2:8-9", "1 Peter 5:7", "Psalm 121:1-2", "Matthew 5:16", "James 1:5",
    "Psalm 34:18", "Deuteronomy 31:6", "Micah 6:8", "Colossians 3:23", "Romans 5:8", "Psalm 91:1-2",
    "John 14:27", "Zephaniah 3:17", "Nahum 1:7", "Psalm 139:14", "2 Corinthians 5:17", "1 John 4:19",
]


def books():
    _, _, _, bkmax = load()
    return [{"code": c, "name": n, "chapters": bkmax[c], "testament": "OT" if ORDER[c] < 39 else "NT"} for c, n, _ in BOOKS]
