"""Councils on the Syncfusion "Public Dashboard" platform.

UKBinCollectionData drives these through Selenium, because the premises
dropdown and the collection calendar are rendered client-side. They don't need
a browser: the page is a Razor Page whose handlers are ordinary form posts, and
both payloads are embedded in the HTML as JSON before Syncfusion touches them.

  1. GET  <base>                          -> antiforgery token + cookie
  2. POST <base>?handler=SearchPostcode   -> premises JSON (UPRN + Premises)
  3. POST <base>?handler=SelectPrem       -> appointment JSON (Subject + StartTime)

`make(base)` returns the (lookup, resolve, collect) trio for one council, so
adding another on this platform is one line. Known hosts:

  bins.staffsmoorlands.gov.uk   Staffordshire Moorlands
  bins.highpeak.gov.uk          High Peak

A property can legitimately have no appointments (commercial units do), which
surfaces as an empty list, not an error.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

import httpx

TOKEN_RE = re.compile(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"')
ARRAY_RE = re.compile(r"isJson\(\s*(\[.*?\])\s*\)", re.S)


def _token(page: str, where: str) -> str:
    found = TOKEN_RE.search(page)
    if not found:
        raise RuntimeError(f"{where} changed: no antiforgery token")
    return found.group(1)


def _rows(page: str) -> list[dict]:
    """Every dict in every embedded isJson([...]) array."""
    out: list[dict] = []
    for match in ARRAY_RE.finditer(page):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            out += [row for row in data if isinstance(row, dict)]
    return out


def _premises(page: str) -> list[dict]:
    seen, out = set(), []
    for row in _rows(page):
        if "UPRN" not in row or not row.get("Premises"):
            continue
        uprn = str(int(row["UPRN"]))
        if uprn in seen:
            continue
        seen.add(uprn)
        out.append({"key": uprn, "address": str(row["Premises"]).strip()})
    return out


def make(base: str, name: str):
    """Build (lookup, resolve, collect) for one Public Dashboard council."""

    async def _search(client: httpx.AsyncClient, postcode: str) -> str:
        page = await client.get(base)
        result = await client.post(f"{base}?handler=SearchPostcode", data={
            "__RequestVerificationToken": _token(page.text, name),
            "SelectedPostcode": postcode,
        })
        return result.text

    async def lookup(postcode: str, *, user_agent: str) -> list[dict]:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30,
                                     headers={"User-Agent": user_agent}) as client:
            return _premises(await _search(client, postcode))

    async def resolve(postcode: str, key: str, *, user_agent: str) -> dict:
        """The picker already returns the real UPRN, so this only confirms the
        address - unlike Stockport, whose search returns a different id."""
        found = await lookup(postcode, user_agent=user_agent)
        match = next((r for r in found if r["key"] == key), None)
        if not match:
            raise RuntimeError("That address isn't in this postcode.")
        return {"uprn": key, "address": match["address"], "url": base}

    def collect(council: str, url: str, extra: dict, *, user_agent: str) -> list[dict]:
        postcode, uprn = extra.get("postcode") or "", extra.get("uprn") or ""
        if not postcode or not uprn:
            raise RuntimeError(f"{name} needs a postcode and a UPRN.")

        with httpx.Client(follow_redirects=True, timeout=40,
                          headers={"User-Agent": user_agent}) as client:
            page = client.get(base)
            search = client.post(f"{base}?handler=SearchPostcode", data={
                "__RequestVerificationToken": _token(page.text, name),
                "SelectedPostcode": postcode,
            })
            detail = client.post(f"{base}?handler=SelectPrem", data={
                "__RequestVerificationToken": _token(search.text, name),
                "SelectedPostcode": postcode,
                "SelectedPremises": uprn,
            })

        bins, seen = [], set()
        for row in _rows(detail.text):
            subject, start = row.get("Subject"), row.get("StartTime")
            if not subject or not start:
                continue
            try:
                when = datetime.fromisoformat(str(start)).date()
            except ValueError:
                continue
            if (subject, when) in seen:
                continue
            seen.add((subject, when))
            bins.append({"type": str(subject),
                         "collectionDate": when.strftime("%d/%m/%Y")})
        return bins

    return lookup, resolve, collect


STAFFS_MOORLANDS = make("https://bins.staffsmoorlands.gov.uk/PublicDashboard",
                        "Staffordshire Moorlands")
HIGH_PEAK = make("https://bins.highpeak.gov.uk/PublicDashboard", "High Peak")
