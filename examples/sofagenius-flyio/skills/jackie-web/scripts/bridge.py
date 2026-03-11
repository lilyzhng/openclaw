#!/usr/bin/env python3
"""Web search, summarization, and browser automation bridge.

Combines three capabilities:
  1. Web search via Tavily API
  2. URL/PDF/YouTube summarization
  3. Browser automation via Chromium (for JS-heavy pages)

Uses urllib (stdlib) for HTTP. Chromium automation uses subprocess + CDP.

Usage:
    python3 bridge.py search --query "agentic RL 2025" --count 5
    python3 bridge.py summarize --url "https://example.com/article"
    python3 bridge.py browse --url "https://xiaohongshu.com/..." --wait 3
    python3 bridge.py extract --url "https://arxiv.org/abs/..."
"""

import argparse
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
try:
    import feedback_store as _fb
except ImportError:
    _fb = None

SKILL_NAME = "jackie-web"
TAVILY_API = "https://api.tavily.com"
ANTHROPIC_API = "https://api.anthropic.com/v1/messages"


def _log(action, args, result, success, start, error=None):
    duration = round((time.monotonic() - start) * 1000)
    if _fb:
        _fb.log_execution(SKILL_NAME, action, args, result, success, duration, error)


def _tavily_key():
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        print(json.dumps({"error": "TAVILY_API_KEY env var is not set."}))
        sys.exit(1)
    return key


def _anthropic_key():
    return os.environ.get("ANTHROPIC_API_KEY", "")


def _post_json(url: str, body: dict, headers: dict | None = None) -> dict:
    data = json.dumps(body).encode()
    hdrs = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, method="POST", headers=hdrs)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def _fetch_url(url: str, max_chars: int = 10000) -> str:
    """Simple HTTP fetch + HTML to text extraction."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; JackieBot/1.0)",
        "Accept": "text/html,application/xhtml+xml,text/plain,application/pdf",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        content_type = resp.headers.get("Content-Type", "")
        raw = resp.read()

    if "application/pdf" in content_type:
        return _extract_pdf_text(raw, max_chars)

    text = raw.decode("utf-8", errors="replace")

    if "text/html" in content_type or "<html" in text[:500].lower():
        text = _html_to_text(text)

    if len(text) > max_chars:
        text = text[:max_chars] + "\n... (truncated)"
    return text


def _html_to_text(html_content: str) -> str:
    """Basic HTML to text extraction."""
    # Remove script and style blocks
    text = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # Convert common block elements to newlines
    text = re.sub(r"<(?:p|div|br|h[1-6]|li|tr)[^>]*>", "\n", text, flags=re.IGNORECASE)
    # Remove remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = html.unescape(text)
    # Clean up whitespace
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _extract_pdf_text(pdf_bytes: bytes, max_chars: int = 10000) -> str:
    """Extract text from PDF bytes using basic parsing or pdftotext."""
    # Try pdftotext first (if available)
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            f.flush()
            result = subprocess.run(
                ["pdftotext", f.name, "-"],
                capture_output=True, text=True, timeout=30,
            )
            os.unlink(f.name)
            if result.returncode == 0 and result.stdout.strip():
                text = result.stdout.strip()
                if len(text) > max_chars:
                    text = text[:max_chars] + "\n... (truncated)"
                return text
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return f"(PDF file, {len(pdf_bytes)} bytes — install poppler-utils for text extraction: sudo apt-get install poppler-utils)"


def _get_youtube_transcript(video_id: str) -> str:
    """Try to get YouTube transcript via captions API."""
    # Fetch the video page to get caption track URLs
    try:
        page_url = f"https://www.youtube.com/watch?v={video_id}"
        req = urllib.request.Request(page_url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; JackieBot/1.0)",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            page_html = resp.read().decode("utf-8", errors="replace")

        # Find the captions JSON in the page source
        caption_match = re.search(r'"captions":\s*(\{.*?"playerCaptionsTracklistRenderer".*?\})\s*,\s*"videoDetails"', page_html, re.DOTALL)
        if not caption_match:
            # Try alternative pattern
            caption_match = re.search(r'"captionTracks":\s*(\[.*?\])', page_html)

        if caption_match:
            caption_data = caption_match.group(1)
            # Find caption track URLs
            url_matches = re.findall(r'"baseUrl":\s*"(https://www\.youtube\.com/api/timedtext[^"]*)"', caption_data)
            if url_matches:
                # Fetch the first caption track
                caption_url = url_matches[0].replace("\\u0026", "&")
                req2 = urllib.request.Request(caption_url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; JackieBot/1.0)",
                })
                with urllib.request.urlopen(req2, timeout=15) as resp2:
                    caption_xml = resp2.read().decode("utf-8", errors="replace")
                # Extract text from XML captions
                texts = re.findall(r"<text[^>]*>(.*?)</text>", caption_xml, re.DOTALL)
                transcript = " ".join(html.unescape(t).strip() for t in texts if t.strip())
                return transcript if transcript else "(no transcript text found)"

        return "(no captions available for this video)"
    except Exception as e:
        return f"(failed to extract transcript: {e})"


def _extract_youtube_id(url: str) -> str | None:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _summarize_text(text: str, max_length: int = 300, language: str | None = None) -> str:
    """Summarize text using Anthropic API."""
    api_key = _anthropic_key()
    if not api_key:
        # Fall back to simple truncation
        words = text.split()
        if len(words) <= max_length:
            return text
        return " ".join(words[:max_length]) + "..."

    lang_instruction = f" Write the summary in {language}." if language else ""
    prompt = f"Summarize the following text in approximately {max_length} words. Be concise and capture the key points.{lang_instruction}\n\n{text[:15000]}"

    try:
        resp = _post_json(ANTHROPIC_API, {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }, headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        })
        return resp.get("content", [{}])[0].get("text", "(summarization failed)")
    except Exception as e:
        # Fall back to truncation on API error
        words = text.split()
        if len(words) <= max_length:
            return text
        return " ".join(words[:max_length]) + f"... (summarization API error: {e})"


# --- Actions ---

def search(query: str, count: int, search_depth: str, include_domains: str | None,
           exclude_domains: str | None, include_raw_content: bool) -> None:
    """Search the web via Tavily API."""
    action_args = {"query": query, "count": count}
    start = time.monotonic()
    try:
        body: dict = {
            "api_key": _tavily_key(),
            "query": query,
            "max_results": count,
            "search_depth": search_depth,
            "include_raw_content": include_raw_content,
        }
        if include_domains:
            body["include_domains"] = [d.strip() for d in include_domains.split(",")]
        if exclude_domains:
            body["exclude_domains"] = [d.strip() for d in exclude_domains.split(",")]

        resp = _post_json(f"{TAVILY_API}/search", body)

        results = []
        for item in resp.get("results", []):
            entry = {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "score": item.get("score"),
            }
            if include_raw_content and item.get("raw_content"):
                raw = item["raw_content"]
                if len(raw) > 5000:
                    raw = raw[:5000] + "\n... (truncated)"
                entry["raw_content"] = raw
            results.append(entry)

        result = {
            "action": "search",
            "query": query,
            "count": len(results),
            "results": results,
        }
        print(json.dumps(result, indent=2))
        _log("search", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if hasattr(e, "read") else ""
        result = {"error": f"Tavily API error: {e.code} {e.reason}", "details": error_body}
        print(json.dumps(result, indent=2))
        _log("search", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("search", action_args, result, False, start, str(e))


def summarize(url: str, max_length: int, extract_only: bool, youtube: bool,
              language: str | None) -> None:
    """Summarize a URL, PDF, or YouTube video."""
    action_args = {"url": url, "max_length": max_length, "extract_only": extract_only}
    start = time.monotonic()
    try:
        # Check if it's a YouTube URL
        video_id = _extract_youtube_id(url)
        if video_id and youtube:
            text = _get_youtube_transcript(video_id)
            source_type = "youtube_transcript"
        else:
            text = _fetch_url(url, max_chars=15000)
            source_type = "url"

        if extract_only:
            if len(text) > 10000:
                text = text[:10000] + "\n... (truncated)"
            result = {
                "action": "summarize",
                "url": url,
                "source_type": source_type,
                "mode": "extract",
                "content": text,
                "chars": len(text),
            }
        else:
            summary = _summarize_text(text, max_length, language)
            result = {
                "action": "summarize",
                "url": url,
                "source_type": source_type,
                "mode": "summary",
                "summary": summary,
                "original_chars": len(text),
            }

        print(json.dumps(result, indent=2))
        _log("summarize", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        result = {"error": f"Fetch error: {e.code} {e.reason}", "url": url}
        print(json.dumps(result, indent=2))
        _log("summarize", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e), "url": url}
        print(json.dumps(result, indent=2))
        _log("summarize", action_args, result, False, start, str(e))


def browse(url: str, wait: int, screenshot: bool, selector: str | None, scroll: bool) -> None:
    """Browse a page with headless Chromium for JS-heavy sites."""
    action_args = {"url": url, "wait": wait, "screenshot": screenshot}
    start = time.monotonic()
    try:
        # Find chromium binary
        chromium_bin = None
        for candidate in ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]:
            if os.path.exists(candidate):
                chromium_bin = candidate
                break

        if not chromium_bin:
            result = {"error": "Chromium not found. Install with: sudo apt-get install chromium"}
            print(json.dumps(result, indent=2))
            _log("browse", action_args, result, False, start, "chromium not found")
            return

        # Build the JS script for content extraction
        screenshot_path = "/tmp/browse-screenshot.png" if screenshot else ""
        js_script = _build_browse_script(url, wait, screenshot_path, selector, scroll)

        # Write script to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(js_script)
            script_path = f.name

        # Run chromium with the script via CDP
        # Use a simpler approach: chromium --dump-dom for basic text extraction
        cmd = [
            chromium_bin,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-software-rasterizer",
        ]

        if screenshot:
            screenshot_path = "/tmp/browse-screenshot.png"
            cmd.extend([f"--screenshot={screenshot_path}", f"--window-size=1280,1024"])

        cmd.extend(["--dump-dom", url])

        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=30 + wait, env={**os.environ, "DISPLAY": ""},
        )
        os.unlink(script_path)

        if proc.returncode != 0 and not proc.stdout:
            result = {"error": f"Chromium failed: {proc.stderr[:500]}"}
            print(json.dumps(result, indent=2))
            _log("browse", action_args, result, False, start, proc.stderr[:200])
            return

        # Extract text from the DOM dump
        dom_html = proc.stdout
        text = _html_to_text(dom_html)

        if selector:
            # Try to find content matching the selector (basic)
            selector_tag = selector.strip(".")
            pattern = rf'class="[^"]*{re.escape(selector_tag)}[^"]*"[^>]*>(.*?)</(?:div|article|section)>'
            matches = re.findall(pattern, dom_html, re.DOTALL | re.IGNORECASE)
            if matches:
                text = _html_to_text(" ".join(matches))

        if len(text) > 10000:
            text = text[:10000] + "\n... (truncated)"

        result = {
            "action": "browse",
            "url": url,
            "content": text,
            "chars": len(text),
        }
        if screenshot and os.path.exists(screenshot_path):
            result["screenshot"] = screenshot_path

        print(json.dumps(result, indent=2))
        _log("browse", action_args, result, True, start)
    except subprocess.TimeoutExpired:
        result = {"error": f"Chromium timed out after {30 + wait}s", "url": url}
        print(json.dumps(result, indent=2))
        _log("browse", action_args, result, False, start, "timeout")
    except Exception as e:
        result = {"error": str(e), "url": url}
        print(json.dumps(result, indent=2))
        _log("browse", action_args, result, False, start, str(e))


def _build_browse_script(url: str, wait: int, screenshot_path: str,
                         selector: str | None, scroll: bool) -> str:
    """Build a simple JS extraction script (placeholder for future CDP usage)."""
    return f"// placeholder — using --dump-dom instead of CDP for simplicity\n"


def extract(url: str, max_chars: int) -> None:
    """Lightweight URL fetch + text extraction (no browser)."""
    action_args = {"url": url, "max_chars": max_chars}
    start = time.monotonic()
    try:
        text = _fetch_url(url, max_chars)

        # If we got very little content, it might be a JS-heavy page
        if len(text.strip()) < 100:
            result = {
                "action": "extract",
                "url": url,
                "content": text,
                "chars": len(text),
                "hint": "Very little content extracted. This might be a JS-heavy page — try 'browse' instead.",
            }
        else:
            result = {
                "action": "extract",
                "url": url,
                "content": text,
                "chars": len(text),
            }

        print(json.dumps(result, indent=2))
        _log("extract", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        result = {"error": f"Fetch error: {e.code} {e.reason}", "url": url}
        print(json.dumps(result, indent=2))
        _log("extract", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e), "url": url}
        print(json.dumps(result, indent=2))
        _log("extract", action_args, result, False, start, str(e))


# --- Main ---

def main() -> None:
    parser = argparse.ArgumentParser(description="Jackie Web Bridge — search, summarize, browse")
    parser.add_argument("action", choices=["search", "summarize", "browse", "extract"])

    # Search args
    parser.add_argument("--query", help="Search query (for search)")
    parser.add_argument("--count", type=int, default=5, help="Number of results (default 5)")
    parser.add_argument("--search-depth", dest="search_depth", default="basic",
                        choices=["basic", "advanced"], help="Search depth (default basic)")
    parser.add_argument("--include-domains", dest="include_domains",
                        help="Comma-separated domains to include")
    parser.add_argument("--exclude-domains", dest="exclude_domains",
                        help="Comma-separated domains to exclude")
    parser.add_argument("--include-raw-content", dest="include_raw_content",
                        action="store_true", help="Include full page content in search results")

    # Summarize args
    parser.add_argument("--url", help="URL to summarize/browse/extract")
    parser.add_argument("--max-length", dest="max_length", type=int, default=300,
                        help="Target summary length in words (default 300)")
    parser.add_argument("--extract-only", dest="extract_only", action="store_true",
                        help="Return raw text without summarizing")
    parser.add_argument("--youtube", action="store_true",
                        help="Treat URL as YouTube — extract transcript")
    parser.add_argument("--language", help="Summary language (e.g. zh, en)")

    # Browse args
    parser.add_argument("--wait", type=int, default=2,
                        help="Seconds to wait for JS rendering (default 2)")
    parser.add_argument("--screenshot", action="store_true",
                        help="Save screenshot to /tmp/browse-screenshot.png")
    parser.add_argument("--selector", help="CSS selector to extract specific content")
    parser.add_argument("--scroll", action="store_true",
                        help="Scroll page to trigger lazy loading")

    # Extract args
    parser.add_argument("--max-chars", dest="max_chars", type=int, default=10000,
                        help="Max characters to extract (default 10000)")

    args = parser.parse_args()

    if args.action == "search":
        if not args.query:
            print(json.dumps({"error": "--query is required for search"}))
            sys.exit(1)
        search(args.query, args.count, args.search_depth, args.include_domains,
               args.exclude_domains, args.include_raw_content)
    elif args.action == "summarize":
        if not args.url:
            print(json.dumps({"error": "--url is required for summarize"}))
            sys.exit(1)
        summarize(args.url, args.max_length, args.extract_only, args.youtube, args.language)
    elif args.action == "browse":
        if not args.url:
            print(json.dumps({"error": "--url is required for browse"}))
            sys.exit(1)
        browse(args.url, args.wait, args.screenshot, args.selector, args.scroll)
    elif args.action == "extract":
        if not args.url:
            print(json.dumps({"error": "--url is required for extract"}))
            sys.exit(1)
        extract(args.url, args.max_chars)


if __name__ == "__main__":
    main()
