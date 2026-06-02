"""arXiv paper search API integration."""

import json
import urllib.parse
import xml.etree.ElementTree as ET

import httpx

ARXIV_API = "http://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


async def arxiv_search(
    query: str,
    max_results: int = 5,
    sort_by: str = "relevance",
    **_,
) -> str:
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": min(max_results, 20),
        "sortBy": sort_by,
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        xml_text = resp.text

    root = ET.fromstring(xml_text)
    papers = []
    for entry in root.findall("atom:entry", ATOM_NS):
        authors = [a.find("atom:name", ATOM_NS).text for a in entry.findall("atom:author", ATOM_NS)]
        link_elem = next(
            (lnk for lnk in entry.findall("atom:link", ATOM_NS) if lnk.get("rel") == "alternate"),
            None,
        )
        link = link_elem.get("href", "") if link_elem is not None else ""
        papers.append({
            "id": entry.find("atom:id", ATOM_NS).text if entry.find("atom:id", ATOM_NS) is not None else "",
            "title": (entry.find("atom:title", ATOM_NS).text or "").strip().replace("\n", " "),
            "summary": (entry.find("atom:summary", ATOM_NS).text or "").strip()[:500],
            "published": entry.find("atom:published", ATOM_NS).text if entry.find("atom:published", ATOM_NS) is not None else "",
            "authors": authors,
            "url": link,
        })

    return json.dumps({"query": query, "count": len(papers), "papers": papers}, indent=2)
