---
name: jackie-web
description: Web search, URL/PDF/YouTube summarization, and browser automation — search the web via Tavily, summarize any URL or file, and browse pages with Chromium.
metadata:
  {
    "openclaw":
      {
        "emoji": "🌐",
        "requires": { "anyBins": ["python3", "python"], "env": ["TAVILY_API_KEY"] },
      },
  }
---

# Jackie Web

Search the web, summarize URLs/PDFs/YouTube, and automate browser interactions. All in one skill.

## When to use

- User wants to search for something on the web
- User shares a URL and wants a summary or the content extracted
- User wants to read a page that requires JavaScript rendering (XiaoHongShu, SPAs)
- User shares a YouTube link and wants a transcript or summary
- User shares a PDF URL

---

## Web Search (Tavily)

```bash
python3 {baseDir}/scripts/bridge.py search --query "agentic RL papers 2025" --count 5
```

Searches the web and returns titles, URLs, and content snippets. Uses the Tavily Search API.

**Options:**

- `--count N` — number of results (default 5, max 20)
- `--search-depth basic|advanced` — basic is faster, advanced is more thorough (default basic)
- `--include-domains "arxiv.org,github.com"` — limit to specific domains
- `--exclude-domains "pinterest.com"` — exclude domains

### Get full page content via search

```bash
python3 {baseDir}/scripts/bridge.py search --query "site:xiaohongshu.com agentic RL" --include-raw-content
```

Returns the full extracted text content of each result (not just snippets).

---

## Summarize URL

```bash
python3 {baseDir}/scripts/bridge.py summarize --url "https://example.com/article"
```

Fetches a URL and returns a structured summary. Works with articles, blog posts, docs, and most web pages.

**Options:**

- `--max-length 500` — target summary length in words (default 300)
- `--extract-only` — return raw extracted text without summarizing
- `--language zh` — summarize in a specific language

### Summarize a YouTube video

```bash
python3 {baseDir}/scripts/bridge.py summarize --url "https://youtube.com/watch?v=..." --youtube
```

Extracts the transcript (via captions API) and summarizes. Add `--extract-only` for full transcript.

---

## Browse (Chromium)

For pages that need JavaScript rendering (SPAs, XiaoHongShu, dynamic content):

```bash
python3 {baseDir}/scripts/bridge.py browse --url "https://www.xiaohongshu.com/explore/..." --wait 3
```

Opens the page in headless Chromium, waits for JS to render, and returns the text content.

**Options:**

- `--wait N` — seconds to wait for JS rendering (default 2)
- `--screenshot` — also save a screenshot to /tmp/browse-screenshot.png
- `--selector "article"` — extract only content matching a CSS selector
- `--scroll` — scroll the page to trigger lazy-loaded content

### Read images on a page

```bash
python3 {baseDir}/scripts/bridge.py browse --url "https://www.xiaohongshu.com/..." --screenshot --wait 3
```

Takes a screenshot that Jackie can then view with vision capabilities.

---

## Extract (fetch without browser)

For simple pages that don't need JS:

```bash
python3 {baseDir}/scripts/bridge.py extract --url "https://arxiv.org/abs/2401.12345"
```

Lightweight fetch + HTML-to-text extraction. Much faster than browse. Falls back to browse if content looks empty/JS-dependent.

**Options:**

- `--max-chars 5000` — truncate output (default 10000)
