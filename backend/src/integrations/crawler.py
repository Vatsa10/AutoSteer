"""Web crawler — follows internal links, extracts text + PDFs."""

import io
import json
import re
from urllib.parse import urljoin, urlparse

import httpx

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore[assignment]

try:
    import trafilatura
except ImportError:
    trafilatura = None  # type: ignore[assignment]

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None  # type: ignore[assignment]

_USER_AGENT = "AutoSteer/0.1 (+https://github.com/autosteer)"


async def web_crawl(
    url: str,
    max_depth: int = 2,
    max_pages: int = 10,
    **_
) -> str:
    """Crawl a website starting from url. Extracts text from HTML pages and PDFs."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    base_domain = urlparse(url).netloc
    if not base_domain:
        return json.dumps({"error": f"Invalid URL: {url}", "pages": [], "pdfs": []})

    visited: set[str] = set()
    pages: list[dict] = []
    pdfs: list[dict] = []
    queue: list[tuple[str, int]] = [(url, 0)]  # (url, depth)

    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": _USER_AGENT},
        max_redirects=5,
    ) as client:

        while queue and len(pages) + len(pdfs) < max_pages:
            current_url, depth = queue.pop(0)
            if current_url in visited:
                continue
            visited.add(current_url)

            try:
                resp = await client.get(current_url)
                resp.raise_for_status()
            except Exception:
                continue

            content_type = resp.headers.get("content-type", "").lower()

            # ── PDF ──────────────────────────────────────────
            if "application/pdf" in content_type or current_url.lower().endswith(".pdf"):
                if PdfReader is None:
                    pdfs.append({
                        "url": current_url,
                        "error": "PyPDF2 not installed. Run: pip install pypdf2",
                    })
                    continue
                try:
                    reader = PdfReader(io.BytesIO(resp.content))
                    text_parts = []
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    pdf_text = "\n\n".join(text_parts)
                    if len(pdf_text) > 16000:
                        pdf_text = pdf_text[:16000] + "\n...[truncated]"
                    pdfs.append({
                        "url": current_url,
                        "title": _extract_title(resp.text) or current_url.rsplit("/", 1)[-1],
                        "text": pdf_text,
                        "pages": len(reader.pages),
                        "char_count": len(pdf_text),
                    })
                except Exception as exc:
                    pdfs.append({"url": current_url, "error": str(exc)})
                continue

            # ── HTML ─────────────────────────────────────────
            html = resp.text

            # Extract text
            text = ""
            if trafilatura:
                text = trafilatura.extract(html, url=current_url, include_comments=False) or ""
            if not text:
                text = _fallback_extract(html)

            if len(text) > 8000:
                text = text[:8000] + "\n...[truncated]"

            title = _extract_title(html) or ""
            pages.append({
                "url": current_url,
                "title": title,
                "text": text,
                "char_count": len(text),
            })

            # ── Discover links (only if within depth) ────────
            if depth < max_depth and BeautifulSoup is not None and html:
                try:
                    soup = BeautifulSoup(html, "lxml")
                except Exception:
                    try:
                        soup = BeautifulSoup(html, "html.parser")
                    except Exception:
                        continue

                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    full_url = urljoin(current_url, href)
                    parsed = urlparse(full_url)
                    # Only follow same-domain, non-fragment URLs
                    if parsed.netloc == base_domain and full_url not in visited:
                        # Skip mailto, tel, javascript
                        if parsed.scheme in ("http", "https"):
                            queue.append((full_url, depth + 1))

    return json.dumps({
        "url": url,
        "domain": base_domain,
        "pages": pages,
        "pdfs": pdfs,
        "stats": {
            "pages_found": len(pages),
            "pdfs_found": len(pdfs),
            "total_urls_visited": len(visited),
            "max_depth": max_depth,
            "max_pages": max_pages,
        },
    }, indent=2)


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _fallback_extract(html: str) -> str:
    """Naive HTML text extraction when trafilatura is unavailable."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())
