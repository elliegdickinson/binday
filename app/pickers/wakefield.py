"""Wakefield: address picker and collector, without a browser.

Flagged `web_driver` upstream, but nothing here needs one. The catch is that
the collection page only answers to a *complete* set of query parameters -
`?uprn=` alone returns the page with no collections on it. The address search
hands back links carrying the full set (uprn, address, usrn, easting,
northing), so the flow is:

  1. GET /pick-your-address?where-i-live=<postcode>  -> one link per address
  2. GET that link verbatim                          -> "Bin collections" section

`collect` repeats the search rather than carrying that long URL around, which
keeps our own feed URLs to a postcode and a UPRN like every other council.
"""
from __future__ import annotations

import html
import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

SEARCH = "https://www.wakefield.gov.uk/pick-your-address"
LINK_RE = re.compile(r'href="([^"]*where-i-live\?[^"]*)"[^>]*>(.*?)</a>', re.S)
UPRN_RE = re.compile(r"[?&]uprn=(\d+)")
# "Next collection - Wednesday, 23 September 2026"
WHEN_RE = re.compile(r"(?:next|last) collection\s*-\s*(.+)", re.I)


def _links(page: str) -> list[dict]:
    out, seen = [], set()
    for href, label in LINK_RE.findall(page):
        href = html.unescape(href)
        found = UPRN_RE.search(href)
        if not found or found.group(1) in seen:
            continue
        seen.add(found.group(1))
        text = html.unescape(re.sub(r"<[^>]+>", "", label)).strip()
        if text:
            out.append({"key": found.group(1), "address": text, "href": href})
    return out


def _search_sync(client: httpx.Client, postcode: str) -> list[dict]:
    r = client.get(SEARCH, params={"where-i-live": postcode})
    return _links(r.text)


async def lookup(postcode: str, *, user_agent: str) -> list[dict]:
    async with httpx.AsyncClient(follow_redirects=True, timeout=30,
                                 headers={"User-Agent": user_agent}) as client:
        r = await client.get(SEARCH, params={"where-i-live": postcode})
    return [{"key": row["key"], "address": row["address"]} for row in _links(r.text)]


async def resolve(postcode: str, key: str, *, user_agent: str) -> dict:
    """The key is already the UPRN; this only confirms the address."""
    found = await lookup(postcode, user_agent=user_agent)
    match = next((r for r in found if r["key"] == key), None)
    if not match:
        raise RuntimeError("That address isn't in this postcode.")
    return {"uprn": key, "address": match["address"], "url": SEARCH}


def _parse(page: str) -> list[dict]:
    soup = BeautifulSoup(page, "html.parser")
    bins: list[dict] = []
    for heading in soup.find_all("div", {"class": "wil_c-content-section_heading"}):
        if heading.get_text(strip=True).lower() != "bin collections":
            continue
        body = heading.find_next_sibling("div", {"class": "c-content-section_body"})
        if not body:
            continue
        rows = body.find_all(
            "div",
            class_=lambda c: c and "tablet:l-col-fb-4" in c and "u-mt-10" in c)
        for row in rows:
            title = row.find("div", class_="u-mb-4")
            if not title:
                continue
            name = title.get_text(strip=True)
            for line in row.find_all("div", class_="u-mb-2"):
                when = WHEN_RE.search(line.get_text(" ", strip=True))
                if not when:
                    continue
                try:
                    date = datetime.strptime(when.group(1).strip(), "%A, %d %B %Y").date()
                except ValueError:
                    continue
                bins.append({"type": name,
                             "collectionDate": date.strftime("%d/%m/%Y")})
        break
    return bins


def collect(council: str, url: str, extra: dict, *, user_agent: str) -> list[dict]:
    postcode, uprn = extra.get("postcode") or "", extra.get("uprn") or ""
    if not postcode or not uprn:
        raise RuntimeError("Wakefield needs a postcode and a UPRN.")

    with httpx.Client(follow_redirects=True, timeout=40,
                      headers={"User-Agent": user_agent}) as client:
        rows = _search_sync(client, postcode)
        match = next((r for r in rows if r["key"] == uprn), None)
        if not match:
            raise RuntimeError("That address isn't in this postcode.")
        # The link must be followed as given - a trimmed query returns the page
        # with no collections on it.
        page = client.get(match["href"])

    return _parse(page.text)
