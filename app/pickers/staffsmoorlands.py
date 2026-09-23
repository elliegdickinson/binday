"""Staffordshire Moorlands: address picker *and* collector, without a browser.

UKBinCollectionData drives this council through Selenium, because its
Syncfusion "Public Dashboard" renders the premises dropdown and the collection
calendar client-side. But the page is a Razor Page whose handlers are ordinary
form posts, and it embeds the data as JSON before Syncfusion ever touches it -
so plain HTTP gets everything:

  1. GET  /PublicDashboard                     -> antiforgery token + cookie
  2. POST /PublicDashboard?handler=SearchPostcode -> premises JSON (UPRN + address)
  3. POST /PublicDashboard?handler=SelectPrem     -> appointment JSON (Subject + StartTime)

That matters beyond this one council: 93 councils are excluded from this build
for needing headless Chrome, and any of them on this platform can be done the
same way. High Peak is on the same dashboard.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

import httpx

BASE = "https://bins.staffsmoorlands.gov.uk/PublicDashboard"
TOKEN_RE = re.compile(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"')
# Both payloads arrive as `...isJson([ ... ])` blocks in the page source.
ARRAY_RE = re.compile(r"isJson\(\s*(\[.*?\])\s*\)", re.S)


def _arrays(page: str) -> list[list]:
    out = []
    for match in ARRAY_RE.finditer(page):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(data, list) and data:
            out.append(data)
    return out


def _token(page: str) -> str:
    found = TOKEN_RE.search(page)
    if not found:
        raise RuntimeError("Staffordshire Moorlands page changed: no token")
    return found.group(1)


async def _search(client: httpx.AsyncClient, postcode: str) -> str:
    page = await client.get(BASE)
    result = await client.post(f"{BASE}?handler=SearchPostcode", data={
        "__RequestVerificationToken": _token(page.text),
        "SelectedPostcode": postcode,
    })
    return result.text


async def lookup(postcode: str, *, user_agent: str) -> list[dict]:
    """Return [{key, address}, ...] - key is the UPRN, which is all we need."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=30,
                                 headers={"User-Agent": user_agent}) as client:
        page = await _search(client, postcode)

    out = []
    for rows in _arrays(page):
        for row in rows:
            if not isinstance(row, dict) or "UPRN" not in row:
                continue
            uprn = str(int(row["UPRN"]))
            address = (row.get("Premises") or "").strip()
            if address:
                out.append({"key": uprn, "address": address})
        if out:
            break
    return out


async def resolve(postcode: str, key: str, *, user_agent: str) -> dict:
    """The picker already hands back the real UPRN, so there is nothing to
    confirm - unlike Stockport, whose search returns a different id."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=30,
                                 headers={"User-Agent": user_agent}) as client:
        page = await _search(client, postcode)
    address = next((r["address"] for r in await lookup(postcode, user_agent=user_agent)
                    if r["key"] == key), "")
    if not address and key not in page:
        raise RuntimeError("That address isn't in this postcode.")
    return {"uprn": key, "address": address, "url": BASE}


def _collect_sync(postcode: str, uprn: str, user_agent: str) -> list[dict]:
    with httpx.Client(follow_redirects=True, timeout=40,
                      headers={"User-Agent": user_agent}) as client:
        page = client.get(BASE)
        search = client.post(f"{BASE}?handler=SearchPostcode", data={
            "__RequestVerificationToken": _token(page.text),
            "SelectedPostcode": postcode,
        })
        detail = client.post(f"{BASE}?handler=SelectPrem", data={
            "__RequestVerificationToken": _token(search.text),
            "SelectedPostcode": postcode,
            "SelectedPremises": uprn,
        })

    bins: list[dict] = []
    seen = set()
    for rows in _arrays(detail.text):
        for row in rows:
            if not isinstance(row, dict):
                continue
            subject, start = row.get("Subject"), row.get("StartTime")
            if not subject or not start:
                continue
            try:
                when = datetime.fromisoformat(start).date()
            except ValueError:
                continue
            marker = (subject, when)
            if marker in seen:
                continue
            seen.add(marker)
            bins.append({"type": subject,
                         "collectionDate": when.strftime("%d/%m/%Y")})
    return bins


def collect(council: str, url: str, extra: dict, *, user_agent: str) -> list[dict]:
    """Native collector, in the shape app.main._collect returns."""
    postcode = extra.get("postcode") or ""
    uprn = extra.get("uprn") or ""
    if not postcode or not uprn:
        raise RuntimeError("Staffordshire Moorlands needs a postcode and a UPRN.")
    return _collect_sync(postcode, uprn, user_agent)
