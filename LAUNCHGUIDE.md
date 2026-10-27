# LAUNCHGUIDE — KJV Verse MCP
<!-- mcp-marketplace.io reads this file to pre-fill the submit form -->

**Name:** KJV Verse MCP
**Tagline:** Offline King James Bible lookup and search for any AI assistant. No API key.
**Category:** Knowledge & Reference (fallback: Education / Productivity)
**Pricing:** Free
**Transport:** stdio (local)
**Runtime:** Python 3.9+, zero dependencies
**Install command:** `pip install kjv-verse-mcp` *(or from the repo: `pip install git+https://github.com/<OWNER>/kjv-verse-mcp`)*
**Run command:** `kjv-verse-mcp`
**Required env vars / secrets:** none
**Network access:** none (fully offline)
**Tools:** get_passage, search_kjv, verse_of_the_day, list_books

## Description
Look up and search the public-domain King James Version (1769 text, 31,102 verses) without leaving your assistant.
Accepts real-world references ("Jn 3:16", "1 Cor 13:4-7", "Psalm 23; Rom 8:28", "Gen 1:31-2:3"), returns exact text with the
reference attached for citation, and gives clear errors instead of hallucinated verses. Ships the whole text inside the package:
no API key, no rate limits, no network, no tracking.

## Use cases
- Quote scripture accurately in sermons notes, devotionals, social posts and study guides
- Check that a verse an AI "remembers" actually says that (stop misquotes)
- Find every verse with a word or phrase ("fear not" → 62 verses)
- Daily verse for apps, newsletters and bots (deterministic by date)

## Tags
bible, kjv, king-james, scripture, verse, christian, devotional, offline, reference, citation
